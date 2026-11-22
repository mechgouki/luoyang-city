# Final main independent public HTTP capture

This directory preserves actual HTTPS response bodies from `https://mechgouki.github.io/luoyang-city/` for source commit `d7cd18a832e30e718dfd360b240c15b79927306b`. The capture ran from 2026-11-22 11:56:16 to 11:56:57 Asia/Shanghai and passed its selected HTTP checks.

The original `http-capture.json` records 39 responses from 38 distinct URLs, their headers, lengths, SHA-256 hashes, and stored body paths. All 39 saved bodies were independently reread during archiving and matched those original recorded lengths and hashes. The capture report and response bodies remain unchanged.

The recorded checks confirm:

- Opening and closing `build-info.json` responses are byte-identical and identify the same source commit.
- The manifest matches the build information; the data has 4 nodes, 32 findings, 32 relations, 28 segments, and 9 waters, with 339/84/34 indexed entities/roads/waters.
- The CSV retains all 28 rows and 30 columns, preserves exact JSON values and unknown values, and has its UTF-8 BOM.
- The R7 offline ZIP has 13 unique members, valid CRCs, byte-identical public members, and all 28 segment anchors.
- Both V12 guide images match the approved public images and their fixed approved fingerprints.

The ZIP files beneath `http-responses/downloads` are actual captured public response bytes and belong in the evidence archive. They are distinct from the large temporary Actions artifact ZIPs excluded by the archive-selection rule.

These checks establish the selected public content and download consistency. Whole-site workflow and browser acceptance are recorded separately in `final-live`; this independent capture does not replace those results.
