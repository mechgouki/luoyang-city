# Final main build evidence

This folder preserves `browser-build-evidence` artifact `14738890215` from main workflow run `44982066390`. Every report with a source field identifies the actual tested main commit `d7cd18a832e30e718dfd360b240c15b79927306b`.

The build job `137084513083` completed successfully. The original run/jobs snapshots were captured at build completion while the wider workflow was still running, so their filenames retain `build-completed`. The terminal production outcome belongs to the later `final-live` metadata; this build snapshot does not establish production acceptance by itself.

`artifact-selection.json` records the source ZIP SHA-256 and all 123 selected artifact members. These include all 49 browser reports and all 44 R7/R6.2/V12 PNGs, together with test/build/runtime summaries. Large terrain products and duplicate downloaded bodies were not selected.

`build-verification.json` records both R6 reports' six measurements: all 12 have `ready_state=complete` and satisfy the unchanged width assertion, with no document-width excess. `screenshot-comparison.json` compares every PNG to `readiness-pr` using its original bytes. It records a byte comparison, not a new manual inspection of every image.
