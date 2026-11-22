"""Verify actual R9 publication bytes against reviewed evidence and source ink.

``reader`` is the sole source of published resources, including the HTML, CSV,
SVG, upstream inputs and ZIP members. Repository files are immutable comparison
inputs, never a fallback for a missing or changed public file. Only the standard
library is needed by the production ``verify-live`` job.
"""
import copy
import csv
import hashlib
import io
import json
import re
import stat
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from city_nodes_r7_verify import Document, _path_points, pointer, verify_links, verify_native_features
from homepage_artwork_v10 import V12

ROOT = Path(__file__).resolve().parents[1]
KEY = "city_spatial_r9"
VERSION = "city-spatial-r9"
PAGE = "luoyang-city-spatial.html"
FOLDER = "city-spatial-r9"
MANIFEST = FOLDER + "/manifest.json"
DATA = FOLDER + "/decisions.json"
CSV = FOLDER + "/decisions.csv"
SVG = FOLDER + "/overview.svg"
AUDIT = FOLDER + "/source-audit.json"
BUNDLE = "downloads/city-spatial-r9.zip"
BASE = "https://mechgouki.github.io/luoyang-city/"
SOURCE = "research/city-spatial-r9/decisions.json"
NODES = ("palace-yongning", "baima", "sima", "jianchun")
NODE_TITLES = ("宫前与永宁", "白马寺坊街", "司马门与仓区", "建春门桥渠")
CSV_FIELDS = ("id", "node_id", "node_title", "title", "evidence_classes", "previous_expression",
              "judgment", "evidence", "map_change", "remaining_unknown", "panorama_action",
              "prior_finding_ids", "road_ids", "water_ids", "source_inputs", "anchor_kind")
NS = "{http://www.w3.org/2000/svg}"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load_source(path):
    file = (ROOT / path).resolve()
    assert file.is_relative_to(ROOT) and file.is_file(), (path, "Missing research input")
    return json.loads(file.read_bytes())


def unique(rows, name="id"):
    identifiers = [row[name] for row in rows]
    assert len(identifiers) == len(set(identifiers)), (name, "Duplicate identifiers")
    return {row[name]: row for row in rows}


def verify_data(data, meta, info, atlas, old_nodes):
    """Compare every published decision and evidence join with its reviewed inputs."""
    original = load_source(SOURCE)
    for name, value in original.items():
        if name != "decisions":
            assert data[name] == value, (name, "Reviewed research header changed")
    assert data["schema"] == "luoyang-city-spatial-decisions-v1"
    assert data["research_version"] == meta["research_version"] == "R9.1"
    assert data["implementation_version"] == meta["version"] == VERSION
    assert data["source_commit"] == meta["source_commit"] == info["source_commit"]
    assert data["target_years"] == [516, 528]
    for name in ("new_historical_coordinates", "new_shoreline_geometries", "evidence_grade_upgrades"):
        assert data[name] == meta[name] == 0, (name, "Research precision was promoted")
    assert data["source_frames_registered_together"] is meta["source_frames_registered_together"] is False
    assert data["homepage_replacement_approved"] is meta["homepage_replacement_approved"] is False
    assert data["homepage_revision"] == meta["homepage_revision"] == V12.revision
    assert data["coordinate_contract"] == meta["coordinate_contract"]
    assert data["map_views"] == meta["map_views"]
    assert set(data["map_views"]) == {"all", "source", *NODES}
    for view, box in data["map_views"].items():
        values = [float(value) for value in box.split()]
        assert len(values) == 4 and values[2] > 0 and values[3] > 0, view
    assert data["nodes"] == [dict(id=nid, title=title) for nid, title in zip(NODES, NODE_TITLES)]
    assert data["csv_fields"] == list(CSV_FIELDS)
    assert "复用R7" in data["evidence_basis_status"] and "没有新增" in data["evidence_basis_status"]

    fingerprints = data["source_inputs_sha256"]
    assert fingerprints == meta["source_inputs_sha256"] and fingerprints
    documents = {}
    for path, checksum in fingerprints.items():
        file = (ROOT / path).resolve()
        assert file.is_relative_to(ROOT) and file.is_file(), path
        raw = file.read_bytes()
        assert digest(raw) == checksum, (path, "Research input bytes changed")
        if file.suffix == ".json":
            documents[path] = json.loads(raw)

    reviewed, sources = {}, {}
    previous_nodes = unique(old_nodes["nodes"])
    used_paths = {SOURCE, "research/prosperity-v1/geographic-evidence.json", "research/prosperity-r5/sima-road.json",
                  "research/city-spatial-r9/source-audit.json"}
    for nid in NODES:
        path = "research/city-nodes-r7/reviews/" + nid + ".json"
        used_paths.add(path)
        reviewed[nid] = documents[path]
        for name, value in reviewed[nid].items():
            assert previous_nodes[nid][name] == value, (nid, name, "Published R7 evidence changed")
        for entry in reviewed[nid]["source_refs"]:
            current = copy.deepcopy(entry)
            current["provenance_stage"] = "R7.1"
            current["prior_access_status"] = current.pop("access_status")
            current["prior_checked_on"] = current.pop("checked_on")
            assert entry["id"] not in sources or sources[entry["id"]] == current, "Source ID collision"
            sources[entry["id"]] = current
    assert data["sources"] == list(sources.values()), "Source access history or identity changed"

    base_rows = unique(original["decisions"])
    rows = unique(data["decisions"])
    assert list(rows) == list(base_rows) == ["SP" + str(i).zfill(2) for i in range(1, 21)]
    assert {row["node_id"] for row in rows.values()} == set(NODES)
    classes, finding_ids, source_ids = set(), set(), set()
    pointer_count = quotes = summaries = 0
    derived = {"node_title", "road_ids", "water_ids", "source_inputs", "evidence", "geometry_changed",
               "evidence_grade_upgraded", "prior_review_url"}
    for identifier, row in rows.items():
        base_row = base_rows[identifier]
        assert set(row) == set(base_row) | derived, (identifier, "Unexpected or missing decision fields")
        for name, value in base_row.items():
            assert row[name] == value, (identifier, name, "Reviewed drawing decision changed")
        assert row["evidence_classes"] and set(row["evidence_classes"]) <= {"source", "relation", "unknown"}
        classes.update(row["evidence_classes"])
        assert row["geometry_changed"] is row["evidence_grade_upgraded"] is False
        assert row["node_title"] == dict(zip(NODES, NODE_TITLES))[row["node_id"]]
        review = reviewed[row["node_id"]]
        findings = [f for f in review["findings"] if f["id"] in row["prior_finding_ids"]]
        assert len(findings) == len(row["prior_finding_ids"]) > 0
        finding_ids.update(row["prior_finding_ids"])
        assert row["road_ids"] == sorted({rid for f in findings for rid in f.get("road_ids", [])})
        assert row["water_ids"] == sorted({wid for f in findings for wid in f.get("water_ids", [])})
        expected_inputs, seen = [], set()
        for finding in findings:
            index = next(i for i, item in enumerate(review["findings"]) if item["id"] == finding["id"])
            references = [dict(path="research/city-nodes-r7/reviews/" + row["node_id"] + ".json",
                               pointer="/findings/" + str(index)), *finding["source_inputs"]]
            for reference in references:
                identity = (reference["path"], reference["pointer"])
                if identity in seen:
                    continue
                seen.add(identity)
                path, location = identity
                used_paths.add(path)
                actual = pointer(documents[path], location)
                if "native_geometry" in reference:
                    assert reference["native_geometry"] == actual, identity
                if "city_registration" in reference:
                    assert reference["city_registration"] is False, identity
                expected_inputs.append(dict(reference, sha256=fingerprints[path]))
                pointer_count += 1
        assert row["source_inputs"] == expected_inputs, (identifier, "Evidence pointer join changed")

        text_ids = row.get("text_check_ids", [])
        text_checks = [item for item in review.get("text_checks", []) if item["id"] in text_ids]
        assert len(text_checks) == len(text_ids), (identifier, "Quoted text identifier missing")
        expected_evidence = []
        for source_id in dict.fromkeys(sid for finding in findings for sid in finding["source_ids"]):
            source = sources[source_id]
            source_ids.add(source_id)
            quoted = [item for item in text_checks if source_id in item["source_ids"]]
            quote_kind = "classical_text_quote" if quoted else "prior_review_summary"
            quotes += bool(quoted)
            summaries += not bool(quoted)
            expected_evidence.append(dict(
                source_id=source_id, title=source["title"], url=source["url"],
                locator="；".join(item["locator"] for item in quoted) if quoted else source["locator"],
                excerpt_or_summary="\n".join(item["excerpt"] for item in quoted) if quoted else
                    "；".join(finding["claim"] for finding in findings if source_id in finding["source_ids"]),
                quote_kind=quote_kind, provenance_stage="R7.1", access_note=source["prior_access_status"],
                original_figure_url=source.get("figure_url")))
        assert row["evidence"] == expected_evidence, (identifier, "Source summary/quotation boundary changed")
        assert row["prior_review_url"] == BASE + "luoyang-city-nodes.html#finding-" + row["prior_finding_ids"][0]
    assert classes == {"source", "relation", "unknown"}
    assert set(fingerprints) == used_paths, "Source-input inventory is incomplete or unrelated"
    source_features = documents["research/prosperity-v1/geographic-evidence.json"]["features"]
    original_features = {f["id"]: f for f in source_features if not f["id"].startswith("geo-modern-")}
    atlas_features = {f["id"]: f for f in atlas["features"] if not f["id"].startswith("geo-modern-")}
    assert set(atlas_features) == set(original_features)
    for fid, feature in atlas_features.items():
        assert feature["source_pdf_geometry"] == original_features[fid]["source_pdf_geometry"], fid
    counts = dict(nodes=4, decisions=20, source_features=len(original_features), existing_findings_reused=len(finding_ids),
                  sources=len(source_ids), source_sima_atomic_lines=len(documents["research/prosperity-r5/sima-road.json"]["image"]["sima_road_ink_px"]))
    assert counts == data["counts"] == meta["counts"]
    return dict(counts=counts, input_files=len(fingerprints), resolved_pointers=pointer_count,
                classical_quotes=quotes, prior_review_summaries=summaries)


def verify_csv(raw, data):
    assert raw.startswith(b"\xef\xbb\xbf"), "CSV lacks its advertised UTF-8 BOM"
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    assert reader.fieldnames == list(CSV_FIELDS), "CSV schema changed"
    rows = list(reader)
    assert [row["id"] for row in rows] == [row["id"] for row in data["decisions"]]
    for actual, expected in zip(rows, data["decisions"], strict=True):
        assert None not in actual, "CSV has unlabelled extra columns"
        for name in CSV_FIELDS:
            value = expected[name]
            if isinstance(value, (list, dict)) or value is None:
                assert json.loads(actual[name]) == value, (expected["id"], name, "Lossy CSV field")
            else:
                assert actual[name] == str(value), (expected["id"], name, "CSV text changed")
    return len(rows)


def verify_svg(raw, data, *, standalone):
    root = ET.fromstring(raw)
    assert root.tag == NS + "svg" and root.get("id") == "spatial-map"
    assert root.get("viewBox") == root.get("data-original-viewbox") == data["map_views"]["all"]
    assert root.get("role") == "img" and list(root.iter(NS + "title")) and list(root.iter(NS + "desc"))
    assert root.get("data-new-geographic-coordinates") == root.get("data-new-shoreline-geometries") == "0"
    assert root.get("data-source-frames-registered-together") == "false"
    ids = [element.get("id") for element in root.iter() if element.get("id")]
    assert len(ids) == len(set(ids)), "Duplicate figure anchors"
    panels = [element for element in root.iter() if element.get("data-panel")]
    assert {p.get("data-panel") for p in panels} == set(NODES) and len(panels) == 4
    assert all(p.get("data-coordinate-space") == "unscaled-relationship" for p in panels)
    frame = [element for element in root.iter() if element.get("data-frame") == "frame-06a"]
    assert len(frame) == 1 and frame[0].get("data-city-registration") == "false"
    assert frame[0].get("data-coordinate-space") == "06a-source-pdf-units"
    retained = verify_native_features(root, "overview")
    assert retained == data["counts"]["source_features"]
    sources = {item["id"]: item for item in load_source("research/prosperity-v1/geographic-evidence.json")["features"]}
    for feature in frame[0]:
        fid = feature.get("data-feature")
        if fid:
            assert json.loads(feature.get("data-source-geometry")) == sources[fid]["source_pdf_geometry"]
    sima_frames = [element for element in root.iter() if element.get("data-frame") == "sima2023-independent"]
    assert len(sima_frames) == 1 and sima_frames[0].get("data-city-registration") == "false"
    native = load_source("research/prosperity-r5/sima-road.json")["image"]
    lines = [element for element in sima_frames[0].iter() if element.get("data-sima-atomic-line") is not None]
    assert [e.get("data-sima-atomic-line") for e in lines] == [str(i) for i in range(6)]
    assert [_path_points(e) for e in lines] == native["sima_road_ink_px"], "Sima native line or gap changed"
    assert [e.get("data-source-pointer") for e in lines] == ["/image/sima_road_ink_px/" + str(i) for i in range(6)]
    regions = [element for element in sima_frames[0].iter() if element.get("data-role") == "source-region-box-not-wall"]
    assert len(regions) == 1 and regions[0].get("stroke-dasharray"), "Range marker became a wall"
    region = regions[0]
    assert [float(region.get("x")), float(region.get("y")), float(region.get("x")) + float(region.get("width")),
            float(region.get("y")) + float(region.get("height"))] == native["storage_box_centerline_px"]
    linked = set()
    parents = {child: parent for parent in root.iter() for child in parent}
    for element in root.iter():
        if element.tag == NS + "a":
            ancestor = parents.get(element)
            while ancestor is not None:
                assert ancestor.tag != NS + "a", "Nested SVG links break focus and evidence navigation"
                ancestor = parents.get(ancestor)
        if element.get("data-decision"):
            identifier = element.get("data-decision")
            assert element.tag == NS + "a"
            expected = (BASE + PAGE if standalone else "") + "#decision-" + identifier
            assert element.get("href") == expected, (identifier, "Wrong figure evidence target")
            linked.add(identifier)
    assert linked == {row["id"] for row in data["decisions"]}
    return dict(retained_source_features=retained, sima_native_lines=len(lines), linked_decisions=len(linked))


class Node:
    def __init__(self, tag, attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()

    def text(self):
        return "".join(child.text() if isinstance(child, Node) else child for child in self.children)

    def has_class(self, name):
        return name in self.attrs.get("class", "").split()


class Tree(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, raw):
        super().__init__(convert_charrefs=True)
        self.root = Node("document")
        self.stack = [self.root]
        self.feed(raw.decode("utf-8"))

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag == "br":
            node.children.append("\n")
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def normalized(value):
    return " ".join(value.split())


def verify_page(raw, data, files, *, offline=False):
    doc = Document(raw)
    assert len(doc.ids) == len(set(doc.ids)), "Duplicate page anchors"
    expected_ids = {"overview", "decisions", "decisions-table", "boundaries", "downloads", "panorama-guide",
                    "spatial-map", "map-viewport", "map-views", "map-view", "zoom-in", "zoom-out", "reset-map",
                    "pan-left", "pan-right", "pan-up", "pan-down", "search", "node-filter", "basis-filter",
                    "reset-filters", "result-count", "no-results"}
    expected_ids.update("decision-" + row["id"] for row in data["decisions"])
    assert expected_ids <= set(doc.ids), "Required interface/evidence anchor missing"
    if not offline:
        verify_links(raw, files, current=PAGE)
    tree = Tree(raw)
    all_nodes = list(tree.root.walk())
    rows = [node for node in all_nodes if node.tag == "tr" and node.has_class("decision-row")]
    assert [node.attrs.get("id") for node in rows] == ["decision-" + row["id"] for row in data["decisions"]]
    for node, row in zip(rows, data["decisions"], strict=True):
        assert node.attrs["data-node"] == row["node_id"]
        assert node.attrs["data-basis"].split() == row["evidence_classes"]
        assert "hidden" not in node.attrs, "No-JavaScript evidence was hidden"
        content = normalized(node.text())
        for field in ("title", "node_title", "judgment", "previous_expression", "map_change", "remaining_unknown", "panorama_action"):
            assert normalized(row[field]) in content, (row["id"], field, "Published row lost content")
        evidence_nodes = [element for element in node.walk() if element.has_class("evidence-item")]
        assert len(evidence_nodes) == len(row["evidence"])
        for element, evidence in zip(evidence_nodes, row["evidence"], strict=True):
            links = [n for n in element.walk() if n.tag == "a"]
            assert any(link.attrs.get("href") == evidence["url"] and link.text() == evidence["title"] for link in links)
            locators = [n for n in element.walk() if n.has_class("evidence-locator")]
            assert len(locators) == 1 and normalized(locators[0].text()) == normalized(evidence["locator"])
            quotes = [n for n in element.walk() if n.tag == "blockquote"]
            summaries = [n for n in element.walk() if n.tag == "details"]
            if evidence["quote_kind"] == "classical_text_quote":
                assert len(quotes) == 1 and not summaries
                displayed = quotes[0].text()
            else:
                assert evidence["quote_kind"] == "prior_review_summary" and not quotes and len(summaries) == 1
                labels = [n for n in summaries[0].walk() if n.tag == "summary"]
                texts = [n for n in summaries[0].walk() if n.tag == "p"]
                assert len(labels) == len(texts) == 1 and labels[0].text() == "查看既有核验摘要"
                displayed = texts[0].text()
            assert normalized(displayed) == normalized(evidence["excerpt_or_summary"]), "Quotation or summary text changed"
        row_links = [n.attrs.get("href") for n in node.walk() if n.tag == "a"]
        assert row["prior_review_url"] in row_links
        for source in row["source_inputs"]:
            assert "https://github.com/mechgouki/luoyang-city/blob/" + data["source_commit"] + "/" + source["path"] in row_links
            assert source["pointer"] in node.text()
    map_views = [n for n in all_nodes if n.attrs.get("id") == "map-views"]
    assert len(map_views) == 1 and json.loads(map_views[0].text()) == data["map_views"]
    figures = re.findall(rb"<svg\b.*?</svg>", raw, flags=re.DOTALL)
    assert len(figures) == 1
    verify_svg(figures[0], data, standalone=False)
    return doc, figures[0]


def verify(info, reader, *, build_control_reader=None):
    """Read and validate the released R9 bytes through a local or HTTPS reader."""
    # R9 adds no build-control file. The argument matches the other release
    # verifiers, and the upstream validator checks .nojekyll only via its local
    # build-control reader, never as a public HTTP resource.
    del build_control_reader
    from city_layout_r10_contract import restore_r9_context
    info, reader = restore_r9_context(info, reader)
    get = lru_cache(maxsize=None)(reader)
    hashes = info["files_sha256"]
    meta = info[KEY]
    assert meta["page"] == PAGE and meta["manifest"] == MANIFEST and meta["bundle"] == BUNDLE
    assert meta["offline_entry"] == "index.html"
    assert json.loads(get(MANIFEST)) == meta, "Live manifest differs from build-info"
    resources = meta["files_sha256"]
    expected_resources = {path for path in hashes if path.startswith(FOLDER + "/") and path != MANIFEST} | {PAGE}
    assert set(resources) == expected_resources, "Manifest omitted a published R9 asset"
    mandatory = {DATA, CSV, SVG, AUDIT, FOLDER + "/atlas.css", FOLDER + "/atlas.js",
                 FOLDER + "/history/release-before-r9.json", PAGE}
    assert mandatory <= set(resources)
    for path in [*resources, MANIFEST, BUNDLE, "release.json"]:
        raw = get(path)
        assert isinstance(raw, bytes), (path, "Reader did not return actual resource bytes")
        assert digest(raw) == hashes[path], (path, "Published resource hash mismatch")
        if path in resources:
            assert hashes[path] == resources[path], (path, "R9 manifest hash mismatch")
    for suffix in ("css", "js"):
        assert get(FOLDER + "/atlas." + suffix) == (ROOT / "web" / (VERSION + "." + suffix)).read_bytes()

    data = json.loads(get(DATA))
    assert data["published_inputs_sha256"] == meta["published_inputs_sha256"]
    assert set(data["published_inputs_sha256"]) == {"city-atlas/atlas.json", "city-nodes/readings.json"}
    for path, checksum in data["published_inputs_sha256"].items():
        assert digest(get(path)) == checksum == hashes[path], (path, "Published source input changed")
    atlas, old_nodes = json.loads(get("city-atlas/atlas.json")), json.loads(get("city-nodes/readings.json"))
    research = verify_data(data, meta, info, atlas, old_nodes)
    assert data["source_audit"] == AUDIT
    assert get(AUDIT) == (ROOT / "research/city-spatial-r9/source-audit.json").read_bytes()
    audit = json.loads(get(AUDIT))
    assert audit["schema"] == "luoyang-city-spatial-r9-source-audit-v1" and audit["research_version"] == "R9.1"
    for name in ("new_ancient_coordinates", "new_bank_geometries", "new_bridgehead_coordinates", "evidence_grade_upgrades"):
        assert audit[name] == 0, (name, "Access follow-up became an unsupported spatial upgrade")
    csv_count = verify_csv(get(CSV), data)
    map_result = verify_svg(get(SVG), data, standalone=True)
    doc, inline_svg = verify_page(get(PAGE), data, hashes)
    assert get(SVG) == inline_svg.replace(b'href="#decision-', ('href="' + BASE + PAGE + '#decision-').encode())
    expected_downloads = [SVG, CSV, DATA, AUDIT, MANIFEST, BUNDLE]
    assert doc.downloads == meta["download_files"] == expected_downloads

    protected = meta["protected_files_sha256"]
    required = {"luoyang-city-nodes.html", "city-nodes/readings.json", "city-nodes/segments.csv", "city-nodes/manifest.json",
                "downloads/luoyang-city-nodes.zip", "all-roads/records.json", V12.full, V12.small, V12.metadata,
                "luoyang-panorama-v13.html", "panorama-v13/review.json", "panorama-v13/manifest.json"}
    for stage in ("city_nodes_r7", "panorama_review_v13"):
        required.update(info[stage]["files_sha256"])
    assert required <= set(protected), "Prior maps, downloads or approved image lost protection"
    assert ".nojekyll" not in protected
    for path, checksum in protected.items():
        assert digest(get(path)) == hashes[path] == checksum, (path, "Protected predecessor changed")
    assert digest(get(V12.full)) == V12.full_sha and digest(get(V12.small)) == V12.small_sha

    prior = meta["predecessor_release"]
    assert prior["path"] == FOLDER + "/history/release-before-r9.json"
    prior_raw = get(prior["path"])
    assert digest(prior_raw) == prior["sha256"] == hashes[prior["path"]]
    expected_release = json.loads(prior_raw)
    expected_release["extensions"] = sorted(set(expected_release["extensions"]) | {VERSION})
    expected_release[KEY + "_version"] = VERSION
    expected_release["current_milestone"] = "盛时 R9.1 · 城市空间总图、20项判断与V13修订候选"
    following = info.get("panorama_review_v13_r2")
    if following:
        following_prior = following["predecessor_release"]
        release_raw = get(following_prior["path"])
        assert digest(release_raw) == following_prior["sha256"] == hashes[following_prior["path"]]
    else:
        release_raw = get("release.json")
    assert json.loads(release_raw) == expected_release, "R9 release changed more than its declared additions"
    assert expected_release["homepage_hero_revision"] == V12.revision

    with ZipFile(io.BytesIO(get(BUNDLE))) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)), "Duplicate ZIP members"
        expected_members = (set(resources) - {PAGE}) | {MANIFEST, "index.html"}
        assert set(names) == expected_members, "Incomplete or unexpected offline bundle members"
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            assert not path.is_absolute() and ".." not in path.parts and "\\" not in item.filename
            assert not item.is_dir() and not stat.S_ISLNK(item.external_attr >> 16)
            if item.filename != "index.html":
                assert archive.read(item.filename) == get(item.filename), (item.filename, "Offline evidence differs")
        offline = archive.read("index.html")
        expected_offline = get(PAGE)
        for page in ("index.html", "prosperity-city-atlas.html", "luoyang-city-nodes.html", "luoyang-panorama-v13-r2.html"):
            expected_offline = expected_offline.replace(('href="' + page + '"').encode(), ('href="' + BASE + page + '"').encode())
        expected_offline = expected_offline.replace(('href="./' + BUNDLE + '"').encode(), ('href="' + BASE + BUNDLE + '"').encode())
        assert offline == expected_offline, "Offline HTML changed beyond the declared navigation rewrites"
        verify_page(offline, data, hashes, offline=True)
        member_count = len(names)
    return dict(status="passed", source_commit=info["source_commit"], research=research,
                csv_rows=csv_count, figure=map_result, downloads=len(expected_downloads),
                offline_members=member_count, protected_public_files=len(protected),
                new_historical_coordinates=0, new_shoreline_geometries=0, evidence_grade_upgrades=0,
                homepage_revision=V12.revision, homepage_replacement_approved=False)
