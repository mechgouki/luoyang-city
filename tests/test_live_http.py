"""Exercise real retry/denial decisions without a network or real waiting."""
import hashlib
import io
import json
import socket
import ssl
import sys
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from live_http import LiveFetchError, LiveFetcher, _ScopedRedirectHandler

BASE = "https://mechgouki.github.io/luoyang-city/"


class Response(io.BytesIO):
    def __init__(self, body=b"live bytes", url=BASE + "asset.bin", status=200, headers=None):
        super().__init__(body)
        self.url, self.status, self.headers = url, status, headers or {}

    def geturl(self):
        return self.url


class SequenceOpener:
    def __init__(self, *results):
        self.results, self.calls = list(results), []

    def open(self, request, timeout):
        self.calls.append((request.full_url, timeout))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def http_error(status, headers=None):
    return HTTPError(BASE + "asset.bin", status, "test response", headers or {}, None)


class LiveHTTP(unittest.TestCase):
    def test_01_transient_503_and_network_errors_retry_then_return_exact_bytes(self):
        for failure in (http_error(503), Response(status=503),
                        URLError(ConnectionResetError("reset")),
                        URLError(socket.gaierror(socket.EAI_AGAIN, "temporary DNS failure"))):
            with self.subTest(failure=type(failure).__name__):
                body = b"\x00unmodified live data\xff"
                opener, delays = SequenceOpener(failure, Response(body)), []
                fetcher = LiveFetcher(BASE, opener=opener, sleep=delays.append)
                self.assertEqual(fetcher.get("asset.bin"), body)
                self.assertEqual(delays, [1])
                self.assertEqual(opener.calls, [(BASE + "asset.bin", 45)] * 2)
                events = json.loads(json.dumps(fetcher.retries))
                self.assertEqual(events[0]["failed_attempt"], 1)
                self.assertEqual(events[0]["next_attempt"], 2)
                self.assertTrue(events[0]["reason"])
                events[0]["path"] = "changed snapshot"
                self.assertEqual(fetcher.retries[0]["path"], "asset.bin")

    def test_02_429_is_bounded_and_honors_safe_retry_after(self):
        opener = SequenceOpener(*(http_error(429, {"Retry-After": "2"}) for _ in range(4)))
        delays = []
        fetcher = LiveFetcher(BASE, opener=opener, sleep=delays.append)
        with self.assertRaises(LiveFetchError) as caught:
            fetcher.get("asset.bin")
        self.assertEqual(delays, [2, 3, 7])
        self.assertEqual(len(opener.calls), 4)
        self.assertEqual(len(fetcher.retries), 3)
        self.assertEqual((caught.exception.path, caught.exception.status, caught.exception.attempts),
                         ("asset.bin", 429, 4))
        self.assertIn("asset.bin: status=429, attempts=4", str(caught.exception))
        for retry_after, expected_delay in (("Thu, 01 Jan 1970 00:00:05 GMT", 5),
                                             ("invalid", 1), ("30", 30), ("31", None)):
            with self.subTest(retry_after=retry_after):
                opener = SequenceOpener(http_error(429, {"Retry-After": retry_after}), Response())
                delays = []
                fetcher = LiveFetcher(BASE, opener=opener, sleep=delays.append, clock=lambda: 0)
                if expected_delay is None:
                    with self.assertRaisesRegex(LiveFetchError, "Retry-After exceeds"):
                        fetcher.get("asset.bin")
                    self.assertEqual(delays, [])
                    self.assertEqual(len(opener.calls), 1)
                else:
                    self.assertEqual(fetcher.get("asset.bin"), b"live bytes")
                    self.assertEqual(delays, [expected_delay])

    def test_03_404_and_hash_mismatches_are_not_recovered(self):
        opener, delays = SequenceOpener(http_error(404)), []
        fetcher = LiveFetcher(BASE, opener=opener, sleep=delays.append)
        with self.assertRaises(LiveFetchError) as caught:
            fetcher.get("asset.bin")
        self.assertEqual((caught.exception.status, caught.exception.attempts), (404, 1))
        self.assertEqual(len(opener.calls), 1)
        self.assertEqual(delays, [])
        self.assertEqual(fetcher.retries, [])
        # A 200 body is never replaced, interpreted, or fetched again because of its hash.
        opener = SequenceOpener(Response(b"wrong deployed content"))
        fetcher = LiveFetcher(BASE, opener=opener, sleep=delays.append)
        body = fetcher.get("asset.bin")
        self.assertEqual(body, b"wrong deployed content")
        expected = hashlib.sha256(b"correct local content").hexdigest()
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            if hashlib.sha256(body).hexdigest() != expected:
                raise ValueError("asset.bin: SHA-256 mismatch")
        self.assertEqual(len(opener.calls), 1)
        self.assertEqual(fetcher.retries, [])

    def test_04_certificate_and_url_boundary_failures_never_retry(self):
        for failure in (URLError(ssl.SSLCertVerificationError(1, "certificate verify failed")),
                        URLError(socket.gaierror(socket.EAI_NONAME, "name does not exist")),
                        URLError("unclassified failure")):
            with self.subTest(failure=str(failure)):
                opener, delays = SequenceOpener(failure), []
                fetcher = LiveFetcher(BASE, opener=opener, sleep=delays.append)
                with self.assertRaises(LiveFetchError) as caught:
                    fetcher.get("asset.bin")
                self.assertEqual(caught.exception.attempts, 1)
                self.assertEqual(len(opener.calls), 1)
                self.assertEqual(delays, [])
        for base in (BASE.replace("https:", "http:"), "https://user:pass@example.org/site/",
                     BASE + "../outside/", BASE + "?query=1"):
            with self.subTest(base=base), self.assertRaises(ValueError):
                LiveFetcher(base)
        opener, delays = SequenceOpener(), []
        fetcher = LiveFetcher(BASE, opener=opener, sleep=delays.append)
        for path in ("../outside.bin", "/outside.bin", "https://example.org/a", "//example.org/a",
                     "dir/../a", "dir\\a", "%2e%2e/a", "%252e%252e/a", "a\n.bin"):
            with self.subTest(path=path), self.assertRaises(LiveFetchError) as caught:
                fetcher.get(path)
            self.assertEqual(caught.exception.attempts, 0)
        self.assertEqual(opener.calls, [])
        # Exercise the pre-follow guard, and separately check injected/final responses.
        handler = _ScopedRedirectHandler(fetcher._allowed_url)
        for url in ("https://example.org/a", "http://mechgouki.github.io/luoyang-city/a",
                    "https://mechgouki.github.io/another-site/a", BASE + "../a",
                    BASE + "%2e%2e/a", BASE + "%252e%252e/a"):
            with self.subTest(url=url):
                with self.assertRaisesRegex(ValueError, "Redirect outside"):
                    handler.redirect_request(Request(BASE + "asset.bin"), None, 302, "Found", {}, url)
                offsite = SequenceOpener(Response(url=url))
                client = LiveFetcher(BASE, opener=offsite, sleep=delays.append)
                with self.assertRaisesRegex(LiveFetchError, "Response outside"):
                    client.get("asset.bin")
                self.assertEqual(len(offsite.calls), 1)
                self.assertEqual(client.retries, [])
        self.assertEqual(delays, [])

    def test_05_parallel_retry_log_is_complete_and_detached(self):
        lock, counts = threading.Lock(), {}

        def opener(request, timeout):
            with lock:
                attempt = counts.get(request.full_url, 0) + 1
                counts[request.full_url] = attempt
            if attempt == 1:
                raise HTTPError(request.full_url, 503, "busy", {}, None)
            return Response(request.full_url.encode(), request.full_url)

        fetcher = LiveFetcher(BASE, opener=opener, sleep=lambda delay: None)
        paths = [f"assets/{i}.bin" for i in range(24)]
        with ThreadPoolExecutor(max_workers=6) as pool:
            bodies = list(pool.map(fetcher.get, paths))
        self.assertEqual(bodies, [(BASE + path).encode() for path in paths])
        events = json.loads(json.dumps(fetcher.retries))
        self.assertEqual({event["path"] for event in events}, set(paths))
        self.assertEqual(len(events), 24)
        self.assertTrue(all(count == 2 for count in counts.values()))
        events.clear()
        self.assertEqual(len(fetcher.retries), 24)


if __name__ == "__main__":
    unittest.main()
