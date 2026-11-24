"""Verify the actual V14 image, geometry guides, source links and old publication."""
import json
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from city_nodes_r7_verify import Document, verify_links, webp_size
from homepage_artwork_v10 import V12
from panorama_v14 import OLD_RECORD, png_size, validate_record, validate_record_review_state
from panorama_v14_contract import (
    KEY, VERSION, RESEARCH_VERSION, PAGE, FOLDER, MANIFEST, RECORD, SOURCE_RECORD,
    HOME_PAGES, BUILD_CONTROL_FILES, DISPLAY_GUIDE_ROLES, digest, restore_r11_context,
)

ROOT = Path(__file__).resolve().parents[1]


class ReviewMarkup(HTMLParser):
    """Read visible state text and containment without a browser dependency."""
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, raw):
        super().__init__(convert_charrefs=True)
        self.nodes, self.stack, self.by_id = [], [], {}
        self.feed(raw.decode("utf-8") if isinstance(raw, bytes) else raw)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        node = dict(tag=tag, attrs=attrs, text=[], index=len(self.nodes),
                    ancestors=[x["attrs"].get("id") for x in self.stack],
                    hidden=any(x["hidden"] for x in self.stack) or "hidden" in attrs or
                    any(term in attrs.get("style", "").replace(" ", "").lower() for term in ("display:none", "visibility:hidden")))
        self.nodes.append(node)
        if attrs.get("id"):
            assert attrs["id"] not in self.by_id, "Duplicate review anchor"
            self.by_id[attrs["id"]] = node
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                return

    def handle_data(self, text):
        for node in self.stack:
            node["text"].append(text)

    @staticmethod
    def text(node):
        return "".join(node["text"]).strip()


def verify_review_presentation(raw, data):
    """A rejected image must stay visibly rejected, including without script."""
    markup = ReviewMarkup(raw)
    candidate = data["candidate"]
    assert data["status"] == candidate["status"]
    status = markup.by_id["review-status"]
    body = next(node for node in markup.nodes if node["tag"] == "body")
    title = next(node for node in markup.nodes if node["tag"] == "title")
    h1 = next(node for node in markup.nodes if node["tag"] == "h1")
    assert body["attrs"]["data-image-status"] == status["attrs"]["data-status"] == data["status"]
    assert body["attrs"]["data-review-status"] == data["review_status"]
    assert not status["hidden"] and not h1["hidden"]
    if data["status"] == "needs_revision":
        assert data["review_status"] == "rejected_needs_revision"
        assert data["blocking_findings"]
        for node in (title, h1, status):
            assert "V14试绘审查·未通过" in markup.text(node), "Rejected image is not visibly labelled as rejected"
        assert "blocking-findings" in markup.by_id, "Rejected image lost its visible blocking findings"
        blockers = markup.by_id["blocking-findings"]
        assert not blockers["hidden"], "Blocking findings are hidden"
        assert blockers["index"] < markup.by_id["comparison"]["index"], "Blocking findings must precede the image"
        items = [node for node in markup.nodes if node["tag"] == "li" and "blocking-findings" in node["ancestors"]]
        assert [markup.text(node) for node in items] == data["blocking_findings"], "Visible blockers differ from the complete review findings"
        assert all(not node["hidden"] for node in items)
        button = next(node for node in markup.nodes if node["tag"] == "button" and node["attrs"].get("data-view") == "v14")
        assert "未通过" in markup.text(button)
        assert "未通过" in markup.text(markup.by_id["figure-v14"])
        assert "未通过" in markup.text(markup.by_id["downloads-title"]), "Rejected image downloads are labelled as accepted"
        current_image = next(node for node in markup.nodes if node["tag"] == "img" and "figure-v14" in node["ancestors"])
        assert "未通过" in current_image["attrs"].get("alt", ""), "Rejected image alt text omits its failed review state"
        image_downloads = {"./" + data["source_png"], "./" + data["images"]["v14"]["full"]}
        for node in markup.nodes:
            if (node["tag"] == "a" and "downloads" in node["ancestors"] and
                    "download" in node["attrs"] and node["attrs"].get("href") in image_downloads):
                assert "未通过" in markup.text(node), "Rejected image download label omits its failed review state"
    else:
        assert data["status"] == "candidate_for_review"
        assert data["review_status"] in {"accepted_for_user_review", "accepted_for_user_review_with_known_limits"}
        assert not data["blocking_findings"] and "blocking-findings" not in markup.by_id
        assert "待审看" in markup.text(status)
    for change in candidate["changes"]:
        node = markup.by_id["change-" + change["id"]]
        assert node["attrs"]["data-treatment"] == change["treatment_type"]
        text = markup.text(node)
        assert all(change[key] in text for key in ("title", "observation", "evidence", "change", "limitation"))
        if change["treatment_type"] == "attempted_not_accepted":
            assert "已试改，未通过" in text
    attempts = [item for item in data["supporting_assets"] if item["role"] == "attempt_review"]
    cards = [node for node in markup.nodes if "data-attempt-review" in node["attrs"]]
    assert len(cards) == len(attempts)
    for card, item in zip(cards, attempts):
        assert card["attrs"]["data-attempt-review"] == item["id"] and not card["hidden"]
        assert item["title"] in markup.text(card) and item["description"] in markup.text(card)
    return dict(image_status=data["status"], image_review_status=data["review_status"],
                visible_blocking_findings=len(data["blocking_findings"]), attempt_reviews=len(attempts))


def verify(info, reader, *, build_control_reader=None):
    get = lru_cache(maxsize=None)(reader)
    hashes, meta = info["files_sha256"], info[KEY]
    old_info, old_reader = restore_r11_context(info, get)
    assert KEY not in old_info and "city_plan_r11" in old_info
    assert meta["version"] == VERSION and meta["research_version"] == RESEARCH_VERSION
    assert meta["status"] in {"candidate_for_review", "needs_revision"}
    assert meta["homepage_revision"] == V12.revision
    assert meta["homepage_replacement_approved"] is False
    assert meta["new_ancient_coordinates"] == meta["new_shoreline_geometries"] == 0
    assert meta["field_registration_verified"] is False
    controls = meta["build_control_files_sha256"]
    assert set(controls) == BUILD_CONTROL_FILES
    for path, checksum in controls.items():
        assert hashes[path] == old_info["files_sha256"][path] == checksum
        if build_control_reader:
            assert digest(build_control_reader(path)) == checksum
    data = json.loads(get(RECORD))
    assert data["schema"] == "luoyang-panorama-v14-review-v1"
    assert data["research_version"] == RESEARCH_VERSION and data["implementation_version"] == VERSION
    assert data["source_commit"] == meta["source_commit"] == info["source_commit"]
    assert data["target_years"] == [516, 528]
    assert data["homepage_revision"] == V12.revision and data["homepage_replacement_approved"] is False
    assert data["new_ancient_coordinates"] == data["new_shoreline_geometries"] == 0
    assert data["field_registration_verified"] is False
    record = validate_record(json.loads((ROOT / SOURCE_RECORD).read_bytes()))
    assert record == data["candidate"], "Published decisions differ from actual reviewed record"
    assert record["revision"] == meta["candidate_revision"]
    assert data["source_inputs_sha256"] == meta["source_inputs_sha256"]
    for path, checksum in data["source_inputs_sha256"].items():
        source = (ROOT / path).resolve()
        assert source.is_relative_to(ROOT) and source.is_file(), path
        assert digest(source.read_bytes()) == checksum, (path, "Source input changed")
    previous = json.loads((ROOT / OLD_RECORD).read_bytes())
    assert data["images"] == meta["images"] and set(data["images"]) == {"v14", "v13r2", "v12"}
    for kind, image in data["images"].items():
        for scale in ("full", "small"):
            raw = get(image[scale])
            prefix = "" if scale == "full" else "small_"
            assert digest(raw) == image[scale + "_sha256"] == hashes[image[scale]]
            assert webp_size(raw) == (image[prefix + "width"], image[prefix + "height"])
            if kind == "v14":
                expected = record[scale]
                assert digest(raw) == expected["sha256"]
                assert webp_size(raw) == (expected["width"], expected["height"])
            elif kind == "v13r2":
                assert digest(raw) == previous[scale]["sha256"]
                assert raw == get(info["panorama_review_v13_r2"]["images"]["v13r2"][scale])
            else:
                path, checksum = (V12.full, V12.full_sha) if scale == "full" else (V12.small, V12.small_sha)
                assert raw == get(path) and digest(raw) == checksum
    assert data["source_png"] == meta["source_png"]
    original = get(data["source_png"])
    assert digest(original) == record["source_png_sha256"]
    assert original == (ROOT / record["source_png"]["path"]).read_bytes()
    assert png_size(original) == (record["source_png"]["width"], record["source_png"]["height"])
    assert get(FOLDER + "/generation-prompts.txt") == (ROOT / record["prompt_file"]).read_bytes()
    for path, source in data["audit_source_paths"].items():
        assert get(path) == (ROOT / source).read_bytes()
    review = json.loads(get(FOLDER + "/candidate-review.json"))
    audit = json.loads(get(FOLDER + "/visual-audit.json")) if record.get("visual_audit_file") else None
    review_state = validate_record_review_state(record, review, audit)
    assert all(data[key] == meta[key] == value for key, value in review_state.items()), "Published review state differs from the actual image reviews"
    assert data["supporting_assets"] == meta["supporting_assets"]
    assert len(data["supporting_assets"]) == len(record["supporting_assets"])
    for published, source in zip(data["supporting_assets"], record["supporting_assets"]):
        assert {k: v for k, v in published.items() if k != "published_path"} == source
        raw = get(published["published_path"])
        assert raw == (ROOT / source["path"]).read_bytes()
        assert digest(raw) == source["sha256"]
    for suffix in ("css", "js"):
        assert get(FOLDER + "/review." + suffix) == (ROOT / ("web/panorama-v14." + suffix)).read_bytes()
    mandatory = {"luoyang-city-plan.html", "city-plan-r11/plan.json", "city-plan-r11/maps/all.svg", "downloads/city-plan-r11.pdf", "downloads/city-plan-r11.zip", "luoyang-panorama-v13-r2.html", "panorama-v13-r2/review.json", "panorama-v13-r2/v13r2.webp", V12.full, V12.small, V12.metadata}
    assert mandatory <= set(meta["protected_files_sha256"])
    for path, checksum in meta["protected_files_sha256"].items():
        assert digest(get(path)) == checksum == old_info["files_sha256"][path], (path, "Earlier public bytes changed")
    for page in HOME_PAGES:
        assert f'data-hero-revision="{V12.revision}"'.encode() in get(page)
        assert b'panorama-candidate-v14' not in get(page)
        assert b'id="r11-plan-entry"' in old_reader(page)
    doc = verify_links(get(PAGE), hashes, current=PAGE)
    presentation = verify_review_presentation(get(PAGE), data)
    assert len(doc.ids) == len(set(doc.ids)), "Duplicate review-page anchor"
    anchors = set(doc.ids)
    assert {"main", "comparison", "review-status", "view-controls", "view-status", "figure-v14", "figure-v13r2", "figure-v12", "projection", "change-table", "changes", "limits", "downloads"} <= anchors
    assert doc.downloads == meta["download_files"] and len(doc.downloads) == len(set(doc.downloads))
    assert record["source_png_sha256"] == hashes[data["source_png"]]
    assert len(record["changes"]) == meta["change_count"] > 0
    for item in record["changes"]:
        assert "change-" + item["id"] in anchors
        for link in item["evidence_links"]:
            assert link["url"] in doc.links
    checked = set()
    for url in doc.links:
        parsed = urlsplit(url)
        if not parsed.scheme and parsed.path and parsed.fragment:
            target = parsed.path.removeprefix("./")
            if (target, parsed.fragment) not in checked:
                assert parsed.fragment in Document(get(target)).ids, url
                checked.add((target, parsed.fragment))
    guides = [item for item in data["supporting_assets"] if item["role"] in DISPLAY_GUIDE_ROLES]
    assert {"projection_overview", "projection_yongning"} <= {x["role"] for x in guides}
    for item in guides:
        assert "guide-" + item["id"] in anchors
        assert any(tag == "img" and attrs.get("src") == "./" + item["published_path"] for tag, attrs in doc.elements)
    from yongning_study import verify as verify_yongning_study
    study = verify_yongning_study(info, get)
    return dict(status="passed", source_commit=info["source_commit"], candidate_revision=meta["candidate_revision"],
                homepage_revision=V12.revision, homepage_replacement_approved=False, change_count=meta["change_count"],
                downloads=len(doc.downloads), projection_guides=len(guides), verified_cross_page_anchors=len(checked),
                protected_public_files=len(meta["protected_files_sha256"]), reversible_homepages=len(HOME_PAGES),
                new_ancient_coordinates=0, new_shoreline_geometries=0, field_registration_verified=False,
                publication_verification="passed", image_accepted_for_user_review=meta["status"] == "candidate_for_review",
                yongning_study=study,
                **presentation)
