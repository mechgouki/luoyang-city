# R12 Actions evidence tools

These tools are local and offline. They do not modify `/workspace/luoyang-r12`, use credentials, make requests, push a branch, or certify an image as historically correct. The root agent still owns collection, CI, publication, human review and final remote verification.

## Required actual artifacts

For a normal successful PR followed by production, collect five distinct artifacts immediately:

| Run | Artifact | Retention | Minimum retained content |
|---|---|---|---|
| Final PR | `github-pages` | 7 days | Full member identity ledger; actual build-info/release, V14 publication and predecessor files, both homepages |
| Final PR | `browser-build-evidence` | 14 days | Original tests, verification reports, all browser reports/screenshots/retained downloads, font and runtime evidence |
| Final production | `github-pages` | 7 days | Same selection, from production's actual artifact |
| Final production | `browser-build-evidence` | 14 days | Original build evidence, including production desktop/mobile downloads |
| Final production | `live-acceptance-evidence` | 30 days | Original live-http and browser reports/screenshots/retained downloads; runtime evidence |

Failed attempts are historical evidence too: keep their available reports and full logs without replacing them with later passes. These five are a minimum for a clean success chain, not a fixed expected count after reruns.

Outer Actions ZIPs and Pages TAR wrappers may be omitted from the permanent branch after their digest and all member identities are verified. Actual browser-downloaded ZIPs remain retained content. All original browser artifacts can share one content-addressed store; repeated paths and repeated bytes do not require separate physical copies.

Do not repeat the entire published site in multiple directories. The Pages ingest keeps every member's identity but stores the current V14 publication and metadata. It does not silently claim that every omitted old resource is unchanged. If using an unchanged-material exception from the existing R11 scope, separately compare that member's hash with a fixed previous archive commit and record the reference.

## Exact GitHub GET routes

Prefix: `https://api.github.com/repos/mechgouki/luoyang-city`.

| Purpose | Path |
|---|---|
| PR snapshot | `/pulls/{number}` |
| PR runs for actual head | `/actions/workflows/pages.yml/runs?event=pull_request&head_sha={sha}&per_page=100&page={page}` |
| Exact run | `/actions/runs/{run}` |
| Exact attempt jobs | `/actions/runs/{run}/attempts/{attempt}/jobs?per_page=100&page={page}` |
| Full job log | `/actions/jobs/{job}/logs` |
| Artifacts | `/actions/runs/{run}/artifacts?per_page=100&page={page}` |
| Exact artifact | `/actions/artifacts/{artifact}` |
| Artifact bytes | `/actions/artifacts/{artifact}/zip` |
| Git commit | `/git/commits/{sha}` |
| Git tree | `/git/trees/{tree}?recursive=1` |

Use the GitHub connector `fetch` for the JSON GET routes, `download_workflow_artifact` for ZIP bytes and `fetch_workflow_job_logs` for redirected logs. The connector's convenience run-jobs wrapper returns only the latest attempt's first page; the run-artifacts wrapper also returns only the first page. Use explicit GET routes when pagination or a historical attempt matters. A truncated recursive tree response requires subtrees.

**Observed connector limitation in this R12 run:** `github_fetch` rejects `/actions/workflows/pages.yml/runs` because its URL allowlist does not match that route. The route above documents the GitHub REST endpoint, not a successful connector call. For PR84, the root used `fetch_commit_workflow_runs` with the exact head to discover run `45165875123`, then `github_fetch /actions/runs/{id}` and `/actions/runs/{id}/attempts/{attempt}/jobs` to preserve raw evidence. The discovery wrapper filters to pull-request runs and only returns the first page; retain that limitation and do not represent it as a general paginated production-run collector.

The same wrapper also rejected `/actions/artifacts/{id}` during the first PR collection. `/actions/runs/{id}/artifacts` worked and returned the artifact digest, ID and expiry. Preserve that full raw response and select the exact artifact object from it, recording its pointer; do not claim a successful direct-artifact metadata fetch. `download_workflow_artifact` returned an authorized temporary `file_uri.download_url` on the OpenAI content host, which was downloaded normally in the executor. Preserve file ID, byte count, digest and host in the receipt; do not retain the temporary signed query string in the public archive.

For the production push, the root successfully used `/actions/runs?head_sha={PRODUCTION_SHA}&event=push&per_page=100` to discover run `45169490719`. This repository-wide run-list route is the observed working alternative to the rejected workflow-specific `pages.yml/runs` URL. Continue matching event, exact SHA and workflow path, and save the exact run afterward.

Preserve the raw JSON and logs. Extract `tested_merge_sha` from the build checkout log and require it to equal the actual Pages `source_commit`. Do not substitute run `head_sha` or a later PR merge-ref value. Verify its Git tree and parents. Compare production tree with the actual tested tree.

## Use

Save each artifact API object in its own JSON file, then download its exact ZIP through the connector. An API digest must match the ZIP before ingestion succeeds.

```bash
python /workspace/r12-evidence-tools/artifact_store.py \
  --zip /path/to/actual-pr-pages.zip --kind pages \
  --artifact-metadata /path/to/actual-pr-pages-api.json \
  --out /workspace/r12-evidence-store --label pr-RUN-aATTEMPT-pages

python /workspace/r12-evidence-tools/artifact_store.py \
  --zip /path/to/actual-pr-browser.zip --kind evidence \
  --artifact-metadata /path/to/actual-pr-browser-api.json \
  --out /workspace/r12-evidence-store --label pr-RUN-aATTEMPT-build
```

The same `--out` across all five archives deduplicates bytes. Each `ingests/LABEL.json` keeps original paths, bytes, SHA256 and Git blob IDs. Raw reports and downloads are unchanged in `objects/sha256/`. Ingestion rejects traversal, duplicate paths, links, nonregular files and digest mismatches. An ingest label cannot overwrite an earlier receipt.

The actual PR Pages TAR omitted the empty `.nojekyll` build control, although the site identity map listed its empty-byte hash. This is the explicit nonpublished build-control exception already present in `verify_live.py` and the release checklist. The collector records `empty_build_control_not_in_tar` only for that exact path with the SHA256 of empty bytes; other missing or changed files still fail. The initial strict collector stopped on this case, was corrected locally, and then reprocessed the unchanged actual artifact. It was not a CI failure or a change to release contents.

Check PR downloads against PR Pages only:

```bash
python /workspace/r12-evidence-tools/check_downloads.py \
  --store /workspace/r12-evidence-store \
  --pages /workspace/r12-evidence-store/ingests/pr-RUN-aATTEMPT-pages.json \
  --evidence /workspace/r12-evidence-store/ingests/pr-RUN-aATTEMPT-build.json \
  --report-prefix panorama-v14-browser --expected-commit TESTED_MERGE_40_SHA
```

Run the same checker for production build using production Pages and `panorama-v14-browser`, then production live using production Pages and `live-panorama-v14-browser`. It verifies both devices, full download sets derived from actual metadata, original retained bytes, report identities, click-attempt records and screenshot identities. Save its stdout as an additional check, not as a replacement for original reports.

Current image count, rejected findings and download count are deliberately not hardcoded. Image-review status is recorded separately from technical evidence checks.

Add raw API snapshots, complete job logs, root public readback bytes, human UI evidence, source/generation identities and the final README/acceptance/scope documents to the evidence tree. Required source files already frozen in the final production commit may be referenced by exact commit/path/hash; do not silently reference a moving branch.

Freeze the final tree before connector upload:

```bash
python /workspace/r12-evidence-tools/freeze_upload_manifest.py \
  --root /workspace/r12-evidence-store \
  --prefix evidence/panorama-r12/ACTUAL-DATE \
  --parent PRODUCTION_40_SHA \
  --output /workspace/r12-frozen-upload-manifest.json
```

The frozen upload manifest is outside its own input tree and includes all final index files. It provides file modes, SHA256, expected Git blob IDs and unique-byte totals for connector blob/tree/commit calls. It does not create a commit. The evidence commit must have final production as its only parent and add only the evidence prefix.

After upload, independently read the exact remote commit from a clean bare checkout or equivalent Git-object retrieval. Verify its one parent, complete tree, file modes, all actual bytes and index bytes against the frozen manifest; confirm main was not changed by archival. Keep this external readback result outside the frozen tree rather than repeatedly editing a self-referential archive.

## Validation performed on these tools

`smoke-check-result.json` records synthetic checks only: selective Pages retention, evidence deduplication, original download consistency, traversal rejection, wrong artifact digest rejection and retained-byte tampering rejection. No project/browser test was rerun and no remote resource was modified. Synthetic fixture paths must never be included as release evidence.

The underlying R11 permanent-archive precedent was read at fixed commit `b276f8e9495be7d4e8a38ddfa65ffc2bf9e85611`, path `evidence/city-plan-r11/2026-11-23/README.md`. Its exact original reports and fixed identity model are retained here; the local tools avoid copying its temporary paths or R11-specific download count.
