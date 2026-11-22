# Main d7 production browser failure

Main source `d7cd18a832e30e718dfd360b240c15b79927306b`, workflow run `44982066390`, completed with overall conclusion `failure`. Build and deployment succeeded; the HTTP verification passed. The production browser job then failed in the legacy R6.2 atlas's first `fits(page)` width assertion. Its R6 predecessor completed successfully in this attempt.

The original R6.2 desktop report and failure PNG are preserved under `live-all-road-atlas-r62-browser`. The report has no successful check groups and records `status=failed`; it does not record the actual width or `document.readyState` at the assertion. The screenshot is a later capture and cannot alone establish the layout state at the exact failing measurement.

`artifact-selection.json` identifies the raw Actions ZIP, its SHA-256, and every selected member. All available browser reports, the HTTP report, runtime digest, and the failure PNG are retained unchanged. Terminal workflow/jobs API snapshots and the complete production verification job log are also retained. This partial attempt stopped before the R7 and V12 browser tests and is not full live acceptance.

The same source's successful build subset is preserved separately in `main-d7-build`; its successful independent public HTTP capture is in `main-d7-independent`. Those successful subsets do not change this workflow's failed outcome.
