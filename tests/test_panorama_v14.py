"""Guard candidate identity, unapproved state and exact predecessor restoration."""
import copy
import io
import json
from pathlib import Path
import sys
import unittest

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from panorama_v14 import (WEBP_CONVERSION, encode_candidate_webp, validate_record,
                         validate_record_review_state, validate_review_identity, validate_webp_derivatives)
from panorama_v14_contract import (KEY, SOURCE_RECORD, HOME_ENTRY, REJECTED_HOME_ENTRY,
                                  home_entry, add_home, strip_current_entries, restore_r11_context)
from city_plan_r11_contract import HOME_ENTRY as R11_ENTRY
from panorama_v14_page import make_page
from panorama_v14_verify import verify, verify_review_presentation


class CandidateContract(unittest.TestCase):
    def test_rejects_same_size_webp_from_another_image_or_mobile_shift(self):
        def png(image):
            stream = io.BytesIO()
            image.save(stream, format="PNG")
            return stream.getvalue()

        first = Image.new("RGB", (1000, 562), "#276655")
        first.paste("#e9b667", (0, 0, 400, 562))
        source = png(first)
        expected = encode_candidate_webp(source)
        validate_webp_derivatives(source, copy.deepcopy(WEBP_CONVERSION), expected)
        other = encode_candidate_webp(png(Image.new("RGB", first.size, "#6b3784")))
        shifted = ImageChops.offset(first, 130, 0).resize((960, round(562 * 960 / 1000)), Image.Resampling.LANCZOS)
        stream = io.BytesIO()
        shifted.save(stream, format="WEBP", quality=92, method=6, lossless=False, exact=False,
                     exif=b"", icc_profile=b"", xmp=b"")
        for scale, wrong in (("full", other["full"]), ("small", stream.getvalue())):
            changed = dict(expected, **{scale: wrong})
            with Image.open(io.BytesIO(expected[scale])) as wanted, Image.open(io.BytesIO(wrong)) as actual:
                self.assertEqual(actual.size, wanted.size)
            with self.subTest(scale=scale), self.assertRaisesRegex(AssertionError, "not derived from this exact PNG"):
                validate_webp_derivatives(source, copy.deepcopy(WEBP_CONVERSION), changed)

    def test_rejects_stale_or_unaccepted_independent_visual_audit(self):
        source_hash = "5f" * 32
        valid = dict(source_png_sha256=source_hash, homepage_replacement_approved=False,
                     review_status="accepted_for_user_review_with_known_limits", blocking_findings=[])
        validate_review_identity(valid, source_hash, "Independent visual audit")
        for key, value in (("source_png_sha256", "0" * 64), ("homepage_replacement_approved", True),
                           ("review_status", "failed"), ("blocking_findings", ["Wrong temple attachment"])):
            with self.subTest(field=key), self.assertRaises(AssertionError):
                validate_review_identity(dict(valid, **{key: value}), source_hash, "Independent visual audit")

    def test_new_home_link_is_unique_exact_and_reversible(self):
        before = b"<main>" + R11_ENTRY + b"</main>"
        for status in ("candidate_for_review", "needs_revision"):
            entry = home_entry(status)
            after = add_home(before, status)
            self.assertEqual(strip_current_entries(after), before)
            self.assertEqual(add_home(after, status), after)
            self.assertEqual(add_home(add_home(before), status), after)
            altered = [after + entry, after + (HOME_ENTRY if status == "needs_revision" else REJECTED_HOME_ENTRY),
                       after.replace(b"./luoyang-panorama-v14.html", b"./other.html"),
                       after.replace(R11_ENTRY + entry, entry + R11_ENTRY)]
            for raw in altered:
                with self.subTest(status=status, raw=raw), self.assertRaises(AssertionError):
                    strip_current_entries(raw)
            unrelated = after.replace(b"<main>", b'<main data-unexpected="true">')
            self.assertNotEqual(strip_current_entries(unrelated), before)

    def test_legacy_home_readers_remove_only_the_new_exact_entry(self):
        from city_layout_r10_contract import HOME_ENTRY as R10_ENTRY
        from panorama_v13_r2_contract import HOME_ENTRIES as R9_ENTRIES
        from panorama_v13_contract import HOME_ENTRY as R8_ENTRY
        from city_plan_r11_contract import strip_current_entries as strip_r11
        from city_layout_r10_contract import strip_current_entries as strip_r10
        before = b"<main>" + R8_ENTRY + R9_ENTRIES + R10_ENTRY + R11_ENTRY + b"</main>"
        for status in ("candidate_for_review", "needs_revision"):
            after = add_home(before, status)
            self.assertEqual(strip_r11(after), before.replace(R11_ENTRY, b""))
            self.assertEqual(strip_r10(after), before.replace(R11_ENTRY, b"").replace(R10_ENTRY, b""))
            with self.assertRaises(AssertionError):
                strip_r10(after.replace(b"./luoyang-panorama-v14.html", b"./other.html"))

    def test_rejected_trial_requires_matching_states_and_every_review_blocker(self):
        source_hash = "2a" * 32
        primary = dict(source_png_sha256=source_hash, homepage_replacement_approved=False,
                       review_status="rejected_needs_revision", blocking_findings=["南门只可辨两层。"])
        audit = dict(primary, blocking_findings=["南门只可辨两层。", "门基偏离共同底稿。"])
        record = dict(status="needs_revision", review_status="rejected_needs_revision",
                      source_png_sha256=source_hash, blocking_findings=list(audit["blocking_findings"]))
        state = validate_record_review_state(record, primary, audit)
        self.assertEqual(state["status"], "needs_revision")
        self.assertEqual(state["blocking_findings"], audit["blocking_findings"])
        cases = [
            (dict(record, status="candidate_for_review"), primary, audit),
            (dict(record, review_status="accepted_for_user_review"), primary, audit),
            (dict(record, blocking_findings=primary["blocking_findings"]), primary, audit),
            (record, dict(primary, blocking_findings=[]), audit),
            (record, primary, dict(audit, blocking_findings=[])),
            (record, primary, dict(audit, review_status="accepted_for_user_review")),
            (record, primary, dict(audit, source_png_sha256="0" * 64)),
            (record, primary, dict(audit, blocking_findings=[{}])),
        ]
        for changed_record, changed_primary, changed_audit in cases:
            with self.subTest(record=changed_record, audit=changed_audit), self.assertRaises(AssertionError):
                validate_record_review_state(changed_record, changed_primary, changed_audit)
        accepted = dict(primary, review_status="accepted_for_user_review", blocking_findings=[])
        state = validate_record_review_state(dict(status="candidate_for_review", source_png_sha256=source_hash), accepted, accepted)
        self.assertEqual(state["blocking_findings"], [])

    def test_rejected_page_exposes_exact_blockers_before_image_without_script(self):
        candidate = dict(status="needs_revision", alt="未通过的试绘样张", remaining_limits=["外部落位未验证。"], changes=[
            dict(id="south-gate", title="南门试改", treatment_type="attempted_not_accepted",
                 observation="南门只可辨两层。", evidence="文献要求三重。", change="试改尚未达到要求。",
                 limitation="层高仍未量得。", evidence_links=[dict(label="来源", url="https://example.org/source")])])
        images = {kind: dict(full=kind + ".webp", small=kind + "-small.webp", width=1672, height=941,
                             revision=kind) for kind in ("v14", "v13r2", "v12")}
        data = dict(candidate=candidate, images=images, supporting_assets=[], source_png="source.png",
                    status="needs_revision", review_status="rejected_needs_revision", blocking_findings=["南门只可辨两层。", "门基偏离共同底稿。"])
        html = make_page(data, [data["source_png"], images["v14"]["full"]])
        result = verify_review_presentation(html, data)
        self.assertEqual(result["visible_blocking_findings"], 2)
        self.assertLess(html.index('id="blocking-findings"'), html.index('id="comparison"'))
        for changed in (html.replace('id="blocking-findings"', 'id="blocking-findings" hidden'),
                        html.replace('<li data-blocking-index="1">门基偏离共同底稿。</li>', ''),
                        html.replace('V14试绘审查·未通过', 'V14 空间校正已通过'),
                        html.replace('alt="未通过的试绘样张"', 'alt="已完成空间校正的全景"'),
                        html.replace('下载未通过试绘、底稿与审查依据', '下载已完成全景与依据'),
                        html.replace('未通过试绘原始 PNG', '最终首页原始 PNG'),
                        html.replace('未通过试绘全幅 WebP', '最终首页全幅 WebP'),
                        html.replace('data-image-status="needs_revision"', 'data-image-status="candidate_for_review"')):
            with self.subTest(markup=changed[:100]), self.assertRaises(AssertionError):
                verify_review_presentation(changed, data)
        accepted = copy.deepcopy(data)
        accepted.update(status="candidate_for_review", review_status="accepted_for_user_review", blocking_findings=[])
        accepted["candidate"]["status"] = "candidate_for_review"
        accepted["candidate"]["changes"][0]["treatment_type"] = "changed"
        self.assertEqual(verify_review_presentation(make_page(accepted, []), accepted)["visible_blocking_findings"], 0)

    def test_candidate_rejects_approval_identity_crop_and_missing_projection(self):
        record = json.loads((ROOT / SOURCE_RECORD).read_bytes())
        validate_record(record)
        attempts = [(["homepage_replacement_approved"], True), (["status"], "approved"),
                    (["source_png_sha256"], "0" * 64), (["source_image", "sha256"], "0" * 64),
                    (["small", "height"], record["small"]["height"] * 2),
                    (["supporting_assets"], [x for x in record["supporting_assets"] if x["role"] != "projection_data"])]
        for path, value in attempts:
            changed = copy.deepcopy(record)
            parent = changed
            for key in path[:-1]:
                parent = parent[key]
            parent[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(AssertionError):
                validate_record(changed)
        changed = copy.deepcopy(record)
        changed["supporting_assets"][0]["sha256"] = "0" * 64
        with self.assertRaises(AssertionError):
            validate_record(changed)


class CandidateDelivery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = ROOT / "_site"
        cls.info = json.loads((cls.site / "build-info.json").read_bytes())

    def test_actual_candidate_guides_and_preserved_publication(self):
        read = lambda p: (self.site / p).read_bytes()
        result = verify(self.info, read, build_control_reader=read)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["homepage_revision"], "panorama-approved-v12")
        self.assertFalse(result["homepage_replacement_approved"])
        self.assertFalse(result["field_registration_verified"])
        self.assertEqual(result["reversible_homepages"], 2)
        self.assertGreaterEqual(result["projection_guides"], 2)
        self.assertEqual(result["image_status"], self.info[KEY]["status"])
        self.assertEqual(result["image_review_status"], self.info[KEY]["review_status"])
        self.assertEqual(result["image_accepted_for_user_review"], self.info[KEY]["status"] == "candidate_for_review")
        self.assertEqual(result["visible_blocking_findings"], len(self.info[KEY]["blocking_findings"]))

    def test_old_r11_receives_its_complete_exact_inventory(self):
        from city_plan_r11_verify import verify as verify_r11
        read = lambda p: (self.site / p).read_bytes()
        old, reader = restore_r11_context(self.info, read)
        self.assertNotIn(KEY, old)
        self.assertNotIn("luoyang-panorama-v14.html", old["files_sha256"])
        self.assertEqual(json.loads(reader("release.json"))["current_milestone"], "盛时 R11.1 · 全城统一坐标复原工作平面")
        result = verify_r11(self.info, read, build_control_reader=read)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["same_geometry_views"], 16)

    def test_changed_new_or_old_bytes_and_unauthorized_home_edit_are_rejected(self):
        meta = self.info[KEY]
        paths = [meta["images"]["v14"]["full"], meta["source_png"], meta["supporting_assets"][0]["published_path"],
                 "city-plan-r11/plan.json", "panorama-v13-r2/v13r2.webp", "release.json", "index.html"]
        for target in paths:
            def changed(path):
                raw = (self.site / path).read_bytes()
                return raw + b"tampered" if path == target else raw
            with self.subTest(path=target), self.assertRaises(AssertionError):
                verify(self.info, changed)


if __name__ == "__main__":
    unittest.main()
