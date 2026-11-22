# PR78 atlas-family readiness evidence

This directory preserves the successful PR78 build and browser evidence from workflow run `44983493286`, artifact `14738559330` (`browser-build-evidence`). It is PR evidence; production acceptance is recorded separately.

- PR head: `3cdf900ebfc4e4b851556360d175bb7798aeea3b`.
- Actual tested PR merge checkout: `251e8e0a3c537699ed0900d379087b8e65ecf102`.
- Tested tree: `b05e0692132f085adf9f00c3702fb095e3f06c5f`.
- The open PR snapshot and tested Git commit document the actual PR test source. The later `pull-request-78.json` was captured after merge and records main `557c468649d6919bd249ddd891b9c97cd37cf706`; this later main commit is not substituted for the PR test checkout.

`artifact-selection.json` records all 123 selected artifact members, including 49 browser reports and 44 R7/R6.2/V12 PNGs. Exact raw ZIP and member hashes are retained. All 44 PNGs match `main-d7-build` byte for byte, as recorded in `screenshot-comparison.json`; this comparison does not imply a new manual inspection of every image.

The ten desktop/mobile family reports contain all 72 expected layout measurements. Every measurement records `ready_state=complete`, preserves its original tolerance, and shows zero document-width excess:

| Family | Measurements per device | Original width tolerance |
|---|---:|---:|
| R4 | 3 | 0 |
| R5 | 5 | 0 |
| R6 | 6 | 1 |
| R6.2 | 8 | 1 |
| R7 | 14 | 1 |

`family-layout-verification.json` contains every original measured value and report checksum. `layout-family-audit.json` preserves the final static source audit: 40 existing browser scripts, five changed family scripts, 35 unchanged scripts, and 45 explicit navigation-mode adjustments. Static audit and executed browser evidence are kept distinct.

The included verifier can recheck the archive without modifying any files:

```sh
python3 verify-family-evidence.py --root . --expected-source 251e8e0a3c537699ed0900d379087b8e65ecf102 --baseline ../main-d7-build --check-only
```

The extraction tool's `corrected-pr` stage is a generic correction category. The PR number, run, artifact, actual checkout, and directory name identify this as PR78 rather than the earlier correction attempts.
