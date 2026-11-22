# Intermediate production capture: 9599123

This folder preserves the independent HTTPS capture for source commit `9599123701766cbdfe5971095af638898f407efe`. It is an **intermediate release snapshot**, not final project acceptance.

The capture began at 2026-11-22 11:30:06 and ended at 11:30:53 Asia/Shanghai. Its 39 responses cover 38 distinct URLs. `http-capture.json` records the successful selected-content checks: matching opening/closing build-info bytes, 28-row / 30-column CSV, JSON counts, 13-member offline ZIP, and the fixed approved V12 image fingerprints. The original report and HTTP response bytes are unchanged.

The corresponding [workflow 44980204847](https://github.com/mechgouki/luoyang-city/actions/runs/44980204847) has successful build and deploy jobs, but a failed verify-live job. `workflow-status-at-archive.json` records the GitHub jobs observed while archiving. The word `passed` in `http-capture.json` applies only to that script's selected HTTP content checks. It does not assert that the complete production browser acceptance passed.

Keep a later corrected release in a separate evidence directory. Do not overwrite this snapshot with another commit's responses or use these response hashes to certify that later release.
