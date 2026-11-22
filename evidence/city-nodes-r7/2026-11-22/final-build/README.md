# Main 557 build evidence

This directory preserves `browser-build-evidence` artifact `14739451810` from main workflow run `44984166317`, actual tested source `557c468649d6919bd249ddd891b9c97cd37cf706`.

Build job `137090982244` completed successfully. The `build-completed-run.json` and `build-completed-jobs.json` API snapshots were taken while the wider production workflow was still running; they are explicitly build-completion snapshots. Production acceptance is established separately by the terminal workflow and public browser evidence in `final-live`.

The selected original artifact contains 123 members, including all 49 browser reports and all 44 R7/R6.2/V12 PNGs. Its raw ZIP and member checksums are recorded in `artifact-selection.json`. All source-bearing selected browser reports identify main `557c468…`.

`family-layout-verification.json` verifies all ten family reports and 72 recorded measurements. Every measurement is `ready_state=complete`, keeps the original tolerance (R4/R5: 0; R6/R6.2/R7: 1), and has zero document-width excess. `screenshot-comparison.json` records that all 44 focus PNGs are byte-identical to `family-readiness-pr`.

The comparisons preserve original image bytes and do not imply a fresh manual inspection of every image. No original artifact report was edited. The family verifier preserved in `family-readiness-pr` supports `--check-only` for a read-only recheck of these reports.
