# Homepage interim v8: durable acceptance evidence

This archive records the publication of PR #28, with production source commit `bd87e471d292a76efbf6bde74c4b77e8f3040c68`.
The image is explicitly **interim**. The user authorized temporary use while remaining dissatisfied with the visual design; publication and webpage presentation checks do not constitute final aesthetic approval.

## Source provenance

- PR head: `1baafefc93a29e7d18e43551348de3958fd286ec`.
- Actual PR tested merge: `719a21047955e158c344157ee6faac9d672028f3`.
- Production merge: `bd87e471d292a76efbf6bde74c4b77e8f3040c68`.
- All three commits have source tree `457b88f6befc536053a100a73a7b50c52ba3037b`.
- Official commit objects, workflow source, runs, jobs and artifact metadata are retained in `metadata/`.

## Accepted runs

| Phase | Run ID | Conclusion |
| --- | ---: | --- |
| pr | 43728326687 | success |
| production | 43728787251 | success |

Both builds passed 249 Python tests and 5 Node tests. The original Python reports and timestamped Node TAP excerpts remain separately readable.

Production attempt 1 deployed successfully and passed all 448 HTTPS resource checks, then stopped during `tests/browser_v30.py`: a GET of the existing `terrain/v3.0/ams-ni49-8.jpg` exceeded the 30-second request timeout. The later homepage suite had not run. The failed job was rerun on the same commit without changing source or removing tests. Original failed-attempt reports and logs remain under `live-attempt1/` and `metadata/production-attempt1-*`; the accepted final run is attempt 2.

| Browser phase | Suites | Passed checks | Runtime errors |
| --- | ---: | ---: | ---: |
| pr | 16 | 239 | 0 |
| production-build | 16 | 239 | 0 |
| live | 16 | 239 | 0 |

`live/` contains reports from the actual HTTPS deployment. `public/` contains separately retrieved build/release/homepage metadata and an independent check of the production commit, image hashes, visible homepage references and preserved research entry points. See `summary.json` for exact paths and totals.

## Download integrity

Each complete evidence ZIP was checked against GitHub's official artifact digest before extraction.

| Artifact ID | Verified ZIP SHA-256 |
| --- | --- |
| 14166593991 | `b9867f4bbff6150bde6a54b12bfed1a55aea8daf02b372be658004eb4a4f7828` |
| 14167796614 | `94b16b2df931c2125e466d1f2f01f70fa31df5d46e05803098d7e5ec72b4434b` |
| 14167906810 | `dae725edaacef3c83a716d076fd2e1a0954d65e4143f7a5ed4a8c96209b822c9` |
| 14168027405 | `5ce00bb8183c6c68da5da559dbdeca2799ef7212f2a5bf85f84c6c09fca95b52` |

Original artifact expiry dates are retained in official metadata. The large ZIPs, unrelated screenshots and the Pages deployment package are intentionally excluded from this branch. All original JSON/TXT reports and the five homepage screenshots for each completed browser phase are retained.

## Visual review and scope

The parent agent directly inspected the original PR desktop and mobile first-screen screenshots: the expected v8 color panorama is present, desktop title/buttons are readable, and mobile displays the whole image with a separate text area. This verifies webpage presentation only. `metadata/visual-review.json` records that bounded conclusion, and `summary.json` compares exact screenshot bytes across phases.

The screenshot files are unmodified CI originals. Full-page pixel comparisons report only observed bounds and do not infer a cause automatically. The picture remains labeled “研究性复原示意”; no new historical claim, coordinate, measured building height or archaeological reconstruction is established by this image replacement.

## File integrity

`SHA256SUMS` covers every other file in this archive. The archive is held on a separate evidence branch and does not trigger a new main deployment. The original JSON/TXT files are the primary evidence; this README and `summary.json` are navigation and independently recounted summaries.
