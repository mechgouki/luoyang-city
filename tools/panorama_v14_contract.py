"""Exact R12 candidate additions above the unchanged R11 publication."""
import copy
import hashlib
import json
from functools import lru_cache

KEY = "panorama_review_v14"
VERSION = "panorama-review-v14"
RESEARCH_VERSION = "R12.1"
PAGE = "luoyang-panorama-v14.html"
FOLDER = "panorama-v14"
MANIFEST = FOLDER + "/manifest.json"
RECORD = FOLDER + "/review.json"
SOURCE_RECORD = "research/panorama-r12/image-record.json"
HOME_PAGES = ("index.html", "v3.0-dual.html")
BUILD_CONTROL_FILES = {".nojekyll"}
RELEASE_ARCHIVE = FOLDER + "/archive/r11-release.json"
HOME_ARCHIVES = {page: FOLDER + "/archive/" + page for page in HOME_PAGES}
HOME_ENTRY = ('<a id="r12-panorama-entry" href="./luoyang-panorama-v14.html">'
              '审看 V14 · 共同平面与全景空间校正</a>').encode()
REJECTED_HOME_ENTRY = ('<a id="r12-panorama-entry" href="./luoyang-panorama-v14.html" '
                       'data-review-status="rejected_needs_revision">'
                       '<strong>V14试绘审查·未通过</strong></a>').encode()
HOME_ENTRIES_BY_STATUS = {"candidate_for_review": HOME_ENTRY, "needs_revision": REJECTED_HOME_ENTRY}
CURRENT_MILESTONE = "盛时 R12.1 · 共同平面约束的V14全景候选"
MILESTONES_BY_STATUS = {
    "candidate_for_review": CURRENT_MILESTONE,
    "needs_revision": "盛时 R12.1 · 共同透视底稿与V14试绘审查·未通过",
}
ACCEPTED_REVIEW_STATUSES = {"accepted_for_user_review", "accepted_for_user_review_with_known_limits"}
REJECTED_REVIEW_STATUS = "rejected_needs_revision"
DISPLAY_GUIDE_ROLES = {"projection_overview", "projection_yongning", "massing_display", "alignment_audit"}


def home_entry(status="candidate_for_review"):
    assert status in HOME_ENTRIES_BY_STATUS, "Unknown V14 image status"
    return HOME_ENTRIES_BY_STATUS[status]


def milestone(status):
    assert status in MILESTONES_BY_STATUS, "Unknown V14 image status"
    return MILESTONES_BY_STATUS[status]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def strip_current_entries(content):
    from city_plan_r11_contract import HOME_ENTRY as anchor
    marker = b'id="r12-panorama-entry"'
    if marker not in content:
        return content
    matching = [entry for entry in HOME_ENTRIES_BY_STATUS.values() if entry in content]
    assert content.count(marker) == len(matching) == 1, "R12 requires one exact state-specific entry"
    entry = matching[0]
    assert content.count(entry) == content.count(anchor + entry) == 1, "R12 homepage edit differs from its exact insertion"
    return content.replace(entry, b"", 1)


def add_home(content, status="candidate_for_review"):
    from city_plan_r11_contract import HOME_ENTRY as anchor
    previous = strip_current_entries(content)
    assert previous.count(anchor) == 1, "The R11 plan entry must remain"
    return previous.replace(anchor, anchor + home_entry(status), 1)


def restore_r11_context(info, reader):
    """Validate this addition before exposing the exact previous inventory/bytes."""
    if KEY not in info:
        return info, reader
    get = lru_cache(maxsize=None)(reader)
    meta, hashes = info[KEY], info["files_sha256"]
    assert meta["version"] == VERSION and meta["research_version"] == RESEARCH_VERSION
    assert meta["source_commit"] == info["source_commit"]
    assert meta["homepage_replacement_approved"] is False
    status = meta["status"]
    assert status in HOME_ENTRIES_BY_STATUS
    if status == "needs_revision":
        assert meta["review_status"] == REJECTED_REVIEW_STATUS
        assert isinstance(meta["blocking_findings"], list) and meta["blocking_findings"]
        assert all(isinstance(item, str) and item.strip() for item in meta["blocking_findings"])
    else:
        assert meta["review_status"] in ACCEPTED_REVIEW_STATUSES
        assert not meta["blocking_findings"]
    assert meta["blocking_findings_count"] == len(meta["blocking_findings"])
    assert json.loads(get(MANIFEST)) == meta
    assert digest(get(MANIFEST)) == hashes[MANIFEST]
    new_paths = {p for p in hashes if p.startswith(FOLDER + "/") and p != MANIFEST} | {PAGE}
    assert set(meta["files_sha256"]) == new_paths, "R12 inventory escaped its publication scope"
    for path, checksum in meta["files_sha256"].items():
        assert digest(get(path)) == checksum == hashes[path], (path, "R12 resource bytes changed")
    prior = meta["predecessor_release"]
    assert prior["path"] == RELEASE_ARCHIVE
    previous = get(RELEASE_ARCHIVE)
    assert digest(previous) == prior["sha256"] == hashes[RELEASE_ARCHIVE]
    expected = json.loads(previous)
    assert all(KEY + suffix not in expected for suffix in ("_version", "_status", "_review_status"))
    assert VERSION not in expected["extensions"]
    expected["extensions"] = sorted(set(expected["extensions"]) | {VERSION})
    expected[KEY + "_version"] = VERSION
    expected[KEY + "_status"] = status
    expected[KEY + "_review_status"] = meta["review_status"]
    expected["current_milestone"] = milestone(status)
    assert digest(get("release.json")) == hashes["release.json"]
    assert json.loads(get("release.json")) == expected, "R12 changed unrelated release fields"
    overrides = {"release.json": previous}
    assert set(meta["homepage_before_sha256"]) == set(meta["homepage_after_sha256"]) == set(HOME_PAGES)
    for page in HOME_PAGES:
        actual, archive = get(page), get(HOME_ARCHIVES[page])
        assert digest(actual) == hashes[page] == meta["homepage_after_sha256"][page]
        assert digest(archive) == hashes[HOME_ARCHIVES[page]] == meta["homepage_before_sha256"][page]
        assert actual.count(home_entry(status)) == 1, "Homepage entry differs from the image review state"
        assert strip_current_entries(actual) == archive, "R12 homepage change is not exactly reversible"
        overrides[page] = archive
    restored = copy.deepcopy(info)
    restored.pop(KEY)
    for path in [*new_paths, MANIFEST]:
        restored["files_sha256"].pop(path)
    for path, raw in overrides.items():
        restored["files_sha256"][path] = digest(raw)
    expected_protected = set(restored["files_sha256"]) - {*HOME_PAGES, "release.json", *BUILD_CONTROL_FILES}
    assert set(meta["protected_files_sha256"]) == expected_protected, "R12 predecessor inventory is incomplete"
    for path, checksum in meta["protected_files_sha256"].items():
        assert checksum == restored["files_sha256"][path], (path, "Earlier public inventory changed")

    def read(path):
        return overrides[path] if path in overrides else get(path)

    return restored, read
