"""H2: the exact user-approved panorama replaces the H1 interim hero without moving the research map."""
from pathlib import Path
from PIL import Image
import hashlib
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"_site"
OLD_REV="panorama-interim-v8"
REV="panorama-approved-v9"
VERSION="homepage-approved-v9"
SRC_SHA="2a59bf83886d77f7c9226ec7f5d99c94ea6c63c6e207c2e560ee82f80ed93891"
FULL_SHA="6465657667ba740d3fc99cde2495a864d3a8a446e2086c25984c0c547eed5825"
SMALL_SHA="98459529d0a2d8210aaf2728b0c1673ca38b46df2f7b761c9064f1c21fe053b6"

def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class ApprovedPanoramaH2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home=read(SITE/"homepage/approval-v9.json")
        cls.h1=read(SITE/"homepage/metadata.json")
        cls.old=read(SITE/"homepage/history/panorama-interim-v8.json")
        cls.approval=read(SITE/"homepage/approval-v9.json")
        cls.preservation=read(SITE/"homepage/approval-preservation-v9.json")
        cls.info=read(SITE/"build-info.json")
        cls.release=read(SITE/"release.json")

    def test_explicit_approval_and_correct_source(self):
        h=self.home["hero"]
        self.assertEqual(self.home["version"],"homepage-approved-v9")
        self.assertEqual(self.h1,self.old)
        self.assertEqual(h["revision"],REV)
        self.assertEqual(h["status"],"approved")
        self.assertEqual(h["visual_review"],"approved_for_homepage")
        self.assertEqual(h["approval_date"],"2026-11-17")
        self.assertEqual(h["approval_scope"],"homepage_visual_only")
        self.assertEqual(h["source_name"],"北魏洛阳盛景全景俯瞰.png")
        self.assertEqual(h["source_sha256"],SRC_SHA)
        self.assertEqual(self.approval["source_sha256"],SRC_SHA)
        self.assertFalse(h["historical_ground_truth_upgraded"])
        self.assertTrue(h["publication_authorized"])
        self.assertTrue(h["generated_image"])
        self.assertFalse(h["measured_reconstruction"])
        self.assertEqual(self.approval["adds_ancient_geographic_control_points"],0)
        self.assertIsNone(self.approval["adds_reconstructed_roof_height_m"])

    def test_full_and_mobile_images_match_approved_blobs(self):
        h=self.home["hero"]
        for path,expected,size in [
            ("asset",FULL_SHA,(1672,941)),
            ("small_asset",SMALL_SHA,(960,540))
        ]:
            source=SITE/h[path]
            self.assertTrue(source.is_file(),path)
            self.assertEqual(sha(source),expected)
            self.assertEqual(self.info["files_sha256"][h[path]],expected)
            with Image.open(source) as im:
                self.assertEqual(im.format,"WEBP")
                self.assertEqual(im.size,size)
        self.assertEqual(h["width"],1672)
        self.assertEqual(h["height"],941)
        self.assertIn("no crop",h["conversion"])

    def test_protected_research_and_interim_images_preserved(self):
        self.assertTrue(self.preservation["protected_unchanged"])
        self.assertEqual(len(self.preservation["sha256"]),self.preservation["protected_files"])
        for path,expected in self.preservation["sha256"].items():
            self.assertEqual(sha(SITE/path),expected,path)
        old=self.old["hero"]
        self.assertEqual(old["revision"],OLD_REV)
        self.assertEqual(old["status"],"interim")
        self.assertEqual(old["visual_review"],"further_revision_requested")
        self.assertEqual(old["source_sha256"],"29427da12c869874f8ccd43749dd44f6a851cde8eddb643f31008088b2eeaa39")
        self.assertEqual(self.info["files_sha256"][old["asset"]],old["asset_sha256"])
        self.assertEqual(self.info["files_sha256"][old["small_asset"]],old["small_asset_sha256"])
        for page in ("index.html","v3.0-dual.html"):
            archive=SITE/"homepage/history"/page.replace(".html","-before-v9.html")
            self.assertEqual(sha(archive),self.approval["previous_html_sha256"][page])
            self.assertIn(old["asset"],archive.read_text(encoding="utf-8"))

    def test_new_homepage_and_both_releases_reference_approved_image(self):
        h=self.home["hero"]
        for name in ("index.html","v3.0-dual.html"):
            archived=SITE/"homepage/history"/name.replace(".html","-before-v10.html")
            code=archived.read_text(encoding="utf-8")
            self.assertIn('data-hero-revision="'+REV+'"',code)
            self.assertIn('src="./'+h["asset"]+'"',code)
            self.assertIn('srcset="./'+h["small_asset"]+'"',code)
            self.assertEqual(code.count('id="home-hero"'),1)
            self.assertIn("研究性复原示意",code)
            self.assertIn("河道",code)
            self.assertIn("已",code)
            self.assertNotIn('src="./'+self.old["hero"]["asset"]+'"',code)
            self.assertIn('id="home-research"',code)
            self.assertIn('id="map-viewport"',code)

    def test_current_homepage_matches_approved_full_frame(self):
        import sys
        sys.path.insert(0,str(ROOT/"tools"))
        from homepage_artwork_v10 import verify, V11, V12
        verify(self.info,self.release,lambda path:(SITE/path).read_bytes())
        for name,size in ((V12.full,(1672,941)),(V12.small,(960,540))):
            with Image.open(SITE/name) as artwork:
                self.assertEqual(artwork.size,size)
                self.assertEqual(artwork.format,"WEBP")
        for page in ("index.html","v3.0-dual.html"):
            archived=(SITE/V12.archive(page)).read_bytes()
            self.assertIn(f'data-hero-revision="{V11.revision}"'.encode(),archived)
            self.assertIn(V11.full.encode(),archived)
            self.assertIn(V11.small.encode(),archived)

    def test_release_provenance_matches_all_versions(self):
        import sys
        sys.path.insert(0,str(ROOT/"tools"))
        from homepage_yongning_v15 import restore_v14_context
        _, legacy_reader=restore_v14_context(self.info,lambda path:(SITE/path).read_bytes())
        legacy_release=json.loads(legacy_reader("release.json"))
        current=read(SITE/"homepage/approval-v12.json")
        previous=read(SITE/current["previous_metadata"])
        earlier=read(SITE/previous["previous_metadata"])
        self.assertEqual(current["previous_revision"],"panorama-approved-v11")
        self.assertEqual(previous["previous_revision"],"panorama-approved-v10")
        self.assertEqual(earlier["previous_revision"],REV)
        self.assertEqual(current["hero"]["selection_label"],"全幅取景版")
        self.assertEqual(current["hero"]["display_mode"],"full_frame")
        self.assertEqual(current["hero"]["based_on_revision"],previous["hero"]["revision"])
        self.assertEqual(current["hero"]["source_sha256"],"c7954dfc3ee659de756c62d0f634e40eddfd2ecc93cc8b833f53f6c0e0dc69ca")
        self.assertEqual(previous["hero"]["selection_number"],"07")
        self.assertEqual(previous["hero"]["source_sha256"],"4d45e831b59f2f7550fe7129455f1da823098e8f34cf633223cd584d5b64a5bf")
        self.assertEqual(earlier["hero"]["source_sha256"],"262e0797c09788f7871bca81c05d5e2c15d5ebc7ab8cf6c559ced68cf883a41e")
        self.assertEqual(legacy_release["homepage_hero_revision"],current["hero"]["revision"])
        self.assertEqual(legacy_release["homepage_hero_status"],"approved")
        self.assertIn(VERSION,legacy_release["extensions"])
        self.assertEqual(self.info["homepage"]["hero_revision"],OLD_REV)
        self.assertEqual(self.info["homepage"]["hero_status"],"interim")
        self.assertEqual(self.info["homepage_approved_v9"]["hero_revision"],REV)
        self.assertEqual(self.info["homepage_approved_v9"]["hero_status"],"approved")
        self.assertEqual(self.info["homepage_approved_v9"]["version"],VERSION)
        self.assertEqual(self.info["homepage_approved_v9"]["source_commit"],self.info["source_commit"])
        self.assertEqual(self.approval["source_commit"],self.info["source_commit"])
        self.assertFalse(self.approval["changes_research_data"])
        self.assertFalse(self.approval["changes_city_layout"])
        self.assertEqual(self.info["counts"]["entities"],339)
        self.assertEqual(self.info["counts"]["markers"],179)
        self.assertEqual(self.info["prosperity_architecture"]["types"],6)
        self.assertEqual(self.info["prosperity_palace_boundaries"]["scope_variants"],3)

if __name__=="__main__":
    unittest.main()
