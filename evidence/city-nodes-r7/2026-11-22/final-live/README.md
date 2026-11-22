# Final production acceptance: main 557

Workflow run `44984166317` completed successfully for main source `557c468649d6919bd249ddd891b9c97cd37cf706`. Build, deployment, and `verify-live` all completed with `success`. The production verification job finished at 2026-11-22 04:32:14 UTC (12:32:14 Asia/Shanghai). Original terminal run/jobs API snapshots are retained here.

The original `live-acceptance-evidence` artifact is `14739119960`. `artifact-selection.json` records its raw ZIP hash and the 95 selected members: 49 browser reports, the HTTP report and runtime digest, and all 44 R7/R6.2/V12 PNGs. Original selected bytes are unchanged.

## Verified results

- `live-http.json` records `status=passed`, `checked_files=818`, and top-level `commit=557c468649d6919bd249ddd891b9c97cd37cf706`; its file record count is also 818.
- All ten R4/R5/R6/R6.2/R7 desktop/mobile reports pass and contain the expected 72 layout measurements. Every measurement records `ready_state=complete`, the unchanged tolerance (R4/R5: 0; R6/R6.2/R7: 1), and zero document-width excess. Every measured value and source-report hash appears in `family-layout-verification.json`.
- All 44 focus screenshots are byte-identical to `final-build`, recorded in `screenshot-comparison.json`. This comparison does not imply a new manual review of every image.
- All error arrays present in the 49 browser reports were read, including the legacy `runtime_errors` and `browser_errors` aliases, and are empty.

## Source attribution

`report-source-inventory.json` lists every browser report and its original source field. Seventeen reports explicitly record `source_commit`, all equal to main `557c468…`. The other 32 legacy reports have no commit field; they are associated through the successful workflow and the exact verified artifact. No missing source field or status was inserted into any original report. Original nested component provenance in the HTTP report is preserved separately from its top-level deployment commit.

The independent selected-content HTTP capture is preserved separately in `final-live-independent`. Earlier unsuccessful production attempts remain in their own source-specific directories and do not replace this successful acceptance evidence.
