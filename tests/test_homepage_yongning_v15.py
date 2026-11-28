"""Acceptance of the actual V15 layer, its research limits and its predecessor.

Run after the normal build. These tests deliberately require the real publication
output: an absent V15 build is an error, not a skipped acceptance gate. Mutations
are supplied through an in-memory reader; no published file is edited.
"""
import copy
from functools import lru_cache
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
sys.path.insert(0, str(ROOT / "tools"))

import homepage_yongning_v15 as publisher


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


class Elements(HTMLParser):
    """Read visible-text candidates and links without a browser dependency."""

    def __init__(self, raw):
        super().__init__()
        self.ids = []
        self.attributes = {}
        self.links = []
        self.text = []
        self.feed(raw.decode("utf-8"))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
            self.attributes[attrs["id"]] = attrs
        if tag == "a":
            self.links.append(attrs)

    def handle_data(self, value):
        if value.strip():
            self.text.append(value.strip())


class HomepageYongningV15Acceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = json.loads((SITE / "build-info.json").read_bytes())
        if publisher.KEY not in cls.info:
            raise AssertionError("Build the actual V15 publication before running its acceptance tests")
        cls.meta = cls.info[publisher.KEY]
        cls.read = staticmethod(lru_cache(maxsize=None)(lambda path: (SITE / path).read_bytes()))
        cls.previous = json.loads(cls.read(cls.meta["previous_build_info"]))
        # Establish a passing real baseline before attributing failures to mutations.
        cls.baseline = publisher.verify(cls.info, cls.read)

    def mutated(self, replacements, *, rehash=False, metadata_changes=None):
        """Optionally simulate coherent manifest rewriting, not only stale hashes."""
        info = copy.deepcopy(self.info)
        changes = dict(replacements)
        meta = info[publisher.KEY]
        if rehash:
            for path, raw in changes.items():
                checksum = sha256(raw)
                info["files_sha256"][path] = checksum
                if path in meta["files_sha256"]:
                    meta["files_sha256"][path] = checksum
                if path in meta["homepage_after_sha256"]:
                    meta["homepage_after_sha256"][path] = checksum
        if metadata_changes:
            meta.update(metadata_changes)
        if rehash or metadata_changes:
            changes[publisher.META] = json_bytes(meta)
            info["files_sha256"][publisher.META] = sha256(changes[publisher.META])

        def read(path):
            return changes[path] if path in changes else self.read(path)

        return info, read

    def assert_rejected(self, replacements, *, rehash=False, metadata_changes=None):
        info, read = self.mutated(replacements, rehash=rehash, metadata_changes=metadata_changes)
        with self.assertRaises(AssertionError):
            publisher.verify(info, read)

    def test_actual_new_layer_has_the_user_entry_assets_and_research_limits(self):
        self.assertEqual(self.baseline["status"], "passed")
        self.assertEqual(self.baseline["structural_feasibility"], "not_established")
        self.assertEqual(self.baseline["reversible_homepages"], 2)
        self.assertEqual(self.meta["source_commit"], self.info["source_commit"])
        self.assertEqual(self.meta, json.loads(self.read(publisher.META)))
        for name in publisher.PAGES:
            page = Elements(self.read(name))
            with self.subTest(homepage=name):
                self.assertEqual(page.ids.count("home-yongning-entry"), 1)
                self.assertEqual(page.attributes["home-yongning-entry"]["href"], "./" + publisher.PAGE)
                self.assertEqual(page.attributes["home-hero"]["data-hero-revision"], publisher.REVISION)
                self.assertIn("整体可行性尚未证实", " ".join(page.text))
                self.assertIn("map-viewport", page.ids)

        topic = Elements(self.read(publisher.PAGE))
        text = " ".join(topic.text)
        self.assertEqual(len(topic.ids), len(set(topic.ids)))
        self.assertTrue({"height", "colour", "mechanics", "sources"} <= set(topic.ids))
        self.assertRegex(text, r"整体(?:结构)?可行性尚未(?:确立|证实)")
        self.assertIn("不能据此认定安全可建", text)
        for required in ("133.77", "盘下", "38.2", "147", "131.8", "1/200", "不是147", "朱", "灰"):
            self.assertIn(required, text)
        self.assertTrue({"scenario-low", "scenario-middle", "scenario-upper"} <= set(topic.ids))
        downloads = {link.get("href") for link in topic.links if "download" in link}
        self.assertIn("./yongning-v6/yongning-v6-scaled-elevation.svg", downloads)
        self.assertIn("./yongning-v6/lateral-sensitivity.csv", downloads)

    def test_actual_previous_context_and_protected_bytes_are_exactly_restored(self):
        old, read = publisher.restore_v14_context(self.info, self.read)
        self.assertEqual(old, self.previous)
        self.assertNotIn(publisher.KEY, old)
        self.assertEqual(read("build-info.json"), self.read(self.meta["previous_build_info"]))
        self.assertEqual(read("release.json"), self.read(self.meta["previous_release"]))
        protected = set(old["files_sha256"]) - set(publisher.MUTABLE)
        self.assertEqual(len(protected), self.meta["protected_public_file_count"])
        for path in sorted(protected):
            with self.subTest(protected=path):
                expected = old["files_sha256"][path]
                self.assertEqual(sha256(self.read(path)), expected)
                self.assertEqual(read(path), self.read(path))
        for path in publisher.PAGES:
            before = self.read(publisher.ARCHIVE + path)
            after = self.read(path)
            with self.subTest(reversible=path):
                self.assertEqual(read(path), before)
                self.assertEqual(publisher.restore_home(after), before)
                self.assertEqual(publisher.add_home(before, self.meta["hero"]), after)
                self.assertEqual(sha256(before), old["files_sha256"][path])
                self.assertNotIn(b'id="home-yongning-entry"', before)
                self.assertIn(b'data-hero-revision="panorama-approved-v12"', before)

    def test_current_home_and_topic_bytes_cannot_be_changed(self):
        for path in (*publisher.PAGES, publisher.PAGE, "yongning-v6/topic.css", "yongning-v6/homepage.css"):
            with self.subTest(path=path):
                self.assert_rejected({path: self.read(path) + b"\n<!-- changed after build -->\n"})

    def test_protected_old_resource_and_archive_changes_are_rejected(self):
        paths = ["city-plan-r11/plan.json", publisher.ARCHIVE + "index.html", self.meta["previous_build_info"]]
        for path in paths:
            self.assertIn(path, self.info["files_sha256"])
            with self.subTest(path=path):
                self.assert_rejected({path: self.read(path) + b"\nunauthorized change\n"})
        # A rewritten current checksum must not legitimize new ancient geometry.
        path = "city-plan-r11/plan.json"
        self.assert_rejected({path: self.read(path) + b"\n"}, rehash=True)

    def test_homepage_limit_cannot_be_reversed_even_with_rewritten_hashes(self):
        needle = "整体可行性尚未证实".encode("utf-8")
        for path in publisher.PAGES:
            raw = self.read(path)
            self.assertEqual(raw.count(needle), 1)
            changed = raw.replace(needle, "整体结构已经验证安全可建".encode("utf-8"), 1)
            with self.subTest(path=path):
                self.assert_rejected({path: changed}, rehash=True)

    def test_topic_limit_removal_hidden_limit_and_positive_claim_are_rejected(self):
        raw = self.read(publisher.PAGE)
        verdict = re.compile(r"整体(?:结构)?可行性尚未(?:确立|证实)，不能据此认定安全可建。")
        text = raw.decode("utf-8")
        self.assertEqual(len(verdict.findall(text)), 1)
        altered = {
            "reversed_verdict": verdict.sub("整体结构已经验证安全可建。", text, count=1),
            "hidden_verdict": text.replace('id="research-verdict"', 'id="research-verdict" hidden', 1),
            "additional_positive_claim": text.replace("</main>", '<p id="unearned-safety-claim">147米复原塔已经完整验证，安全可建。</p></main>', 1),
            "incorrect_height_endpoint": text.replace("地面至金露盘下", "地面至宝瓶顶", 1),
        }
        for kind, changed in altered.items():
            self.assertNotEqual(changed, text, kind)
            with self.subTest(change=kind):
                self.assert_rejected({publisher.PAGE: changed.encode("utf-8")}, rehash=True)

    def test_research_asset_substitution_is_rejected_even_with_rewritten_hashes(self):
        replacements = {}
        path = "yongning-v6/mechanics-results.json"
        result = json.loads(self.read(path))
        result["verdict"] = "historical_structural_feasibility_proved_safe"
        replacements[path] = json_bytes(result)
        path = "yongning-v6/design-parameters.json"
        parameters = json.loads(self.read(path))
        parameters["total_height_m_assumed"] = 180
        replacements[path] = json_bytes(parameters)
        path = "yongning-v6/colour-evidence.md"
        replacements[path] = self.read(path) + "\n九层白墙均已得到考古证明。\n".encode("utf-8")
        path = "yongning-v6/yongning-v6-scaled-elevation.svg"
        replacements[path] = self.read(path).replace(b"147", b"180", 1)
        for path, changed in replacements.items():
            self.assertNotEqual(changed, self.read(path), path)
            with self.subTest(path=path):
                self.assert_rejected({path: changed}, rehash=True)

    def test_metadata_cannot_upgrade_reconstruction_to_historical_or_structural_fact(self):
        for field, value in (("structural_feasibility", "safe_to_build"),
                             ("historical_ground_truth_upgraded", True),
                             ("new_ancient_coordinates", 1)):
            with self.subTest(field=field):
                self.assert_rejected({}, metadata_changes={field: value})

    def test_hero_and_scope_cannot_change_behind_the_manifest(self):
        hero = self.meta["hero"]
        for key in ("asset", "small_asset"):
            path = hero[key]
            with self.subTest(asset=path):
                self.assert_rejected({path: self.read(path) + b"wrong image"}, rehash=True)
        info, read = self.mutated({})
        info["unrelated_research_revision"] = "unexpected"
        with self.assertRaises(AssertionError):
            publisher.verify(info, read)


if __name__ == "__main__":
    unittest.main()
