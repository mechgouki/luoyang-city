# Terrain acquisition blockers: verified diagnosis and working route

Verified on 2026-11-12 for `mechgouki/luoyang-city` using the intended `mechgouki` connection. This is an infrastructure diagnostic and raw-source acquisition, not a v3.0 research release.

## What actually failed

The previous preparation package recorded `urlopen error [Errno -3] Temporary failure in name resolution`. This session reproduced that failure inside its local execution environment for both the global and EU-central-1 Copernicus S3 endpoints and the UT Austin map endpoint. This is not evidence of an AWS subscription requirement or insufficient repository permissions. It does not diagnose the user's own computer or DNS.

The earlier session exposed read-only GitHub actions. This session again exposed create/update actions. Actual branch and workflow-file writes succeeded using the existing account connection, without requesting a password, personal access token, broader installation scope or a Pages settings change.

## Working route tested end-to-end

1. Create an isolated branch from `main`: `fix/terrain-acquisition-20261112`.
2. Write `.github/workflows/acquire-terrain.yml` on that branch.
3. Its branch-scoped push trigger runs `Acquire terrain sources (no secrets)` on a GitHub-hosted Ubuntu runner.
4. Download the two fixed public HTTPS sources; verify full transfer length and TIFF/JPEG signatures; record URLs, response metadata, SHA-256 and source notices.
5. Upload the files as `luoyang-terrain-inputs`; retrieve that artifact through the authenticated GitHub artifact-download action.
6. Independently open the actual downloaded TIFF/JPEG, check the hashes and raster coverage in the local workspace.

This route moves acquisition to an environment where the public hosts resolve. It does not claim to repair or bypass the local environment's DNS configuration. The workflow uses `permissions: contents: read`, has bounded downloads, uses no external Secrets, does not commit large source files to Git, and does not deploy Pages. The user does not need to reconfigure GitHub or reconnect their account.

## Observed results

- Acquisition commit: `937305dbb1b327491e20ea7b65fec39d12a80060`.
- Successful Actions run: https://github.com/mechgouki/luoyang-city/actions/runs/43161390182
- Artifact ID: `13918121511`; ZIP size: 49,562,603 bytes.
- Artifact ZIP SHA-256: `20446a21dacee5d7278969f170052211409c98ccb230a05b1159a080c4a70973`.
- Both downloads succeeded on their first attempt in the runner. The downloaded artifact hash matched GitHub's reported digest; each extracted source matched `acquisition.json`.

| Source | File size | Independent content check | SHA-256 |
|---|---:|---|---|
| Copernicus GLO-30 N34 E112 | 43,927,531 bytes | GTiff; 3600 x 3600; Float32; one band; EPSG:4326; all 12,960,000 samples finite | `60bde4a8534d1b18b8c1bd0a275c8e4f6153d526a14df740f240e0f13ed7dad7` |
| AMS LO-YANG NI49-7 | 5,631,328 bytes | JPEG; 5000 x 3779; RGB; image decoder verification passed | `005a2b3c81f9135ab03739f2c8f52566c554f7c7af56c6bad5d9b47927970532` |

Raster extent reported by the reader: west 111.99986111111112, south 34.00013888888889, east 112.99986111111112, north 35.00013888888889. It covers the proposed 112.35-112.95E, 34.50-34.95N analysis window. Angular sample spacing is 1/3600 degree in both directions. The small edge offsets follow the raster's point-sampling convention; the analysis window is not an ancient city boundary.

## Source information and limits

Copernicus public AWS catalogue: https://registry.opendata.aws/copernicus-dem/ . The catalogue explicitly permits anonymous access without an AWS account, subject to the data licence. The dataset is a modern digital surface model, not Northern Wei bare-earth elevation.

AMS source catalogue: https://maps.lib.utexas.edu/maps/ams/china/ . Downloading and decoding the original image does not establish its sheet edition, survey dates, datum, registration controls or ancient river geometry. Those remain research tasks.

Raw data acquisition is now verified. Terrain processing, historical-map registration and integration into the published website remain separate acceptance gates. The public website and its historical geometry were not modified by this fix.

## Reuse

The branch push trigger already ran automatically. The successful run can be rerun in GitHub Actions. `workflow_dispatch` is also declared, but the normal manual workflow button requires the workflow to exist on the default branch; this diagnostic has not been merged into `main`. Integrate this reusable acquisition workflow through a reviewed PR when continuing the terrain milestone. Do not mistake this working diagnostic branch for a released terrain website.

Artifacts are retained for 30 days (current expiry 2026-12-12); the raw ZIP and independent verification JSON have also been copied into the conversation deliverables. A long-term source archive and licence review should be part of the terrain milestone, rather than depending only on expiring CI artifacts.
