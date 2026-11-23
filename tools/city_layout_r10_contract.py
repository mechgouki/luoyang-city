"""Exact R10 publication additions and a verified view of the preceding R9 bytes.

This is a reader adapter, not a relaxation of earlier acceptance assertions.
The current release and both homepage edits are checked before any predecessor
bytes are exposed to a previous stage's unchanged verification contract.
"""
import copy
import hashlib
import json
from functools import lru_cache

from panorama_v13_r2_contract import HOME_ENTRIES as HOME_ANCHOR

KEY = "city_layout_r10"
VERSION = "city-layout-r10"
RESEARCH_VERSION = "R10.1"
PAGE = "luoyang-city-layout.html"
FOLDER = "city-layout-r10"
MANIFEST = FOLDER + "/manifest.json"
DATA = FOLDER + "/atlas.json"
PDF = "downloads/city-layout-r10.pdf"
BUNDLE = "downloads/city-layout-r10.zip"
HOME_PAGES = ("index.html", "v3.0-dual.html")
BUILD_CONTROL_FILES = {".nojekyll"}
RELEASE_ARCHIVE = FOLDER + "/archive/r9-release.json"
HOME_ARCHIVES = {page: FOLDER + "/archive/" + page for page in HOME_PAGES}
HOME_ENTRY = ('<a id="r10-layout-entry" href="./luoyang-city-layout.html">'
              '全城总平面 · 十一片区系统深化</a>').encode("utf-8")
CURRENT_MILESTONE = "盛时 R10.1 · 全城总平面与十一片区布局系统深化"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def strip_current_entries(content):
    marker = b'id="r10-layout-entry"'
    if marker not in content:
        return content
    if content.count(marker) != 1 or content.count(HOME_ENTRY) != 1:
        raise ValueError("R10 requires one unchanged homepage entry")
    if content.count(HOME_ANCHOR + HOME_ENTRY) != 1:
        raise ValueError("R10 homepage edit differs from its exact allowed insertion")
    return content.replace(HOME_ENTRY, b"", 1)


restore_home = strip_current_entries


def add_home(content):
    previous = strip_current_entries(content)
    if previous.count(HOME_ANCHOR) != 1:
        raise ValueError("R10 requires the two existing R9 entries exactly once")
    return previous.replace(HOME_ANCHOR, HOME_ANCHOR + HOME_ENTRY, 1)


def restore_r9_context(info, reader):
    """Validate R10's additions, then supply the exact prior release and homes."""
    from city_plan_r11_contract import restore_r10_context
    info, reader = restore_r10_context(info, reader)
    if KEY not in info:
        return info, reader
    get = lru_cache(maxsize=None)(reader)
    meta, hashes = info[KEY], info["files_sha256"]
    assert meta["version"] == VERSION and meta["research_version"] == RESEARCH_VERSION
    assert meta["source_commit"] == info["source_commit"]
    assert json.loads(get(MANIFEST)) == meta, "R10 manifest differs from build-info"
    assert digest(get(MANIFEST)) == hashes[MANIFEST]
    current_raw = get("release.json")
    assert digest(current_raw) == hashes["release.json"], "Current release bytes differ"
    prior = meta["predecessor_release"]
    assert prior["path"] == RELEASE_ARCHIVE
    prior_raw = get(prior["path"])
    assert digest(prior_raw) == hashes[prior["path"]] == prior["sha256"]
    expected = json.loads(prior_raw)
    assert KEY + "_version" not in expected and VERSION not in expected["extensions"]
    expected["extensions"] = sorted(set(expected["extensions"]) | {VERSION})
    expected[KEY + "_version"] = VERSION
    expected["current_milestone"] = CURRENT_MILESTONE
    assert json.loads(current_raw) == expected, "R10 changed release fields beyond its contract"
    assert set(meta["homepage_before_sha256"]) == set(HOME_PAGES)
    assert set(meta["homepage_after_sha256"]) == set(HOME_PAGES)
    overrides = {"release.json": prior_raw}
    for page in HOME_PAGES:
        actual = get(page)
        assert actual.count(HOME_ENTRY) == 1, (page, "Missing exact R10 entry")
        assert digest(actual) == hashes[page] == meta["homepage_after_sha256"][page]
        archive = get(HOME_ARCHIVES[page])
        assert digest(archive) == hashes[HOME_ARCHIVES[page]] == meta["homepage_before_sha256"][page]
        assert strip_current_entries(actual) == archive, "R10 homepage edit is not exactly reversible"
        overrides[page] = archive
    restored = copy.deepcopy(info)
    restored.pop(KEY)
    for path, raw in overrides.items():
        restored["files_sha256"][path] = digest(raw)

    def read(path):
        return overrides[path] if path in overrides else get(path)

    return restored, read
