"""Verify the exact R8 view beneath the two reversible R9 delivery layers.

R9 adds pages and two homepage links. R8's existing provenance, resource and
homepage assertions still run against the exact earlier bytes after checking
the public R9 archives. No candidate art or older evidence is substituted.
"""
import copy
import hashlib
import json

from panorama_v13_r2_contract import HOME_PAGES, KEY as PANORAMA_KEY, strip_current_entries


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def restore_r8_context(info, reader):
    if "city_spatial_r9" not in info:
        return info, reader
    restored = copy.deepcopy(info)
    overrides = {}
    hashes = info["files_sha256"]
    current_release = reader("release.json")
    assert digest(current_release) == hashes["release.json"], "Current release bytes differ"
    current = json.loads(current_release)
    spatial = info["city_spatial_r9"]
    assert current["city_spatial_r9_version"] == spatial["version"]
    assert spatial["version"] in current["extensions"]
    if PANORAMA_KEY in info:
        panorama = info[PANORAMA_KEY]
        prior = panorama["predecessor_release"]
        prior_raw = reader(prior["path"])
        assert digest(prior_raw) == hashes[prior["path"]] == prior["sha256"]
        previous = json.loads(prior_raw)
        expected = copy.deepcopy(previous)
        expected["extensions"] = sorted(set(expected["extensions"]) | {panorama["version"]})
        expected[PANORAMA_KEY + "_version"] = panorama["version"]
        from panorama_v13_r2_contract import CURRENT_MILESTONE
        expected["current_milestone"] = CURRENT_MILESTONE
        assert current == expected, "R9 candidate changed release fields beyond its contract"
        current = previous
        for page in HOME_PAGES:
            actual = reader(page)
            assert digest(actual) == hashes[page]
            previous_home = strip_current_entries(actual)
            saved = panorama["predecessor_homepage"][page]
            archive = reader(saved["archive"])
            assert digest(archive) == hashes[saved["archive"]] == saved["sha256"]
            assert previous_home == archive, "R9 homepage edit is not exactly reversible"
            overrides[page] = previous_home
            restored["files_sha256"][page] = digest(previous_home)
    prior = spatial["predecessor_release"]
    raw = reader(prior["path"])
    assert digest(raw) == hashes[prior["path"]] == prior["sha256"]
    expected = json.loads(raw)
    expected["extensions"] = sorted(set(expected["extensions"]) | {spatial["version"]})
    expected["city_spatial_r9_version"] = spatial["version"]
    expected["current_milestone"] = "盛时 R9.1 · 城市空间总图、20项判断与V13修订候选"
    assert current == expected, "R9 spatial release changed fields beyond its contract"
    overrides["release.json"] = raw
    restored["files_sha256"]["release.json"] = digest(raw)

    def read(path):
        return overrides[path] if path in overrides else reader(path)
    return restored, read
