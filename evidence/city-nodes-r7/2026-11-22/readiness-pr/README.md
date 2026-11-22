# PR77 readiness evidence

This folder preserves the successful build and browser evidence from PR #77, workflow run `44981414863`, artifact `14738590169` (`browser-build-evidence`). It is PR evidence, not production acceptance.

- PR head: `87a2b52cbd5ae3923f30ca9221c4d88bd769ecc8`.
- Actual tested checkout (`refs/pull/77/merge`): `3fa80ae293a753b2c04bfe98e83b249229ab123c`.
- The preserved `pull-request-77.json` is the authentic pre-merge snapshot.
- The extracted artifact has 123 selected members: all 49 browser reports, 44 R7/R6.2/V12 PNGs, and other selected test/build/runtime summaries. Exact ZIP provenance and member checksums are in `artifact-selection.json`.
- Both R6 reports contain six layout measurements. All 12 show `ready_state=complete`, zero document-width excess, zero body margin, and map overflow `auto`. Desktop width is 1440; mobile width is 390. The unchanged assertion remains `document_width <= inner_width + 1`. See `readiness-verification.json` and the original reports for every measurement.
- All 44 PNGs are byte-identical to their counterparts in both `merge-build` and `corrected-pr`. `screenshot-comparison.json` records every SHA-256 pair. This byte comparison does not imply a new manual inspection of every image.

The extractor's `corrected-pr` stage is its generic PR-correction category. The actual PR number, workflow run, artifact ID, checkout commit, and this folder name distinguish PR77 from the earlier PR76 correction. A successful final production workflow and independent public response capture are recorded separately.
