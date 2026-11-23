"""An exact, reversible publication layer above the complete R10 release."""
import copy
import hashlib
import json
from functools import lru_cache

KEY = "city_plan_r11"
VERSION = "city-plan-r11"
RESEARCH_VERSION = "R11.1"
PAGE = "luoyang-city-plan.html"
FOLDER = "city-plan-r11"
DATA = FOLDER + "/plan.json"
MANIFEST = FOLDER + "/manifest.json"
PDF = "downloads/city-plan-r11.pdf"
BUNDLE = "downloads/city-plan-r11.zip"
HOME_PAGES = ("index.html", "v3.0-dual.html")
RELEASE_ARCHIVE = FOLDER + "/archive/r10-release.json"
HOME_ARCHIVES = {p: FOLDER + "/archive/" + p for p in HOME_PAGES}
BUILD_CONTROL_FILES = {".nojekyll"}
HOME_ENTRY = ('<a id="r11-plan-entry" href="./luoyang-city-plan.html">'
              '全城统一坐标 · 复原工作平面</a>').encode()
CURRENT_MILESTONE = "盛时 R11.1 · 全城统一坐标复原工作平面"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def strip_current_entries(content):
    from panorama_v14_contract import strip_current_entries as strip_v14_entries
    content = strip_v14_entries(content)
    from city_layout_r10_contract import HOME_ENTRY as anchor
    if b'id="r11-plan-entry"' not in content:
        return content
    assert content.count(HOME_ENTRY) == 1 and content.count(b'id="r11-plan-entry"') == 1
    assert content.count(anchor + HOME_ENTRY) == 1, "R11 homepage change is not its reviewed insertion"
    return content.replace(HOME_ENTRY, b"", 1)


def add_home(content):
    from city_layout_r10_contract import HOME_ENTRY as anchor
    previous = strip_current_entries(content)
    assert previous.count(anchor) == 1, "The existing R10 entry must remain"
    return previous.replace(anchor, anchor + HOME_ENTRY, 1)


def restore_r10_context(info, reader):
    """Validate additions before exposing the exact previous publication bytes."""
    from panorama_v14_contract import restore_r11_context
    info, reader = restore_r11_context(info, reader)
    if KEY not in info:
        return info, reader
    get = lru_cache(maxsize=None)(reader)
    meta, hashes = info[KEY], info["files_sha256"]
    assert meta["version"] == VERSION and meta["research_version"] == RESEARCH_VERSION
    assert meta["source_commit"] == info["source_commit"]
    assert json.loads(get(MANIFEST)) == meta
    assert digest(get(MANIFEST)) == hashes[MANIFEST]
    expected_new={p for p in hashes if p.startswith(FOLDER+'/') and p!=MANIFEST}|{PAGE,PDF}
    assert set(meta['files_sha256'])==expected_new, 'R11 new resource inventory escaped its publication scope'
    for p, checksum in meta['files_sha256'].items():
        assert digest(get(p))==checksum==hashes[p], ('R11 resource bytes changed',p)
    assert digest(get(BUNDLE))==hashes[BUNDLE]
    prior = meta["predecessor_release"]
    assert prior["path"] == RELEASE_ARCHIVE
    previous = get(RELEASE_ARCHIVE)
    assert digest(previous) == prior["sha256"] == hashes[RELEASE_ARCHIVE]
    expected = json.loads(previous)
    assert KEY + "_version" not in expected and VERSION not in expected["extensions"]
    expected["extensions"] = sorted(set(expected["extensions"]) | {VERSION})
    expected[KEY + "_version"] = VERSION
    expected["current_milestone"] = CURRENT_MILESTONE
    assert digest(get("release.json")) == hashes["release.json"]
    assert json.loads(get("release.json")) == expected, "R11 changed unrelated release fields"
    overrides = {"release.json": previous}
    for page in HOME_PAGES:
        actual, archive = get(page), get(HOME_ARCHIVES[page])
        assert actual.count(HOME_ENTRY) == 1
        assert digest(actual) == meta["homepage_after_sha256"][page] == hashes[page]
        assert digest(archive) == meta["homepage_before_sha256"][page] == hashes[HOME_ARCHIVES[page]]
        assert strip_current_entries(actual) == archive, "R11 homepage edit is not exactly reversible"
        overrides[page] = archive
    restored = copy.deepcopy(info)
    restored.pop(KEY)
    # Earlier preservation assertions must see their complete original inventory,
    # with only this new layer removed, not a relaxed predecessor contract.
    for p in [*meta["files_sha256"], MANIFEST, BUNDLE]:
        restored["files_sha256"].pop(p, None)
    for p, raw in overrides.items():
        restored["files_sha256"][p] = digest(raw)

    def read(path):
        return overrides[path] if path in overrides else get(path)

    return restored, read
