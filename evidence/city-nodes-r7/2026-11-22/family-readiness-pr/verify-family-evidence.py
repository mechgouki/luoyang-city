"""Validate completed PR78-family reports and compare original screenshot bytes.

This checks a supplied evidence directory only. It does not infer workflow or
production acceptance and does not edit any original reports or screenshots.
"""
import argparse
import hashlib
import json
from pathlib import Path


FAMILIES = {
    "R4": ("city-atlas-r4-browser", 0, 3),
    "R5": ("city-panorama-r5-browser", 0, 5),
    "R6": ("road-atlas-r6-browser", 1, 6),
    "R6.2": ("all-road-atlas-r62-browser", 1, 8),
    "R7": ("city-nodes-r7-browser", 1, 14),
}
FOCUS = {"city-nodes-r7-browser", "all-road-atlas-r62-browser", "homepage-approved-v9-browser"}


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-source", required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--check-only", action="store_true", help="Validate without writing any derived reports")
    args = parser.parse_args()
    root = args.root.resolve()
    baseline = args.baseline.resolve()
    assert root.is_dir() and baseline.is_dir()
    assert len(args.expected_source) == 40 and all(c in "0123456789abcdef" for c in args.expected_source)
    prefix = "live-" if args.live else ""
    layout_output = root / "family-layout-verification.json"
    screenshot_output = root / "screenshot-comparison.json"
    if not args.check_only:
        assert not layout_output.exists() and not screenshot_output.exists(), "Use fresh derived output names or --check-only"
    reports = []
    for family, (folder, tolerance, expected_count) in FAMILIES.items():
        for device in ("desktop", "mobile"):
            path = root / (prefix + folder) / (device + "-report.json")
            raw = path.read_bytes()
            report = json.loads(raw)
            assert report["status"] == "passed" and not report["errors"], str(path)
            assert report["source_commit"] == args.expected_source, str(path)
            checks = report["layout_checks"]
            assert len(checks) == expected_count, (str(path), len(checks), expected_count)
            for item in checks:
                assert item["ready_state"] == "complete", (str(path), item)
                assert item["tolerance"] == tolerance, (str(path), item)
                assert item["document_width"] <= item["inner_width"] + tolerance, (str(path), item)
            reports.append(dict(
                family=family, device=device, path=path.relative_to(root).as_posix(),
                report_sha256=sha256(raw), status=report["status"],
                source_commit=report["source_commit"], expected_layout_checks=expected_count,
                actual_layout_checks=len(checks), original_width_tolerance=tolerance,
                all_ready_state_complete=True,
                maximum_document_minus_inner_width=max(c["document_width"] - c["inner_width"] for c in checks),
                layout_checks=checks,
            ))
    selected_pngs = sorted(p for p in root.rglob("*.png") if p.parent.name.removeprefix("live-") in FOCUS)
    assert len(selected_pngs) == 44, ("Expected all R7/R6.2/V12 PNGs", len(selected_pngs))
    comparisons = []
    for path in selected_pngs:
        relative = path.relative_to(root)
        original_folder = relative.parts[0].removeprefix("live-")
        baseline_path = baseline / original_folder / path.name
        raw = path.read_bytes()
        prior = baseline_path.read_bytes()
        comparisons.append(dict(
            path=relative.as_posix(), baseline_path=baseline_path.relative_to(baseline).as_posix(),
            current_sha256=sha256(raw), baseline_sha256=sha256(prior), byte_identical=raw == prior,
        ))
    layout = dict(
        schema="luoyang-atlas-family-layout-verification-v1",
        actual_tested_source_commit=args.expected_source,
        evidence_mode="public-live" if args.live else "build-or-pr",
        release_acceptance="not_asserted_by_this_report_verification",
        scope="Exact recorded measurements in ten completed browser reports. Source, nonempty coverage, PR78 call counts, readyState, and unchanged original tolerances checked.",
        expected_coverage_origin="PR78 source: per device R4=3, R5=5, R6=6, R6.2=8, R7=14. R6.2 includes two return links; R7 includes two homepage entries and four node round trips.",
        totals=dict(reports=len(reports), layout_checks=sum(r["actual_layout_checks"] for r in reports)),
        reports=reports,
    )
    screenshots = dict(
        schema="luoyang-evidence-screenshot-comparison-v1",
        actual_tested_source_commit=args.expected_source, baseline_directory=baseline.name,
        method="Exact original PNG bytes and SHA-256; no image re-encoding.",
        compared=len(comparisons), byte_identical=sum(r["byte_identical"] for r in comparisons),
        changed=[r["path"] for r in comparisons if not r["byte_identical"]], files=comparisons,
        manual_visual_review="Byte comparison only; changed images require separate manual review. Prior manual observations are recorded separately.",
        release_acceptance="not_asserted_by_this_comparison",
    )
    if not args.check_only:
        layout_output.write_text(json.dumps(layout, ensure_ascii=False, indent=2) + "\n")
        screenshot_output.write_text(json.dumps(screenshots, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(layout_totals=layout["totals"], screenshots_compared=len(comparisons),
                          screenshots_identical=screenshots["byte_identical"], changed=screenshots["changed"])))


if __name__ == "__main__":
    main()
