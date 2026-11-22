"""Regression guards for real R10 evidence, geometry and downloadable bytes."""
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from city_layout_r10_contract import (
    BUNDLE, CURRENT_MILESTONE, DATA, FOLDER, HOME_ANCHOR, HOME_ARCHIVES, HOME_ENTRY, HOME_PAGES,
    KEY, MANIFEST, PAGE, PDF, RELEASE_ARCHIVE, RESEARCH_VERSION, VERSION,
    add_home, digest, restore_r9_context, strip_current_entries,
)
from city_layout_r10_verify import (
    BASE, CSVS, OVERVIEW, PUBLIC_INPUTS, REGIONS, SVGS, pointer, source_inputs,
    verify, verify_csv, verify_data, verify_page, verify_svg,
)
from panorama_v13_r2_contract import (
    HOME_ANCHOR as R9_HOME_ANCHOR,
    add_home as add_r9_home,
    strip_current_entries as restore_r8_home,
)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def contract_fixture():
    before = {page: b"<!doctype html><main>" + HOME_ANCHOR + b"</main>" for page in HOME_PAGES}
    prior = {"source_commit": "b" * 40, "extensions": ["city-spatial-r9", "panorama-v13-r2"],
             "current_milestone": "R9", "homepage_hero_revision": "panorama-approved-v12", "unchanged": [1, 2, 3]}
    current = dict(prior, extensions=sorted(prior["extensions"] + [VERSION]), current_milestone=CURRENT_MILESTONE)
    current[KEY + "_version"] = VERSION
    files = {"release.json": encoded(current), RELEASE_ARCHIVE: encoded(prior)}
    for page in HOME_PAGES:
        files[page] = add_home(before[page])
        files[HOME_ARCHIVES[page]] = before[page]
    meta = dict(version=VERSION, research_version=RESEARCH_VERSION, source_commit=prior["source_commit"],
                predecessor_release=dict(path=RELEASE_ARCHIVE, sha256=digest(files[RELEASE_ARCHIVE])),
                homepage_before_sha256={page: digest(before[page]) for page in HOME_PAGES},
                homepage_after_sha256={page: digest(files[page]) for page in HOME_PAGES})
    files[MANIFEST] = encoded(meta)
    info = dict(source_commit=prior["source_commit"], files_sha256={path: digest(raw) for path, raw in files.items()})
    info[KEY] = meta
    return info, files, before, prior


class R10PublicationContract(unittest.TestCase):
    def test_entry_is_exact_idempotent_and_all_older_restoration_still_works(self):
        r8 = b"<main>" + R9_HOME_ANCHOR + b"</main>"
        r9 = add_r9_home(r8)
        r10 = add_home(r9)
        self.assertEqual(strip_current_entries(r10), r9)
        self.assertEqual(add_home(r10), r10)
        self.assertEqual(restore_r8_home(r10), r8)
        for altered in (r10 + HOME_ENTRY, r10.replace(b"./luoyang-city-layout.html", b"./wrong.html"),
                        r10.replace(HOME_ANCHOR + HOME_ENTRY, HOME_ENTRY + HOME_ANCHOR)):
            with self.subTest(altered=altered), self.assertRaises(ValueError):
                strip_current_entries(altered)

    def test_predecessor_context_comes_from_verified_exact_archived_bytes(self):
        info, files, before, prior = contract_fixture()
        restored, read = restore_r9_context(info, files.__getitem__)
        self.assertNotIn(KEY, restored)
        self.assertEqual(read("release.json"), files[RELEASE_ARCHIVE])
        self.assertEqual(json.loads(read("release.json")), prior)
        for page in HOME_PAGES:
            self.assertEqual(read(page), before[page])
            self.assertEqual(restored["files_sha256"][page], digest(before[page]))
        again, again_reader = restore_r9_context(restored, read)
        self.assertIs(again, restored)
        self.assertIs(again_reader, read)
        self.assertIn(KEY, info, "The caller's metadata must not be mutated")

    def test_recomputed_hashes_cannot_authorize_unrelated_release_or_home_edits(self):
        for kind in ("release", "home"):
            info, files, _, _ = contract_fixture()
            if kind == "release":
                data = json.loads(files["release.json"])
                data["unchanged"].append(4)
                files["release.json"] = encoded(data)
                info["files_sha256"]["release.json"] = digest(files["release.json"])
            else:
                files["index.html"] = files["index.html"].replace(b"<main>", b'<main data-unapproved="change">')
                checksum = digest(files["index.html"])
                info["files_sha256"]["index.html"] = checksum
                info[KEY]["homepage_after_sha256"]["index.html"] = checksum
                files[MANIFEST] = encoded(info[KEY])
                info["files_sha256"][MANIFEST] = digest(files[MANIFEST])
            with self.subTest(kind=kind), self.assertRaises(AssertionError):
                restore_r9_context(info, files.__getitem__)

    def test_archives_and_manifest_are_not_trusted_without_actual_byte_checks(self):
        for path in (MANIFEST, RELEASE_ARCHIVE, *HOME_ARCHIVES.values()):
            info, files, _, _ = contract_fixture()
            files[path] += b"\n"
            with self.subTest(path=path), self.assertRaises(AssertionError):
                restore_r9_context(info, files.__getitem__)

    def test_strict_pointer_handles_escaping_and_rejects_python_indexing(self):
        doc = {"a/b": {"~value": [{"answer": None}]}}
        self.assertIsNone(pointer(doc, "/a~1b/~0value/0/answer"))
        self.assertIs(pointer(doc, ""), doc)
        for path in ("a~1b", "/a~1b/~0value/-1", "/a~1b/~0value/00", "/a~1b/~0value/1",
                     "/a~1b/~0value/0/missing", "/a~2b", "/a~1b/~0value/0/answer/deeper"):
            with self.subTest(path=path), self.assertRaises(AssertionError):
                pointer(doc, path)


class R10DeliveredEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = ROOT / "_site"
        cls.info = json.loads((cls.site / "build-info.json").read_bytes())
        cls.meta = cls.info[KEY]
        cls.data = json.loads((cls.site / DATA).read_bytes())
        cls.inputs = {path: json.loads((cls.site / path).read_bytes()) for path in PUBLIC_INPUTS}

    def check_data(self, data=None, meta=None):
        return verify_data(data if data is not None else self.data,
                           meta if meta is not None else self.meta, self.info, self.inputs)

    def test_actual_release_passes_the_same_independent_live_verifier(self):
        requested = set()

        def public_read(path):
            self.assertNotEqual(path, ".nojekyll", "Production verifier tried to fetch a build-control file")
            requested.add(path)
            return (self.site / path).read_bytes()

        result = verify(self.info, public_read, build_control_reader=lambda path: (self.site / path).read_bytes())
        self.assertEqual(requested, set(self.info["files_sha256"]) - {".nojekyll"})
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["downloads"], 21)
        self.assertEqual(result["reversible_homepages"], 2)
        self.assertEqual(result["maps"]["overview"]["source_features"], 28)
        self.assertEqual(result["research"]["counts"]["coverage"], 339)
        self.assertEqual(result["research"]["counts"]["network_records"], 118)
        self.assertFalse(result["homepage_replacement_approved"])

    def test_all_eleven_regions_have_real_sources_and_keep_original_catalog_levels(self):
        result = self.check_data()
        self.assertEqual(result["counts"]["regions"], 11)
        self.assertGreaterEqual(result["counts"]["panels"], 22)
        self.assertGreaterEqual(result["counts"]["decisions"], 44)
        self.assertGreater(result["resolved_pointers"], result["counts"]["decisions"])
        self.assertEqual(result["original_placement_levels"], {"source": 11, "candidate": 1, "relative": 315, "unlocated": 12})

    def test_no_missing_objects_new_coordinates_or_silent_precision_upgrades(self):
        for mutation in ("drop", "identity", "grade", "coordinates", "network", "network_region", "network_basis", "source_binding"):
            data = copy.deepcopy(self.data)
            if mutation == "drop":
                data["coverage"].pop()
            elif mutation == "identity":
                data["coverage"][0]["id"] = "invented_ancient_site"
            elif mutation == "grade":
                row = next(row for row in data["coverage"] if row["level"] == "relative")
                row["level"] = "source"
            elif mutation == "coordinates":
                data["coverage"][0]["coordinates"] = [112.0, 34.0]
            elif mutation == "network":
                data["networks"][0]["original"]["id"] = "changed_identity"
            elif mutation == "network_region":
                row = next(row for row in data["networks"] if row["region_ids"] == ["register"])
                row["region_ids"] = ["R01"]
            elif mutation == "network_basis":
                row = next(row for row in data["networks"] if row["basis"] == "interpretation")
                row["basis"] = "source"
            else:
                row = next(row for row in data["coverage"] if not row["feature_ids"])
                row["feature_ids"] = ["geo-jianchun-gate"]
            with self.subTest(mutation=mutation), self.assertRaises(AssertionError):
                self.check_data(data)

    def test_research_claims_source_pointer_excerpt_and_uncertainty_cannot_drift(self):
        for mutation in ("pointer", "judgment", "uncertainty", "quote_kind", "excerpt", "registration"):
            data, meta = copy.deepcopy(self.data), copy.deepcopy(self.meta)
            if mutation == "pointer":
                data["regions"][0]["panels"][0]["nodes"][0]["source_inputs"][0]["pointer"] = "/evidence/-1"
            elif mutation == "judgment":
                data["decisions"][0]["judgment"] = "全部边界已测定"
            elif mutation == "uncertainty":
                data["decisions"][0]["remaining_unknown"] = "无"
            elif mutation == "quote_kind":
                data["decisions"][0]["source_evidence"][0]["excerpt_kind"] = "classical_text_quote"
            elif mutation == "excerpt":
                data["decisions"][0]["source_evidence"][0]["excerpt"] = "新增无来源原文"
            else:
                data["source_frames_registered_together"] = meta["source_frames_registered_together"] = True
            with self.subTest(mutation=mutation), self.assertRaises(AssertionError):
                self.check_data(data, meta)

    def test_source_hashes_protect_the_actual_research_files(self):
        data, meta = copy.deepcopy(self.data), copy.deepcopy(self.meta)
        path = next(iter(data["source_inputs_sha256"]))
        data["source_inputs_sha256"][path] = meta["source_inputs_sha256"][path] = "0" * 64
        with self.assertRaises(AssertionError):
            source_inputs(data, meta)

    def test_native_06a_geometry_and_every_region_figure_have_actual_semantic_targets(self):
        self.assertEqual(verify_svg((self.site / OVERVIEW).read_bytes(), self.data)["source_features"], 28)
        for rid, path in zip(REGIONS, SVGS[1:], strict=True):
            with self.subTest(region=rid):
                result = verify_svg((self.site / path).read_bytes(), self.data, rid)
                self.assertGreaterEqual(result["panels"], 2)
                self.assertGreaterEqual(result["linked_decisions"], 4)
        root = ET.fromstring((self.site / OVERVIEW).read_bytes())
        point = next(element for element in root.iter() if element.get("data-native-geometry") and element.tag.endswith("circle"))
        point.set("cx", str(float(point.get("cx")) + 1))
        with self.assertRaises(AssertionError):
            verify_svg(ET.tostring(root), self.data)
        root = ET.fromstring((self.site / SVGS[1]).read_bytes())
        edge = next(element for element in root.iter() if element.get("data-relation"))
        edge.set("data-source-inputs", "[]")
        with self.assertRaises(AssertionError):
            verify_svg(ET.tostring(root), self.data, "R01")

    def test_a_valid_but_unrelated_decision_anchor_does_not_count_as_source_traceability(self):
        region = self.data["regions"][0]
        item = region["panels"][0]["nodes"][0]
        sources = {(ref["path"], ref["pointer"]) for ref in item["source_inputs"]}
        unrelated = next(row for row in region["decisions"]
                         if not sources & {(ref["path"], ref["pointer"]) for ref in row["source_inputs"]}
                         and not set(item["entity_ids"]) & set(row["entity_ids"]))
        root = ET.fromstring((self.site / SVGS[1]).read_bytes())
        node = next(element for element in root.iter() if element.get("data-node") == item["id"])
        anchor = next(element for element in node.iter() if element.tag.endswith("}a"))
        anchor.set("data-decision", unrelated["id"])
        anchor.set("href", BASE + PAGE + "#decision-" + unrelated["id"])
        with self.assertRaises(AssertionError):
            verify_svg(ET.tostring(root), self.data, "R01")

    def test_all_four_csv_exports_match_every_published_projected_field(self):
        for kind, path in CSVS.items():
            with self.subTest(kind=kind):
                raw = (self.site / path).read_bytes()
                self.assertEqual(verify_csv(raw, self.data[kind], self.data["csv_fields"][kind]), len(self.data[kind]))
                changed = copy.deepcopy(self.data[kind])
                changed[0]["id"] = "missing-evidence"
                with self.assertRaises(AssertionError):
                    verify_csv(raw, changed, self.data["csv_fields"][kind])

    def test_page_keeps_full_no_javascript_evidence_and_exact_inline_figures(self):
        raw = (self.site / PAGE).read_bytes()
        document, figures = verify_page(raw, self.data, self.info["files_sha256"])
        self.assertEqual(len(figures), 12)
        self.assertEqual(len(set(document.downloads)), 21)
        first = self.data["decisions"][0]["id"]
        changed = raw.replace(('id="decision-' + first + '"').encode(), ('id="decision-' + first + '" hidden').encode(), 1)
        with self.assertRaises(AssertionError):
            verify_page(changed, self.data, self.info["files_sha256"])

    def test_recomputed_outer_zip_hash_cannot_hide_changed_offline_evidence(self):
        changed = io.BytesIO()
        with ZipFile(self.site / BUNDLE) as original, ZipFile(changed, "w", ZIP_DEFLATED) as archive:
            for name in original.namelist():
                raw = original.read(name)
                if name == CSVS["coverage"]:
                    raw += b"invented offline row\n"
                archive.writestr(name, raw)
        replacement = changed.getvalue()
        info = copy.deepcopy(self.info)
        info["files_sha256"][BUNDLE] = digest(replacement)

        def read(path):
            return replacement if path == BUNDLE else (self.site / path).read_bytes()

        with self.assertRaises(AssertionError):
            verify(info, read)

    def test_pdf_contains_thirteen_real_readable_pages_and_embedded_fonts(self):
        pdf = PdfReader(io.BytesIO((self.site / PDF).read_bytes()))
        self.assertEqual(len(pdf.pages), 13)
        self.assertEqual(len(pdf.outline), 13)
        self.assertIn("R10.1", str(pdf.metadata.get("/Title")))
        self.assertIn(self.info["source_commit"], str(pdf.metadata.get("/Keywords")))
        seen_fonts = set()
        for index, page in enumerate(pdf.pages):
            with self.subTest(page=index + 1):
                self.assertGreater(float(page.mediabox.width), 500)
                self.assertGreater(float(page.mediabox.height), 500)
                text = page.extract_text()
                self.assertGreater(len(text.strip()), 40)
                self.assertTrue(any("\u3400" <= char <= "\u9fff" for char in text), "Missing extractable Chinese text")
                if 1 <= index <= 11:
                    region = self.data["regions"][index - 1]
                    self.assertIn(region["id"], text)
                    compact = "".join(text.split())
                    self.assertIn("".join(region["title"].split()), compact)
                    for panel in region["panels"]:
                        for value in [panel["caption"], *(row["label"] for row in panel["nodes"]),
                                      *(row["label"] for row in panel["relations"])]:
                            self.assertIn("".join(value.split()), compact, (region["id"], "PDF lost figure text", value))
                    uris = set()
                    for annotation in page.get("/Annots", []):
                        action = annotation.get_object().get("/A")
                        if action:
                            action = action.get_object()
                            if action.get("/S") == "/URI":
                                uris.add(str(action["/URI"]))
                    self.assertLessEqual({BASE + PAGE + "#decision-" + row["id"] for row in region["decisions"]}, uris,
                                         "PDF evidence links do not correspond to regional decisions")
                resources = page["/Resources"].get_object()
                objects = resources.get("/XObject", {})
                if hasattr(objects, "get_object"):
                    objects = objects.get_object()
                self.assertFalse(any(ref.get_object().get("/Subtype") == "/Image" for ref in objects.values()),
                                 "Vector atlas page was replaced by a bitmap")
                fonts = resources.get("/Font", {})
                if hasattr(fonts, "get_object"):
                    fonts = fonts.get_object()
                for reference in fonts.values():
                    font = reference.get_object()
                    descendants = font.get("/DescendantFonts", [font])
                    for child in descendants:
                        child = child.get_object()
                        descriptor = child.get("/FontDescriptor")
                        if descriptor:
                            descriptor = descriptor.get_object()
                            self.assertTrue(any(name in descriptor for name in ("/FontFile", "/FontFile2", "/FontFile3")),
                                            "PDF font was not embedded")
                            seen_fonts.add(str(descriptor.get("/FontName")))
        self.assertTrue(seen_fonts)


if __name__ == "__main__":
    unittest.main()
