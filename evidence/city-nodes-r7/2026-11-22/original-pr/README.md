# Original PR #75 evidence subset

This folder preserves the original R7.1 pull-request checks before the final release fix. It **does not assert production acceptance**. The tested source is `6fae2767ca220a59e8357f2d4483ac57c32922be` (`refs/pull/75/merge`); the PR head is `9242bf54a6a45328d0d5a16633c063743de3219f`.

- `selection-manifest.json` lists the files retained here and their SHA-256 hashes. Original artifact members were checked byte-for-byte against the downloaded ZIP; API captures and derived summaries are marked separately.
- `acceptance-summary.json` is the unmodified earlier summary. Its `archive_inventory` describes the broader earlier extraction, so it is **not** the inventory of this selected folder. Use `selection-manifest.json` for this folder.
- `visual-review.json` records exactly which 16 screenshots were inspected and the limits of that inspection. The 36 original PNGs are preserved without resizing or re-encoding.
- The 49 browser reports and 21 Python semantic reports retain evidence for the previous research stages as well as R7. Browser check groups are not counted as individual assertions.
- Terrain rasters, duplicate downloaded data, built PDFs and the full Actions ZIP are omitted. They are not required to understand the selected original PR checks.

Final corrected PR, merged main, HTTPS resource verification and deployed browser results belong in separate sibling folders.
