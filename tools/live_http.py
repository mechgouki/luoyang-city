"""Bounded HTTPS retrieval for live acceptance; content hashes stay with the caller."""
import errno
import math
import socket
import ssl
import threading
import time
from datetime import timezone
from email.utils import parsedate_to_datetime
from http.client import IncompleteRead, RemoteDisconnected
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class LiveFetchError(RuntimeError):
    """A failed asset request, including its actual attempt count."""

    def __init__(self, path, status, attempts, reason):
        self.path, self.status, self.attempts, self.reason = path, status, attempts, reason
        super().__init__(f"{path}: status={status}, attempts={attempts}: {reason}")


def _checked_path(path):
    """Reject traversal even when a redirect percent-encodes it."""
    for _ in range(8):
        if "\\" in path or any(ord(char) < 32 or ord(char) == 127 for char in path):
            raise ValueError("Unsafe asset path")
        if any(part in (".", "..") for part in path.split("/")):
            raise ValueError("Unsafe asset path")
        decoded = unquote(path)
        if decoded == path:
            return path
        path = decoded
    raise ValueError("Excessively encoded asset path")


class _ScopedRedirectHandler(HTTPRedirectHandler):
    def __init__(self, allowed):
        super().__init__()
        self.allowed = allowed

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Reject before urllib follows it, as well as checking the final response.
        if not self.allowed(urljoin(req.full_url, newurl)):
            if fp is not None:
                fp.close()
            raise ValueError("Redirect outside HTTPS base URL")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _transient(error):
    if isinstance(error, URLError):
        return isinstance(error.reason, Exception) and _transient(error.reason)
    if isinstance(error, ssl.SSLError):
        return False
    if isinstance(error, socket.gaierror):
        return error.errno == socket.EAI_AGAIN
    if isinstance(error, (TimeoutError, ConnectionResetError, ConnectionAbortedError,
                          BrokenPipeError, RemoteDisconnected, IncompleteRead)):
        return True
    return isinstance(error, OSError) and error.errno in {
        errno.ECONNRESET, errno.ECONNABORTED, errno.ETIMEDOUT, errno.EPIPE, errno.ENETRESET,
    }


class LiveFetcher:
    """Fetch only this HTTPS site, with finite retries for transient failures.

    ``opener`` may be a urllib-style callable or an object with ``open``. The
    default opener rejects off-site/out-of-base redirects before following them.
    ``retries`` returns a thread-safe, JSON-serializable snapshot of actual retries.
    No local files, expected hashes, or fallback content are accepted by this API.
    """

    def __init__(self, base_url, attempts=4, timeout=45, *, opener=None, sleep=None, clock=None):
        if not isinstance(base_url, str) or any(ord(c) < 32 for c in base_url):
            raise ValueError("Invalid HTTPS base URL")
        parsed = urlsplit(base_url)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
                or parsed.password is not None or parsed.query or parsed.fragment or "\\" in base_url):
            raise ValueError("HTTPS base URL without credentials, query or fragment required")
        self._origin = (parsed.hostname.lower(), 443 if parsed.port is None else parsed.port)
        base_path = parsed.path.rstrip("/") + "/"
        self._base_path = _checked_path(base_path)
        self.base_url = urlunsplit(("https", parsed.netloc, base_path, "", ""))
        if type(attempts) is not int or attempts < 1:
            raise ValueError("attempts must be a positive integer")
        if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be a positive finite number")
        self.attempts, self.timeout = attempts, timeout
        self._sleep = sleep if sleep is not None else time.sleep
        self._clock = clock if clock is not None else time.time
        default_opener = build_opener(_ScopedRedirectHandler(self._allowed_url)) if opener is None else opener
        self._open = default_opener.open if hasattr(default_opener, "open") else default_opener
        self._retries = []
        self._lock = threading.Lock()

    @property
    def retries(self):
        with self._lock:
            return [event.copy() for event in self._retries]

    def _allowed_url(self, url):
        try:
            if any(ord(c) < 32 or ord(c) == 127 for c in url):
                return False
            parsed = urlsplit(url)
            return (parsed.scheme == "https" and parsed.hostname is not None
                    and parsed.username is None and parsed.password is None
                    and (parsed.hostname.lower(), 443 if parsed.port is None else parsed.port) == self._origin
                    and _checked_path(parsed.path).startswith(self._base_path))
        except (TypeError, ValueError):
            return False

    def _target(self, path):
        if not isinstance(path, str) or not path or path.startswith("/"):
            raise ValueError("A relative asset path is required")
        parsed = urlsplit(path)
        if parsed.scheme or parsed.netloc:
            raise ValueError("A relative asset path is required")
        _checked_path(path)
        target = urljoin(self.base_url, quote(path, safe="/"))
        if not self._allowed_url(target):
            raise ValueError("Asset outside HTTPS base URL")
        return target

    def _delay(self, attempt, retry_after):
        delay = (1, 3, 7)[min(attempt - 1, 2)]
        if not retry_after:
            return float(delay)
        value = retry_after.strip()
        try:
            if value.isascii() and value.isdigit():
                requested = float(value)
            else:
                date = parsedate_to_datetime(value)
                if date.tzinfo is None:
                    date = date.replace(tzinfo=timezone.utc)
                requested = max(0, date.timestamp() - self._clock())
        except (ValueError, TypeError, OverflowError):
            return float(delay)
        # Do not retry earlier than a server's valid, longer requested wait.
        if requested > 30:
            return None
        return float(max(delay, requested))

    def get(self, path):
        try:
            target = self._target(path)
        except (TypeError, ValueError) as error:
            raise LiveFetchError(path, None, 0, str(error)) from error
        for attempt in range(1, self.attempts + 1):
            status, retry_after, cause = None, None, None
            try:
                request = Request(target, headers={
                    "User-Agent": "Luoyang-Atlas-Acceptance/0.8.0", "Cache-Control": "no-cache",
                })
                with self._open(request, timeout=self.timeout) as response:
                    status = response.status
                    if not self._allowed_url(response.geturl()):
                        raise ValueError("Response outside HTTPS base URL")
                    if status == 200:
                        return response.read()
                    reason = f"HTTP {status}"
                    retryable = status == 429 or 500 <= status <= 599
                    retry_after = response.headers.get("Retry-After")
            except HTTPError as error:
                cause, status = error, error.code
                reason = f"HTTP {status}: {error.reason}"
                retryable = status == 429 or 500 <= status <= 599
                retry_after = error.headers.get("Retry-After") if error.headers is not None else None
                if not self._allowed_url(error.geturl()):
                    reason, retryable = "Response outside HTTPS base URL", False
                error.close()
            except Exception as error:
                cause, reason, retryable = error, f"{type(error).__name__}: {error}", _transient(error)
            if not retryable or attempt == self.attempts:
                raise LiveFetchError(path, status, attempt, reason) from cause
            delay = self._delay(attempt, retry_after)
            if delay is None:
                raise LiveFetchError(path, status, attempt,
                                     f"{reason}; Retry-After exceeds the 30-second wait limit") from cause
            with self._lock:
                self._retries.append({
                    "path": path, "failed_attempt": attempt, "next_attempt": attempt + 1,
                    "retry_number": attempt, "status": status, "reason": reason,
                    "delay_seconds": delay,
                })
            self._sleep(delay)
