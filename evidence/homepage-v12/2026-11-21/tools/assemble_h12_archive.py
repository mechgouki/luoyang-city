#!/usr/bin/env python3
"""Validate and preserve the complete H12 PR/live/public acceptance record.

No network, Git invocation, deployment, or repository writes. All inputs must
already exist. --pr-commit is the PR run's actual tested source_commit, which
may be a synthetic merge SHA rather than the pull request branch head.

Required workflow snapshot structure (original extra fields are retained):
  {"pr": {"tested_source_commit": "...", "run": {"id": 1,
           "status": "completed", "conclusion": "success"}, "jobs": [...]},
   "live": {"source_commit": "...", "run": {"id": 2, "head_sha": "...",
             "status": "completed", "conclusion": "success"}, "jobs": [...]}}
"production" may replace "live". Jobs must supply name/status/conclusion.
PR build must succeed; any PR deploy/verify-live jobs must be skipped. All
three production jobs must explicitly succeed. A URL is never proof of success.

Example, only after all actual acceptance evidence has arrived:
  python assemble_h12_archive.py --pr-commit TESTED_SHA --main-commit MAIN_SHA \
    --pr-run PR_RUN_ID --live-run LIVE_RUN_ID --workflow-snapshot workflows.json
"""

from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
BASE = "https://mechgouki.github.io/luoyang-city/"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def safe_relative(name):
    require(isinstance(name, str) and bool(name) and not any(c in name for c in "\\\x00\n\r"),
            f"Invalid archive path: {name!r}")
    require(not PurePosixPath(name).is_absolute() and ":" not in name
            and all(part not in ("", ".", "..") for part in name.split("/")),
            f"Unsafe archive path: {name!r}")
    return name


def inventory(directory):
    require(directory.is_dir() and not directory.is_symlink(), f"Missing or linked directory: {directory}")
    result = {}
    for path in sorted(directory.rglob("*")):
        require(not path.is_symlink(), f"Linked evidence refused: {path}")
        if path.is_dir():
            continue
        require(path.is_file(), f"Nonregular evidence refused: {path}")
        name = safe_relative(path.relative_to(directory).as_posix())
        result[name] = {"bytes": path.stat().st_size, "sha256": sha(path)}
    require(result, f"Empty evidence directory: {directory}")
    return result


def validate_checksums(directory, files):
    expected = {}
    for line in (directory / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  (.+)", line)
        require(match is not None, f"Malformed SHA256SUMS in {directory}")
        checksum, name = match.groups()
        safe_relative(name)
        require(name not in expected, f"Duplicate checksum entry: {name}")
        expected[name] = checksum
    require(set(expected) == set(files) - {"SHA256SUMS"}, f"Incomplete checksum inventory in {directory}")
    for name, checksum in expected.items():
        require(files[name]["sha256"] == checksum, f"Retained evidence hash changed: {directory / name}")


def validate_workflow(snapshot, phase, run_id, commit):
    key = phase if phase in snapshot else "production" if phase == "live" else phase
    record = snapshot.get(key)
    require(isinstance(record, dict), f"Workflow snapshot missing {phase}")
    run, jobs = record.get("run"), record.get("jobs")
    require(isinstance(run, dict) and isinstance(jobs, list), f"{phase}: run/jobs absent")
    require(str(run.get("id")) == str(run_id), f"{phase}: workflow run ID mismatch")
    require(run.get("status") == "completed" and run.get("conclusion") == "success",
            f"{phase}: actual workflow is not explicitly completed/success")
    if phase == "pr":
        require(record.get("tested_source_commit", record.get("source_commit")) == commit,
                "PR snapshot must bind the actual tested source_commit, not merely branch head")
    else:
        require(run.get("head_sha") == commit, "Live workflow head_sha does not match released main")
        require(record.get("source_commit", record.get("commit", run.get("head_sha"))) == commit,
                "Live snapshot source_commit mismatch")
    by_name = {}
    for job in jobs:
        require(isinstance(job, dict) and isinstance(job.get("name"), str), f"{phase}: invalid job")
        require(job["name"] not in by_name, f"{phase}: duplicate job name {job['name']}")
        by_name[job["name"]] = job
    required = {"build"} if phase == "pr" else {"build", "deploy", "verify-live"}
    require(required <= set(by_name), f"{phase}: required job missing")
    for name in required:
        job = by_name[name]
        require(job.get("status") == "completed" and job.get("conclusion") == "success",
                f"{phase}: {name} is not explicitly completed/success")
    if phase == "pr":
        for name in {"deploy", "verify-live"} & set(by_name):
            require(by_name[name].get("status") == "completed" and by_name[name].get("conclusion") == "skipped",
                    f"PR {name} must be skipped when present")
    return {"snapshot_key": key, "run_id": run_id,
            "run_url": f"https://github.com/mechgouki/luoyang-city/actions/runs/{run_id}",
            "source_commit": commit, "status": run["status"], "conclusion": run["conclusion"],
            "jobs": {name: {"status": job.get("status"), "conclusion": job.get("conclusion")}
                     for name, job in by_name.items()}}


def load_collector(path):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("h12_collector_for_archive", path)
    require(spec is not None and spec.loader is not None, "Cannot load evidence collector")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_phase(directory, phase, commit, run_id, collector):
    files = inventory(directory)
    validate_checksums(directory, files)
    meta = read(directory / "evidence-metadata.json")
    require(meta.get("schema") == "luoyang-homepage-v12-selected-evidence-v1", f"{phase}: metadata schema mismatch")
    require(meta.get("phase") == phase and meta.get("expected_source_commit") == commit, f"{phase}: metadata commit mismatch")
    require(meta.get("collection_validation") == "passed_for_selected_evidence", f"{phase}: evidence collection not passed")
    require(meta.get("hero_revision") == "panorama-approved-v12", f"{phase}: wrong homepage revision")
    require(meta.get("approved_source_png_sha256") == collector.SOURCE_PNG_SHA
            and meta.get("approved_webp_sha256") == collector.ASSET_HASHES, f"{phase}: approval identity mismatch")
    expected_url = f"https://github.com/mechgouki/luoyang-city/actions/runs/{run_id}"
    require(meta.get("workflow_url") in (None, expected_url), f"{phase}: collector workflow URL mismatch")
    approval, journey, allowed = collector.whitelist(phase)
    require(meta.get("whitelist") == sorted(allowed) and meta.get("selected_files") == len(allowed),
            f"{phase}: incomplete collected inventory")
    recorded = meta.get("files", [])
    require(isinstance(recorded, list) and len(recorded) == len(allowed), f"{phase}: metadata file inventory incomplete")
    require({item.get("path") for item in recorded} == allowed, f"{phase}: metadata file inventory differs")
    for item in recorded:
        require({k: item.get(k) for k in ("bytes", "sha256")} == files[item["path"]],
                f"{phase}: metadata file identity changed: {item['path']}")
    raw = {name: (directory / name).read_bytes() for name in allowed}
    # Reapply the collector's complete report, geometry, test and screenshot checks.
    audits, runtime = collector.validate(raw, phase, commit, approval, journey)
    require(audits == meta.get("report_validations") and runtime == meta.get("browser_runtime_digests"),
            f"{phase}: collector validation no longer matches retained metadata")
    report = json.loads(raw[approval + "/results.json"])
    return files, report, approval


def validate_production(directory, commit, pr_report, live_report, http, collector, verifier):
    files = inventory(directory)
    report = read(directory / "independent-live.json")
    require(report.get("status") == "passed" and not report.get("failure"), "Independent public verification did not pass")
    require(report.get("base_url") == BASE, "Unexpected public site")
    for key in ("expected_source_commit", "observed_source_commit", "ending_source_commit"):
        require(report.get(key) == commit, f"Public {key} mismatch")
    checks = report.get("checks", [])
    require(checks and all(x.get("status") == "passed" for x in checks), "Independent check missing or failed")
    require(report.get("runner_sha256") == sha(verifier), "Public verifier changed since its recorded run")
    index_record = report.get("response_index", {})
    require(index_record.get("path") == "response-index.json"
            and index_record.get("sha256") == files["response-index.json"]["sha256"], "Response index hash mismatch")
    index = read(directory / "response-index.json")
    require(index.get("expected_source_commit") == commit and index.get("base_url") == BASE,
            "Response index source/site mismatch")
    receipts = index.get("responses", [])
    require(isinstance(receipts, list) and receipts, "No actual public responses retained")
    require(report.get("response_count") == len(receipts), "Public response count mismatch")
    require(report.get("distinct_public_resources") == len({r.get("requested_path") for r in receipts}),
            "Public distinct resource count mismatch")
    seen, public_hashes = set(), {}
    for receipt in receipts:
        require(receipt.get("status") == "passed" and receipt.get("http_status") == 200, "Unsuccessful public response")
        saved = safe_relative(receipt.get("saved_response"))
        require(saved not in seen and saved in files, f"Missing/duplicate retained response: {saved}")
        seen.add(saved)
        require(files[saved] == {k: receipt.get(k) for k in ("bytes", "sha256")}, f"Response bytes changed: {saved}")
        requested = safe_relative(receipt.get("requested_path"))
        require(receipt.get("url") == BASE + requested, f"Unexpected response URL: {requested}")
        if requested != "build-info.json":
            require(receipt.get("matches_build_info") is True
                    and receipt.get("declared_sha256") == receipt["sha256"], f"Public hash did not match build-info: {requested}")
            require(requested not in public_hashes, f"Duplicate public body: {requested}")
            public_hashes[requested] = receipt["sha256"]
    for attempt in index.get("http_attempts", []):
        if "headers_file" in attempt:
            name = safe_relative(attempt["headers_file"])
            require(name in files and files[name]["sha256"] == attempt.get("headers_sha256"), f"HTTP headers changed: {name}")
    initial, ending = directory / "responses/build-info.json", directory / "responses/build-info.end.json"
    require(initial.read_bytes() == ending.read_bytes(), "Publication changed during independent verification")
    require(sha(initial) == report.get("build_info_sha256") == report.get("ending_build_info_sha256"), "build-info hash mismatch")
    info = read(initial)
    require(info.get("source_commit") == commit == http.get("commit"), "Public and live HTTP commits differ")
    require(all(info.get("files_sha256", {}).get(path) == checksum for path, checksum in public_hashes.items()),
            "Retained public response hashes differ from retained build-info")
    hero = report.get("homepage", {})
    require(hero.get("revision") == "panorama-approved-v12" and hero.get("label") == "全幅取景版", "Wrong public homepage")
    require(hero.get("source_image_sha256") == pr_report.get("source_png_sha256")
            == live_report.get("source_png_sha256") == collector.SOURCE_PNG_SHA, "PR/live/public source PNG identities differ")
    require(pr_report.get("asset_sha256") == live_report.get("asset_sha256") == collector.ASSET_HASHES,
            "PR and live browser image asset identities differ")
    http_hashes = {item["path"]: item["sha256"] for item in http["files"]}
    for path, checksum in collector.ASSET_HASHES.items():
        require(public_hashes.get(path) == http_hashes.get(path) == checksum,
                f"PR/live/public image bytes disagree: {path}")
    layout = hero.get("layout_asset")
    require(isinstance(layout, str) and layout in public_hashes
            and public_hashes[layout] == http_hashes.get(layout) == hero.get("layout_sha256"),
            "Public and live layout stylesheet hashes differ")
    for page in ("index.html", "v3.0-dual.html"):
        require(public_hashes.get(page) == http_hashes.get(page) == hero.get("entrances", {}).get(page, {}).get("sha256")
                and page in public_hashes, f"Public and live homepage HTML differs: {page}")
    return files, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pr-commit", required=True, help="Actual tested PR source_commit, including synthetic merge SHA where applicable")
    parser.add_argument("--main-commit", required=True)
    parser.add_argument("--pr-run", required=True, type=int)
    parser.add_argument("--live-run", required=True, type=int)
    parser.add_argument("--workflow-snapshot", required=True, type=Path)
    parser.add_argument("--source", type=Path, default=ROOT / "h12-evidence")
    parser.add_argument("--output", type=Path, default=ROOT / "h12-permanent")
    args = parser.parse_args(argv)
    for name in ("pr_commit", "main_commit"):
        value = getattr(args, name)
        require(re.fullmatch(r"[a-f0-9]{40}", value) is not None, f"{name}: full lowercase 40-hex SHA required")
    require(args.pr_run > 0 and args.live_run > 0, "Positive actual workflow run IDs required")
    source, output = args.source.resolve(), args.output.absolute()
    require(not output.exists() and not output.is_symlink(), f"Refusing existing archive: {output}")
    require(not output.resolve().is_relative_to(source) and not source.is_relative_to(output.resolve()), "Input/output directories overlap")
    repo = (ROOT / "luoyang-city").resolve()
    require(not output.resolve().is_relative_to(repo), "Archive output must be outside the repository")
    snapshot_path = args.workflow_snapshot.resolve()
    snapshot_raw = snapshot_path.read_bytes()
    snapshot = json.loads(snapshot_raw)
    workflows = {phase: validate_workflow(snapshot, phase, run, commit)
                 for phase, run, commit in (("pr", args.pr_run, args.pr_commit), ("live", args.live_run, args.main_commit))}
    collector_path, verifier_path = ROOT / "collect_h12_evidence.py", ROOT / "verify_h12_public.py"
    script_paths = (collector_path, verifier_path, Path(__file__).resolve())
    script_hashes = {path.name: sha(path) for path in script_paths}
    collector = load_collector(collector_path)
    inventories = {}
    inventories["pr"], pr, pr_folder = validate_phase(source / "pr", "pr", args.pr_commit, args.pr_run, collector)
    inventories["live"], live, live_folder = validate_phase(source / "live", "live", args.main_commit, args.live_run, collector)
    http = read(source / "live/live-http.json")
    inventories["production"], production = validate_production(source / "production", args.main_commit, pr, live, http, collector, verifier_path)
    require(set(pr["screenshots"]) == set(live["screenshots"]), "PR/live screenshot identities differ")
    screenshots = [{"name": name, "pr_sha256": checksum, "live_sha256": live["screenshots"][name],
                    "pr_live_identical": checksum == live["screenshots"][name]}
                   for name, checksum in sorted(pr["screenshots"].items())]
    stamp = datetime.now(timezone.utc)
    summary = {"schema": "luoyang-homepage-v12-acceptance-v1", "status": "passed",
               "recorded_at": stamp.isoformat(timespec="seconds"),
               "recorded_at_shanghai": stamp.astimezone(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
               "hero_revision": "panorama-approved-v12", "selection_label": "全幅取景版",
               "pr_tested_source_commit": args.pr_commit, "production_commit": args.main_commit,
               "source_png_sha256": collector.SOURCE_PNG_SHA, "asset_sha256": collector.ASSET_HASHES,
               "workflows": workflows, "public_hash_checked_files": http["checked_files"],
               "independent_public_responses": production["response_count"],
               "distinct_public_resources": production["distinct_public_resources"],
               "screenshots": screenshots, "reported_screenshot_hashes_verified": len(screenshots) * 2,
               "total_screenshots_retained": sum(name.endswith(".png") for phase in ("pr", "live") for name in inventories[phase]),
               "screenshot_comparison_policy": "Each report hash checked against its actual PNG; cross-phase equality recorded, not required or substituted for visual review.",
               "evidence_files": {phase: len(files) for phase, files in inventories.items()},
               "retention": "All files from all three validated input directories, including actual public response bodies and HTTP header records.",
               "workflow_provenance": "Original supplied GitHub workflow snapshot retained verbatim; explicit run and job success required.",
               "research_scope": "Homepage artwork/layout release only. Research evidence levels and unknown ancient endpoints are unchanged."}
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".h12-permanent-", dir=output.parent))
    try:
        for phase in ("pr", "live", "production"):
            shutil.copytree(source / phase, stage / phase)
            require(inventory(stage / phase) == inventories[phase], f"Evidence changed while copying {phase}")
        shutil.copy2(snapshot_path, stage / "github-workflows.json")
        require((stage / "github-workflows.json").read_bytes() == snapshot_raw, "Workflow snapshot changed since validation")
        (stage / "tools").mkdir()
        for path in script_paths:
            shutil.copy2(path, stage / "tools" / path.name)
            require(sha(stage / "tools" / path.name) == script_hashes[path.name], f"Script changed since validation: {path.name}")
        (stage / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        readme = f'''# 首页 V12「全幅取景版」验收档案

正式首页：{BASE}

本档案在全部输入校验通过后生成。首页版本 **panorama-approved-v12**；实际 PR 测试源为 `{args.pr_commit}`，正式发布提交为 `{args.main_commit}`。PR 与正式站的首页原图 SHA-256、两个 WebP 资源 SHA-256 已相互核对，并与独立 HTTPS 原响应核对。

## 实际运行

- PR：{workflows['pr']['run_url']}；快照明确记录 build 为 completed/success，若出现 deploy/verify-live 则必须为 completed/skipped。
- 正式站：{workflows['live']['run_url']}；快照明确记录 build、deploy、verify-live 均为 completed/success。
- 原始快照完整保存在 `github-workflows.json`。采集元数据中的 workflow_conclusion 不是工作流验收依据；本档案要求实际运行和作业记录明确成功。
- 正式 HTTP 清单验证 {http['checked_files']} 项资源；独立公开回读保留 {production['response_count']} 次原响应、{production['distinct_public_resources']} 项不同资源，以及首尾一致的 build-info。

## 文件

`pr/`、`live/`、`production/` 保留三个输入目录的全部文件；原报告、截图、响应体、响应索引和响应头记录均未重建或省略。`tools/` 保存实际采集脚本、独立 HTTPS 校验脚本及本归档脚本。`summary.json` 记录提交、资源哈希、截图比对和检查结果；根目录 `SHA256SUMS` 覆盖全部文件，除清单自身。

截图逐一与原报告或采集清单核验哈希。PR 与正式截图是否逐字节相同见 summary；哈希一致性不冒充人工视觉审阅。生成时间：{summary['recorded_at_shanghai']}（Asia/Shanghai）。

本次只发布用户批准的首页图和完整画幅布局；图像仍是研究性复原示意，已有道路、水系证据等级和未知端点不因画面替换而升级。
'''
        (stage / "README.md").write_text(readme, encoding="utf-8")
        checksums = inventory(stage)
        (stage / "SHA256SUMS").write_text("".join(f"{value['sha256']}  {name}\n" for name, value in sorted(checksums.items())), encoding="utf-8")
        validate_checksums(stage, inventory(stage))
        require(not output.exists() and not output.is_symlink(), f"Archive appeared during validation: {output}")
        stage.rename(output)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    print(json.dumps({"status": "passed", "archive": str(output), "files": len(checksums) + 1,
                      "main_commit": args.main_commit, "pr_run": args.pr_run, "live_run": args.live_run}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, AssertionError) as error:
        print(f"REFUSED: {error}\nNo final acceptance archive was produced.", file=sys.stderr)
        raise SystemExit(2)
