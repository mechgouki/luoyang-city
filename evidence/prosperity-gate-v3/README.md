# P3 Changhe gate: durable acceptance evidence

This archive records the completed publication of PR #29 at production commit `a52b28be7063fb30fb7c3c81375bf9ec05cb5dea`.
The published topic is `prosperity-gate.html`: ten source-backed components, three research views, a three-page atlas, source/metric readings and documented limits on city registration.

## Source and workflow provenance

- Accepted PR head: `747932370d9c1113ddc1b2dae6a0e65661e573ee`.
- Actual tested PR merge: `eea118a1adb6c4c782230b2c0545f6e4f50a92be`.
- Production merge: `a52b28be7063fb30fb7c3c81375bf9ec05cb5dea`.
- All three source trees are `c243415b440f9199ddfe5cbd23b1cc019b4a44e3`.
- Accepted PR run: [43731134315](https://github.com/mechgouki/luoyang-city/actions/runs/43731134315).
- Production run: [43731735963](https://github.com/mechgouki/luoyang-city/actions/runs/43731735963).

| Production job | ID | Result |
| --- | ---: | --- |
| build | 132865465910 | success |
| deploy | 132866771695 | success |
| verify-live | 132866880112 | success |

Official commit, run, job, artifact and source-tree objects and the accepted workflow source are retained in `metadata/`.

## Accepted checks

The accepted PR and production builds each passed **261 Python tests and 5 Node tests**. The original Python test reports and timestamped Node TAP excerpts are retained separately from the generated summary.

| Browser phase | Suites | Passed checks | Reported errors |
| --- | ---: | ---: | ---: |
| pr | 17 | 248 | 0 |
| production-build | 17 | 248 | 0 |
| live | 17 | 248 | 0 |

P3 contributes nine browser check groups. Its original result file is `report.json`; earlier suites use `results.json`. Both contracts are counted. Pointer/keyboard selection, camera controls, source-layer state, deep links, browser history, downloads, mobile use, no-JavaScript reading and failed-data-request fallback are exercised.

The actual HTTPS acceptance report is `live/live-http.json`; it records **469 resources**. Independent HTTP sampling separately checked **26 resources / 73 assertions**, including the native JPEG, all three SVGs, PDF, ZIP and the reversible HTML archive chain. Raw JSON/HTML responses and HTTP headers, sizes and SHA-256 values are under `public/`.

The parent's separate 17-resource public check is preserved unchanged in `metadata/parent-public-asset-verification.json`. Its `build_manifest_sha256` hashes a sorted-key JSON representation. The independent sample's HTTP record for `build-info.json` hashes the exact response bytes; these are different, explicitly labeled quantities.

## Prior validation failures retained

1. Run **43729698896** stopped in the existing P1 drag test. The map's unscrolled drag coordinates fell below the 1000 px viewport after the added entry block. `pr-attempt1/` retains the original results and first-screen image; `metadata/pr-attempt1-*` retains official objects, the original exception excerpt and the bounded coordinate analysis. The correction scrolls the real map into view and verifies pointer hit targets before retaining the same viewBox-change/reset assertions. P2/P3 had not run.
2. Run **43730476238** passed the previous 16 browser suites / 239 checks, then stopped before P3's first check group because the Python harness called `Locator.first` as a function. `pr-attempt2/` and matching metadata preserve the original zero-check P3 report and exception. All three calls were corrected to properties. P3 was moved first for quicker feedback; no earlier suite or assertion was removed.

These directory labels identify successive PR validation revisions. Both failed GitHub runs themselves have `run_attempt: 1`; neither is represented as the accepted final run.

## Original screenshot review

Five original P3 screenshots are retained for each successful browser phase. Root reviewed the PR desktop plan, city diagram and mobile source-off/west-que state; the interface agent reviewed all five, including diagnostics and no-JavaScript output. The map panels, source notes and controls remain within their intended layout, and the city registration annotation does not obscure the que traces. Mobile diagram detail is available through zoom and the full-SVG link.

`metadata/screenshot-comparisons.json` records exact byte and pixel differences without altering images. PR-to-production differences in the three full-page captures are confined to the short commit label in the footer; the city and diagnostics workspace captures are byte-identical. Actual live-to-build comparisons are recorded separately in that file.

## Download and archive integrity

Every complete evidence ZIP was verified against GitHub's official artifact digest before extraction.

| Artifact ID | Verified ZIP SHA-256 |
| --- | --- |
| 14168250726 | `4d8c9934cefa41a19413dc046aa3ce0a3a55995e42c7f833dd2747c66160e6c6` |
| 14167774972 | `f34b6d32a4063d4572604821a504cb135ee840305720a60182abe047bc70c756` |
| 14168436875 | `4a1831f5b136382493671fcab04daf449f6cffaf35dd6cc128ce27bc02f7fd68` |
| 14168947141 | `2dc482698984b04e9f7fa5c1b05cd8d619630e7345692589adfb2beea46f590c` |
| 14168927969 | `2a19b659b327b3f25bb6fea43a82eee6af5004ab92e3bd56e27f9a35bea60848` |

Original expiry dates are retained in the artifact metadata. Large ZIP files, Pages packages and unrelated screenshots are not committed. `SHA256SUMS` covers every other archive file; all uploaded Git blob IDs are separately compared with the local original bytes before the evidence branch is created.

## Historical and publication boundaries

The image-local metre conversion, table-listed dimensions and generalized city anchor remain separate. City registration is unsolved, common controls remain zero, and no new ancient absolute coordinates, external true-north solution, historical building height, roof or ancient ground surface is asserted. Open que traces and source dashes retain their original evidence status. The four older HTML pages have exact before-P3 archives, and **444 earlier assets** remain protected.

This is evidence of the P3 research interface and its publication. It does not turn the interim homepage panorama into a final aesthetic approval or certify a completed reconstruction of the whole prosperous city.
