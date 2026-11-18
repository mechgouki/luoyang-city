"""Verify the offline package and the reversibility of the P4.6 entry insertion."""
import hashlib
import json
import unittest
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
SOURCE = ROOT / "research/prosperity-v4/anchor-461"


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        for key in ("href", "src", "data" if tag == "object" else "poster"):
            if key in attrs:
                self.urls.append(attrs[key])


class AnchorReadings(unittest.TestCase):
    def test_sources_and_offline_links(self):
        meta = json.loads((SITE / "build-info.json").read_text())["prosperity_anchors_p461"]
        manifest = json.loads((SITE / meta["manifest"]).read_text())
        self.assertEqual(meta["source_commit"], manifest["source_commit"])
        self.assertEqual((SITE / meta["page"]).read_bytes(), (SOURCE / "index.html").read_bytes())
        with zipfile.ZipFile(SITE / meta["bundle"]) as package:
            members = set(package.namelist())
            self.assertEqual(members, set(manifest["files_sha256"]) | {"index.html", meta["manifest"]})
            self.assertEqual(package.read(meta["manifest"]), (SITE / meta["manifest"]).read_bytes())
            index = package.read("index.html")
            self.assertEqual(hashlib.sha256(index).hexdigest(), manifest["offline_index_sha256"])
            refs = References()
            refs.feed(index.decode())
            for url in refs.urls:
                parts = urlsplit(url)
                if parts.scheme or parts.netloc:
                    continue
                if parts.path:
                    self.assertIn(unquote(parts.path).removeprefix("./"), members, url)
                elif parts.fragment:
                    self.assertIn(unquote(parts.fragment), refs.ids, url)
            for name, expected in manifest["files_sha256"].items():
                payload = package.read(name)
                self.assertEqual(hashlib.sha256(payload).hexdigest(), expected, name)
                self.assertEqual(payload, (SITE / name).read_bytes(), name)
                if name == meta["atlas"]:
                    self.assertEqual(len(PdfReader(SITE / name).pages), len(meta["atlas_plates"]))
                    continue
                self.assertEqual(payload, (SOURCE / Path(name).relative_to("anchor-461")).read_bytes(), name)

    def test_prior_page_restorable_to_archived_bytes(self):
        info = json.loads((SITE / "build-info.json").read_text())
        study = info["prosperity_anchors_p461"]
        name = "prosperity-hydro-roads.html"
        html = (SITE / name).read_text()
        new_entry = next(line + "\n" for line in html.splitlines() if line.startswith('<p id="p461-entry">'))
        previous = html.replace(new_entry, "", 1).encode()
        with zipfile.ZipFile(SITE / "downloads/prosperity-hydro-roads-p46-package.zip") as old_bundle:
            self.assertEqual(previous, old_bundle.read(name))
        self.assertEqual(hashlib.sha256(previous).hexdigest(), study["previous_html_sha256"])
        self.assertEqual(info["homepage_approved_v9"]["hero_revision"], "panorama-approved-v9")
