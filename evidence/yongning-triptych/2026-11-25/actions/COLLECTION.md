# Yongning triptych Actions evidence collection

This payload is a scoped, byte-preserving collection of the actual production run `45363321713` for source `bbfbac9022e133e61836614f3b120cf42efde43e`.

Six ZIP archives were downloaded through GitHub's artifact API. Their actual byte counts and SHA-256 values match GitHub's artifact metadata. `artifact-identities.json` records that comparison. `artifact-members/` records every original member, its actual byte count and SHA-256, and whether its bytes were retained. The temporary signed download URLs are not included.

The complete production build evidence, failed first live attempt, and successful second live attempt are separated under `build/`, `live-attempt1/`, and `live-attempt2/`. All original JSON/text/log reports outside legacy download directories are retained. All Yongning study screenshots, reports, and actual browser downloads are retained. Ordinary screenshots and downloaded artifacts for older features, and reproducible terrain products, are omitted with an explicit per-member identity and reason. This is not a claim that every byte of the deployed site or every old-feature screenshot has been archived.

The three focused Yongning artifact packages were separately downloaded and compared byte for byte with corresponding members of the full artifacts. Their inventories point to the exact same retained payload paths; duplicate copies were not made.

The six original Yongning device reports each identify the production source, report `passed`, and retain eight actual click downloads plus three screenshots. All 48 retained download events and 18 screenshot entries were checked against the actual retained bytes and their original report hashes. These are six device-stage reports across build, failed first live attempt, and successful second live attempt; they are not 48 unique downloadable files. The eight unique download identities are the seven study originals and their publication manifest. `study-evidence-byte-checks.json` preserves the checks.

The first live attempt's old P4 axis report contains empty `checks` and `errors` lists because its image visibility assertion failed before the first screenshot and first passed checkpoint. No failure screenshot exists in that original artifact. The exact traceback must be read from the separately collected GitHub job log, not reconstructed from the empty report. The failure is not reclassified as a known network fault.

Both original HTTP reports check 968 public resources. The successful second attempt records one transient HTTP 503 retry for `anchor-461/roads.json`, which then succeeded. Its retry is preserved in the raw report. The first attempt's HTTP check has no retries but its later browser regression failed.

This collection does not recover or recreate the previous session's claimed independent 49-file check or manual browser session. Any new independent readback must be timestamped and reported as a new check. The source images and research decisions remain at the fixed production source; image generation, full-ground acceptance, and homepage replacement were not performed by this evidence collection.

## Retained raw artifact members

| Stage | Original members | Retained members | Retained bytes |
| --- | ---: | ---: | ---: |
| Production build | 762 | 128 | 26,964,503 |
| First live attempt, failed | 457 | 57 | 26,995,953 |
| Second live attempt, successful | 715 | 88 | 27,095,675 |

The six member inventories, artifact identities, scope, derived byte check, and collection summary are additional collection records. Their counts must be recomputed if further API snapshots, logs, or independent observations are added.
