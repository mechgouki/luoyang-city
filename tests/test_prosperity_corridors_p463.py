"""The road spacings and each author's pond contacts retain independent frames."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

from pypdf import PdfReader
from test_prosperity_anchors_p461 import References

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"


class CorridorsStudy(unittest.TestCase):
    def test_study_and_readings(self):
        record = json.loads((SITE / "corridors-463/evidence.json").read_text())
        ward = record["ward"]
        self.assertEqual((ward["ns_offsets_m"], ward["ew_offsets_m"]), ([-86,0,86],[-40,0,40]))
        self.assertEqual((ward["central_ns_width_m"], ward["gate_gap_m"]), (22,7.5))
        self.assertIsNone(ward["gate_to_central_cross_m"])
        older = json.loads((SITE / "network-462/outer.json").read_text())
        self.assertEqual({r[2] for r in record["roads"] if r[2]}, {r["id"] for r in older["corridors"]})
        self.assertEqual((len(set(r[0] for r in record["roads"])),len(record["southern_separate"])), (9,2))
        pond = record["hongchi"]
        self.assertEqual([len(f["contacts"]) for f in pond["figures"]],[4,3])
        self.assertIsNone(pond["northern_wei_shoreline"])
        self.assertEqual(pond["archaeological_control"]["period"],"商代")
        for figure in pond["figures"]:
            left, top, right, bottom = figure["crop_xyxy"]
            self.assertTrue(0 <= left < right <= figure["size"][0])
            self.assertTrue(0 <= top < bottom <= figure["size"][1])
            for side, name, (x, y) in figure["contacts"]:
                self.assertTrue(left < x < right and top < y < bottom, (side, name))

    def test_offline_edition(self):
        info = json.loads((SITE/"build-info.json").read_text())
        study = info["prosperity_corridors_p463"]
        self.assertEqual(len(PdfReader(SITE/study["atlas"]).pages),3)
        with zipfile.ZipFile(SITE/study["bundle"]) as archive:
            manifest = json.loads(archive.read(study["manifest"]))
            self.assertEqual(manifest["source_commit"], info["source_commit"])
            for name, digest in manifest["files_sha256"].items():
                self.assertEqual(archive.read(name), (SITE/name).read_bytes())
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(),digest)
            index = archive.read("index.html")
            self.assertEqual(hashlib.sha256(index).hexdigest(), manifest["offline_index_sha256"])
            refs = References()
            refs.feed(index.decode())
            for url in refs.urls:
                parts = urlsplit(url)
                if parts.scheme or parts.netloc:
                    continue
                if parts.path:
                    self.assertIn(unquote(parts.path).removeprefix("./"),archive.namelist())
                elif parts.fragment:
                    self.assertIn(unquote(parts.fragment),refs.ids)
