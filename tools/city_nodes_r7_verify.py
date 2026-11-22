"""Independently verify R7 evidence joins, source geometry and delivered resources.

The verifier reads the published bytes through ``get``. Repository originals are
used only as immutable evidence inputs, never as a substitute for a missing live
resource. A matching count is insufficient: retained values and JSON pointers
must also agree.
"""
import csv
import hashlib
import io
import json
import posixpath
import re
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from city_nodes_r7_contract import BASE, BUILD_CONTROL_FILES, BUNDLE, FOLDER, HOME_EDITS, KEY, MANIFEST, PAGE, ROAD_ENTRY, VERSION, restore_home
from homepage_artwork_v10 import V12

ROOT = Path(__file__).resolve().parents[1]
DATA = FOLDER + "/readings.json"
CSV = FOLDER + "/segments.csv"
NODE_IDS = ("palace-yongning", "baima", "sima", "jianchun")
FIGURES = tuple(FOLDER + "/" + key + ".svg" for key in ("overview", *NODE_IDS))
NS = "{http://www.w3.org/2000/svg}"
REF_FIELDS = {"source_inputs", "geometry_refs", "native_geometry_refs"}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads((ROOT / path).read_bytes())


def pointer(document, path):
    """Resolve RFC 6901 pointers without accepting paths or negative array indices."""
    assert isinstance(path, str) and (path == "" or path.startswith("/")), path
    current = document
    for token in path.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            assert token.isdigit() and (token == "0" or not token.startswith("0")), path
            current = current[int(token)]
        else:
            current = current[token]
    return current


def references(value):
    """Include references in interpretive scenarios as well as finding cards."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key in REF_FIELDS:
                assert isinstance(item, list), key
                yield from item
            yield from references(item)
    elif isinstance(value, list):
        for item in value:
            yield from references(item)


def verify_source_inputs(data):
    hashes = data["source_inputs_sha256"]
    assert hashes, "No source input fingerprints"
    cache = {}
    for path, expected in hashes.items():
        file = (ROOT / path).resolve()
        assert file.is_relative_to(ROOT) and file.is_file(), path
        raw = file.read_bytes()
        assert digest(raw) == expected, (path, "Source input changed")
        if file.suffix == ".json":
            cache[path] = json.loads(raw)
    count = 0
    for ref in references(data):
        path = ref.get("source_path") or ref.get("path") or ref.get("file")
        where = ref.get("json_pointer", ref.get("pointer"))
        assert path in hashes, (path, "Referenced input hash missing")
        assert path in cache and where is not None, ref
        native = pointer(cache[path], where)
        if "native_geometry" in ref:
            assert ref["native_geometry"] == native, (path, where, "Native geometry changed")
        if "city_registration" in ref:
            assert ref["city_registration"] is False, "An independent frame was promoted to city coordinates"
        count += 1
    assert count, "No resolvable evidence inputs"
    return dict(files=len(hashes), resolved_pointers=count)


def _unique(rows, field="id"):
    ids = [row[field] for row in rows]
    assert len(ids) == len(set(ids)), (field, "Duplicate identifiers")
    return {row[field]: row for row in rows}


def verify_data(data, atlas):
    """Check content against previous research, not merely the new manifest."""
    assert data["schema"] == "luoyang-city-nodes-v1"
    assert data["research_version"] == "R7.1" and data["implementation_version"] == VERSION
    assert data["target_years"] == [516, 528]
    assert data["new_historical_coordinates"] == data["new_shoreline_geometries"] == 0
    assert data["source_frames_registered_together"] is False
    assert data["homepage_revision"] == V12.revision
    assert [node["id"] for node in data["nodes"]] == list(NODE_IDS)
    nodes = _unique(data["nodes"])
    original = load("research/roads-r62/catalog.json")
    old_roads = _unique(original["records"])
    old_waters = _unique(atlas["waters"])
    old_entities = _unique(atlas["entities"])
    assert (len(old_entities), len(old_roads), len(old_waters)) == (339, 84, 34)
    road_ids, water_ids, entity_ids = set(old_roads), set(old_waters), set(old_entities)
    all_findings, all_relations = [], []
    for node in data["nodes"]:
        source = load("research/city-nodes-r7/reviews/" + node["id"] + ".json")
        for key, value in source.items():
            assert node[key] == value, (node["id"], key, "Reviewed decision changed during publication")
        assert node["schema"] == "luoyang-node-review-v1" and node["target_years"] == [516, 528]
        for key, value in node.items():
            if key.startswith(("accepted_new_", "new_field_", "new_excavation_")):
                assert value == 0, (node["id"], key)
        assert set(node["road_ids"]) <= road_ids and set(node["water_ids"]) <= water_ids
        assert set(node["entity_ids"]) <= entity_ids
        sources = _unique(node["source_refs"])
        for source in sources.values():
            for field in ("title", "url", "locator", "access_status", "checked_on", "source_kind"):
                assert source.get(field), (source["id"], field)
            assert urlsplit(source["url"]).scheme in ("http", "https"), source["url"]
        for finding in node["findings"]:
            for field in ("title", "public_label", "claim", "basis_kind", "period", "source_ids",
                          "source_inputs", "drawing_decision", "change_from_prior", "limitation"):
                assert finding.get(field), (finding["id"], field)
            assert len(finding["public_label"]) <= 18, finding["id"]
            assert set(finding["source_ids"]) <= set(sources), finding["id"]
            assert set(finding["road_ids"]) <= set(node["road_ids"]), finding["id"]
            assert set(finding["water_ids"]) <= water_ids, finding["id"]
        for relation in node["relations"]:
            for field in ("from", "to", "relation", "status", "period", "source_ids", "drawing_decision"):
                assert relation.get(field), (relation["id"], field)
            assert set(relation["source_ids"]) <= set(sources), relation["id"]
        assert node["next_originals"]
        for item in node["next_originals"]:
            assert all(item.get(key) for key in ("title", "locator", "needed_to_decide", "status")), node["id"]
        all_findings.extend(node["findings"])
        all_relations.extend(node["relations"])
    _unique(all_findings)
    _unique(all_relations)
    guides = _unique(data["guides"])
    assert set(guides) == {"palace", "yongning", "avenue", "southgate", "luo", "bridge"}
    for guide in guides.values():
        assert 0 <= guide["x"] <= 100 and 0 <= guide["y"] <= 100
        assert guide["node"] is None or guide["node"] in nodes
        assert set(guide["road_ids"]) <= road_ids and set(guide["water_ids"]) <= water_ids
        assert guide["statement"] and guide["level"] and guide["link"]
    expected_ids = set(r for n in nodes.values() for r in n["road_ids"]) | set(r for g in guides.values() for r in g["road_ids"])
    rows = _unique(data["segments"])
    assert list(rows) == [r["id"] for r in original["records"] if r["id"] in expected_ids]
    sources = original["sources"]
    if isinstance(sources, list):
        sources = _unique(sources)
    for rid, row in rows.items():
        for key, value in old_roads[rid].items():
            assert row[key] == value, (rid, key, "Previous road evidence changed")
        assert row["node_ids"] == [n["id"] for n in nodes.values() if rid in n["road_ids"]]
        assert row["geometry_status"] == ("source_frame" if row["geometry_refs"] else "relation_only")
        expected_temporal = "changes_within_window" if rid == "B01" else "documentary_reference" if row["group"] in ("documentary", "bridge") else "phase_not_resolved"
        assert row["temporal_status"] == expected_temporal, (rid, "Period was promoted")
        assert row["temporal_label"] and row["geometry_label"]
        assert row["original_url"] == BASE + "luoyang-all-roads.html#" + rid
        expected_findings = [dict(node_id=n["id"], **f)
                             for n in nodes.values() for f in n["findings"] if rid in f["road_ids"]]
        assert row["findings"] == expected_findings, (rid, "Finding join is incomplete")
        expected_context = [dict(node_id=n["id"], **f)
                            for n in nodes.values() for f in n["findings"] if rid in f.get("context_road_ids", [])]
        assert row["context_findings"] == expected_context, (rid, "Context finding became a road measurement")
        cited = {(f["node_id"], sid) for f in expected_findings + expected_context for sid in f["source_ids"]}
        expected_sources = [dict(node_id=n["id"], **s) for n in nodes.values() for s in n["source_refs"] if (n["id"], s["id"]) in cited]
        assert row["review_source_citations"] == expected_sources, (rid, "Review citations are incomplete")
        expected_next = [dict(node_id=n["id"], **item) for n in nodes.values() if n["id"] in row["node_ids"] for item in n["next_originals"]]
        assert row["next_originals"] == expected_next, (rid, "Next original source is lost")
        assert [s["id"] for s in row["source_citations"]] == row["source_refs"]
        for citation in row["source_citations"]:
            for key, value in sources[citation["id"]].items():
                assert citation[key] == value, (rid, citation["id"], key)
    expected_waters = set(w for n in nodes.values() for w in n["water_ids"]) | set(w for g in guides.values() for w in g["water_ids"]) | set(w["id"] for r in rows.values() for w in r.get("water_constraints", []))
    waters = _unique(data["waters"])
    assert list(waters) == [w["id"] for w in atlas["waters"] if w["id"] in expected_waters]
    for wid, water in waters.items():
        for key, value in old_waters[wid].items():
            assert water[key] == value, (wid, key, "Previous water evidence changed")
        assert water["node_ids"] == [n["id"] for n in nodes.values() if wid in n["water_ids"]]
        assert water["original_url"] == BASE + "luoyang-water-atlas.html#" + wid
    for index, originals, keys, target in (("entity_index", old_entities, ("name", "placement", "period"), "prosperity-city-atlas.html#entity-"),
                                            ("road_index", old_roads, ("name", "group", "entity_ids"), "luoyang-all-roads.html#"),
                                            ("water_index", old_waters, ("name",), "luoyang-water-atlas.html#")):
        actual = _unique(data[index])
        assert list(actual) == list(originals), (index, "Coverage differs from previous catalog")
        node_field = {"entity_index": "entity_ids", "road_index": "road_ids", "water_index": "water_ids"}[index]
        for identifier, row in actual.items():
            for key in keys:
                assert row[key] == originals[identifier].get(key, []), (index, identifier, key)
            assert row["node_ids"] == [n["id"] for n in nodes.values() if identifier in n[node_field]]
            assert row["url"] == BASE + target + identifier
    counts = dict(nodes=4, findings=len(all_findings), relations=len(all_relations), segments=len(rows), waters=len(waters),
                  entities_indexed=339, roads_indexed=84, waters_indexed=34)
    assert data["counts"] == counts
    assert nodes["baima"]["gate_to_central_cross_m"] is None
    assert nodes["baima"]["all_six_roads_proven_contemporary_516_528"] is False
    assert nodes["sima"]["all_roads_proven_contemporary_516_528"] is False
    assert nodes["sima"]["accepted_new_r4_wall_segments"] == 0
    old_baima = load("research/prosperity-v4/backbone-469/road01-source-audit.json")
    for key in ("gate_to_central_cross_m", "gate_to_central_cross_excavated_continuously", "world_coordinates"):
        assert old_baima["reusable_topology"][key] is None
    comparison = nodes["sima"]["new_source_comparison"]
    assert len(comparison["readings"]) == 2 and len(comparison["not_concluded"]) == 3
    assert comparison["readings"][0]["surveyed_pits"] == 168
    assert comparison["readings"][1]["reported_north_south_rows"] == 3
    assert all(r["excavated_pits"] == 13 for r in comparison["readings"])
    source_report = verify_source_inputs(data)
    return dict(counts=counts, source_inputs=source_report, new_historical_coordinates=0,
                target_window_upgrades=0, retained_road_records=len(rows), retained_water_records=len(waters))


class Document(HTMLParser):
    """Collect resource links as well as ordinary links, including picture sources."""
    def __init__(self, raw):
        super().__init__()
        self.ids, self.links, self.downloads, self.elements = [], [], [], []
        self.feed(raw.decode("utf-8"))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.elements.append((tag, attrs))
        if "id" in attrs:
            self.ids.append(attrs["id"])
        for key in ("href", "src", "poster"):
            if attrs.get(key):
                self.links.append(attrs[key])
        if attrs.get("srcset"):
            self.links.extend(item.strip().split()[0] for item in attrs["srcset"].split(",") if item.strip())
        if "download" in attrs:
            self.downloads.append(attrs["href"].removeprefix("./"))


def verify_links(raw, files, current=PAGE, document_ids=None):
    doc = Document(raw)
    assert len(doc.ids) == len(set(doc.ids)), (current, "Duplicate deep-link anchors")
    ids = set(doc.ids) if document_ids is None else set(document_ids)
    for url in doc.links:
        parts = urlsplit(url)
        if parts.scheme or parts.netloc:
            continue
        if parts.path:
            path = posixpath.normpath(posixpath.join(posixpath.dirname(current), unquote(parts.path)))
            assert path in files, (current, url, "Missing local resource")
            if path == current and parts.fragment:
                assert unquote(parts.fragment) in ids, (current, url)
        elif parts.fragment:
            assert unquote(parts.fragment) in ids, (current, url, "Missing anchor")
    return doc


def _points(element):
    return [[float(n) for n in point.split(",")] for point in element.get("points", "").split()]


def _path_points(element):
    """Read the straight native paths without reusing the renderer's serializer."""
    value = element.get("d", "")
    token = r"[MLZ]|[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    assert not re.sub(token, "", value).replace(",", "").strip(), value
    parts = re.findall(token, value)
    assert parts and parts[0] == "M", value
    if parts[-1] == "Z":
        parts.pop()
    assert len(parts) % 3 == 0, value
    points = []
    for index in range(0, len(parts), 3):
        assert parts[index] == ("M" if index == 0 else "L"), value
        points.append([float(parts[index + 1]), float(parts[index + 2])])
    return points


def _frame_shapes(element, frame, inherited=None):
    active = element.get("data-frame", inherited)
    if active == frame and element.tag in (NS + "path", NS + "polyline", NS + "polygon", NS + "circle"):
        yield element
    for child in element:
        yield from _frame_shapes(child, frame, active)


def verify_sima_geometry(svg):
    native = load("research/prosperity-r5/sima-road.json")["image"]["sima_road_ink_px"]
    shapes = list(_frame_shapes(svg, "frame-sima2023"))
    lines = [shape for shape in shapes if shape.tag in (NS + "path", NS + "polyline")]
    assert len(lines) == len(native) == 6, "Sima source must retain exactly six separate native line parts"
    assert [_path_points(line) if line.tag == NS + "path" else _points(line) for line in lines] == native, "Sima source gaps or pixel coordinates changed"
    assert [line.get("data-sima-atomic-line") for line in lines] == [str(i) for i in range(6)]
    assert [line.get("data-source-pointer") for line in lines] == ["/image/sima_road_ink_px/" + str(i) for i in range(6)]
    boxes = [e for e in svg.iter() if e.get("data-role") == "source-region-box-not-wall"]
    assert len(boxes) == 1 and boxes[0].get("stroke-dasharray"), "Source range box was promoted to a surveyed wall"
    expected = load("research/prosperity-r5/sima-road.json")["image"]["storage_box_centerline_px"]
    box = boxes[0]
    assert [float(box.get("x")), float(box.get("y")), float(box.get("x")) + float(box.get("width")),
            float(box.get("y")) + float(box.get("height"))] == expected
    return dict(sima_native_line_parts=6)


def verify_native_features(svg, key):
    """Artwork viewport transforms may change; the underlying 06a ink may not."""
    source = {f["id"]: f for f in load("research/prosperity-v1/geographic-evidence.json")["features"]}
    seen = {}
    for element in svg.iter():
        fid = element.get("data-native-geometry")
        if fid:
            assert fid in source, (key, fid)
            seen.setdefault(fid, []).append(element)
    for fid, elements in seen.items():
        shape = source[fid]["source_pdf_geometry"]
        if shape["type"] == "Point":
            assert len(elements) == 1 and elements[0].tag == NS + "circle", (key, fid)
            assert [float(elements[0].get("cx")), float(elements[0].get("cy"))] == shape["coordinates"], (key, fid)
        else:
            expected = [shape["coordinates"]] if shape["type"] == "LineString" else shape["coordinates"]
            assert all(e.tag == NS + "path" for e in elements), (key, fid)
            assert [_path_points(e) for e in elements] == expected, (key, fid, "Native 06a geometry changed")
    if key == "overview":
        assert set(seen) == {fid for fid in source if not fid.startswith("geo-modern-")}
    elif key == "palace-yongning":
        assert {"geo-yongning-temple-walls", "geo-yongning-pagoda-reference", "geo-changhe-palace-gate", "geo-tongtuo-avenue"} <= set(seen)
    elif key == "jianchun":
        assert "geo-jianchun-gate" in seen
    return len(seen)


def verify_water_frame(svg):
    source = load("research/water-atlas/huang-figure1.json")
    frames = [e for e in svg.iter() if e.get("data-frame") == "huang-figure1"]
    assert len(frames) == 1 and frames[0].get("data-city-registration") == "false"
    frame = frames[0]
    marks = [e for e in frame.iter() if e.get("data-water-ref")]
    assert len(marks) == len(source["traces"])
    for index, (mark, original) in enumerate(zip(marks, source["traces"], strict=True)):
        wid, name, kind, coords = original
        assert mark.get("data-water-ref") == wid
        assert mark.get("data-source-pointer") == "/traces/" + str(index)
        if kind == "symbol":
            circles = list(mark.iter(NS + "circle"))
            assert len(circles) == 1
            assert [float(circles[0].get("cx")), float(circles[0].get("cy"))] == coords[0]
        else:
            paths = list(mark.iter(NS + "path"))
            assert len(paths) == 1 and _path_points(paths[0]) == coords, wid
            if kind == "dry":
                assert paths[0].get("stroke-dasharray"), wid
    return len(marks)


def verify_figure(svg, key, data, anchors):
    assert svg.tag == NS + "svg" and svg.get("viewBox"), key
    assert svg.get("data-new-geographic-coordinates") == "0", key
    _unique([{"id": e.get("id")} for e in svg.iter() if e.get("id")])
    road_ids = {r["id"] for r in data["segments"]}
    node_ids = {n["id"] for n in data["nodes"]}
    linked = set()
    for element in svg.iter():
        if element.get("data-segment-ref"):
            identifier = element.get("data-segment-ref")
            assert identifier in road_ids, (key, identifier)
            target = element.get("href") or element.get("{http://www.w3.org/1999/xlink}href") or ""
            assert urlsplit(target).fragment == "segment-" + identifier, (key, identifier, "Diagram opens another record")
            linked.add(identifier)
        href = element.get("href") or element.get("{http://www.w3.org/1999/xlink}href")
        if href:
            parts = urlsplit(href)
            if not parts.path or parts.path.endswith(PAGE):
                assert parts.fragment in anchors, (key, href)
    if key in node_ids:
        node = next(n for n in data["nodes"] if n["id"] == key)
        assert set(node["road_ids"]) <= linked, (key, "A reviewed road cannot be looked up on the diagram")
    else:
        for nid in node_ids:
            assert any((e.get("href") or "").endswith("#node-" + nid) for e in svg.iter()), nid
    report = dict(linked_segments=len(linked), retained_06a_features=verify_native_features(svg, key))
    if key == "sima":
        report.update(verify_sima_geometry(svg))
    if key == "overview":
        report["retained_water_marks"] = verify_water_frame(svg)
    return report


def webp_size(raw):
    """Read VP8/VP8L/VP8X canvas sizes with the standard library used in CI."""
    assert raw[:4] == b"RIFF" and raw[8:12] == b"WEBP", "Not a WebP file"
    limit = int.from_bytes(raw[4:8], "little") + 8
    assert limit == len(raw), "Truncated WebP container"
    offset = 12
    while offset + 8 <= limit:
        tag = raw[offset:offset + 4]
        length = int.from_bytes(raw[offset + 4:offset + 8], "little")
        chunk = raw[offset + 8:offset + 8 + length]
        assert len(chunk) == length
        if tag == b"VP8X":
            assert len(chunk) >= 10
            return (1 + int.from_bytes(chunk[4:7], "little"), 1 + int.from_bytes(chunk[7:10], "little"))
        if tag == b"VP8 ":
            assert len(chunk) >= 10 and chunk[3:6] == b"\x9d\x01\x2a"
            return (int.from_bytes(chunk[6:8], "little") & 0x3fff,
                    int.from_bytes(chunk[8:10], "little") & 0x3fff)
        if tag == b"VP8L":
            assert len(chunk) >= 5 and chunk[0] == 0x2f
            bits = int.from_bytes(chunk[1:5], "little")
            return ((bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1)
        offset += 8 + length + (length & 1)
    raise AssertionError("WebP has no supported image chunk")


def verify_homepage(meta, hashes, get):
    expected_sizes = {V12.full: (1672, 941), V12.small: (960, 540)}
    hero = meta["hero"]
    assert hero["revision"] == V12.revision and (hero["width"], hero["height"]) == (1672, 941)
    for path, copy_path, checksum in ((V12.full, hero["full"], V12.full_sha), (V12.small, hero["small"], V12.small_sha)):
        raw = get(path)
        assert digest(raw) == hashes[path] == checksum, (path, "Approved V12 artwork changed")
        assert webp_size(raw) == expected_sizes[path], path
        assert get(copy_path) == raw and hashes[copy_path] == checksum, (copy_path, "Guide repainted or cropped V12")
    previous = meta["predecessor_homepage"]
    assert set(previous) == {"index.html", "v3.0-dual.html"}
    for path, entry in previous.items():
        archive = get(entry["archive"])
        assert digest(archive) == hashes[entry["archive"]] == entry["sha256"], entry["archive"]
        actual = get(path)
        assert restore_home(actual) == archive, (path, "Homepage edit extends outside allowed insertions")
        for before, after in HOME_EDITS:
            assert actual.count(after) == 1 and archive.count(before) == 1, path
        assert f'data-hero-revision="{V12.revision}"'.encode() in actual
        assert V12.full.encode() in actual and V12.small.encode() in actual
    return dict(revision=V12.revision, full_size=list(expected_sizes[V12.full]),
                small_size=list(expected_sizes[V12.small]), reversible_entries=2)


def verify_csv(raw, data):
    """All evidence-bearing columns must round-trip, not just road names."""
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    assert len(rows) == len(data["segments"])
    assert rows and [row["id"] for row in rows] == [row["id"] for row in data["segments"]]
    # The public CSV serializes nested values as JSON to keep their objects and
    # measurement qualifications unambiguous. Required fields are checked below.
    required = {"id", "name", "period", "node_ids", "geometry_status", "temporal_status",
                "source_refs", "locatable_segment", "start", "end", "gates", "water_constraints",
                "reported_metrics", "missing_evidence", "source_inputs", "geometry_refs", "findings"}
    fields = data["csv_fields"]
    assert list(rows[0]) == fields
    assert required <= set(fields), ("CSV omits evidence", sorted(required - set(fields)))
    for row, segment in zip(rows, data["segments"], strict=True):
        for field in fields:
            expected = segment.get(field, "")
            actual = row[field]
            if isinstance(expected, (dict, list)) or expected is None:
                try:
                    actual = json.loads(actual)
                except json.JSONDecodeError as error:
                    raise AssertionError((segment["id"], field, "Lossy CSV value")) from error
            assert actual == expected, (segment["id"], field, "CSV differs from JSON")
    return len(rows)


def verify_protected_files(meta, hashes, get, build_control_reader=None):
    """Verify public bytes and separately account for Pages' root control marker.

    Early R7.1 manifests kept the marker in protected_files_sha256. Accept that
    shape by extracting only the exact known path; never infer exclusions from
    an HTTP error, a leading dot, or a caller-supplied list. New manifests split
    the two sets explicitly. The build checks both sets' actual local bytes;
    callers can additionally supply a local reader for control-byte validation.
    """
    protected = dict(meta["protected_files_sha256"])
    if "build_control_files_sha256" in meta:
        controls = meta["build_control_files_sha256"]
        assert not BUILD_CONTROL_FILES.intersection(protected), "Control file remains in public protection table"
    else:
        controls = {path: protected.pop(path) for path in BUILD_CONTROL_FILES if path in protected}
    expected_controls = {path: hashes[path] for path in BUILD_CONTROL_FILES}
    assert controls == expected_controls, "Build controls differ from the fixed Pages contract or release hashes"
    for path, checksum in protected.items():
        assert digest(get(path)) == hashes[path] == checksum, (path, "Protected predecessor changed")
    if build_control_reader is not None:
        for path, checksum in controls.items():
            assert digest(build_control_reader(path)) == checksum, (path, "Build control bytes changed")
    return protected, controls


def verify(info, reader, *, build_control_reader=None):
    get = lru_cache(maxsize=None)(reader)
    hashes = info["files_sha256"]
    meta = info[KEY]
    assert meta == json.loads(get(MANIFEST)), "Build-info and R7 manifest differ"
    assert meta["version"] == VERSION and meta["research_version"] == "R7.1"
    assert meta["source_commit"] == info["source_commit"]
    assert (meta["page"], meta["manifest"], meta["bundle"]) == (PAGE, MANIFEST, BUNDLE)
    assert VERSION in json.loads(get("release.json"))["extensions"]
    resources = meta["files_sha256"]
    required = {DATA, CSV, FOLDER + "/atlas.css", FOLDER + "/atlas.js", *FIGURES}
    assert required <= set(resources)
    assert MANIFEST not in resources, "Manifest cannot hash itself"
    all_r7 = {path for path in hashes if path.startswith(FOLDER + "/") and path != MANIFEST}
    assert all_r7 <= set(resources), "An R7 resource is absent from its manifest"
    for path, checksum in resources.items():
        assert digest(get(path)) == hashes[path] == checksum, (path, "Resource fingerprint mismatch")
    for path in (PAGE, MANIFEST, BUNDLE):
        assert digest(get(path)) == hashes[path], path
    data = json.loads(get(DATA))
    assert data["source_commit"] == info["source_commit"]
    report = verify_data(data, json.loads(get("city-atlas/atlas.json")))
    assert meta["counts"] == data["counts"]
    assert meta["source_inputs_sha256"] == data["source_inputs_sha256"]
    assert meta["published_inputs_sha256"] == data["published_inputs_sha256"]
    assert meta["baseline_counts"] == dict(entities=339, roads=84, waters=34)
    assert meta["new_historical_coordinates"] == meta["new_shoreline_geometries"] == 0
    assert meta["source_frames_registered_together"] is False and meta["homepage_revision"] == V12.revision
    for path, checksum in meta["published_inputs_sha256"].items():
        assert digest(get(path)) == hashes[path] == checksum, (path, "Published input changed")
    # R6.2's published catalog is independently compared to its repository input.
    public_roads = json.loads(get("all-roads/records.json"))
    for key, value in load("research/roads-r62/catalog.json").items():
        assert public_roads[key] == value, (key, "Predecessor road catalog changed")
    protected, build_controls = verify_protected_files(meta, hashes, get, build_control_reader)
    mandatory_protected = {"all-roads/records.json", "all-roads/manifest.json", "downloads/luoyang-all-roads.zip",
                           "city-atlas/atlas.json", "water-location-data.json", "water-locations.csv", V12.full, V12.small, V12.metadata}
    assert mandatory_protected <= set(protected), "A predecessor is outside R7 preservation coverage"
    old_road = meta["predecessor_road_page"]
    road_html = get(old_road["path"])
    assert road_html.count(ROAD_ENTRY) == road_html.count(b'id="r7-road-entry"') == 1
    road_before = get(old_road["archive"])
    assert road_html.replace(ROAD_ENTRY, b"", 1) == road_before
    assert digest(road_before) == old_road["sha256"] == hashes[old_road["archive"]]
    csv_rows = verify_csv(get(CSV), data)
    document = verify_links(get(PAGE), hashes)
    anchors = set(document.ids)
    expected_anchors = {"main", "overview", "panorama", "register", "segment-query", "node-filter", "evidence-filter",
                        "segment-count", "segment-empty", "segment-clear", "downloads"}
    expected_anchors |= {"node-" + node["id"] for node in data["nodes"]}
    expected_anchors |= {"map-" + key for key in ("overview", *NODE_IDS)}
    expected_anchors |= {"segment-" + row["id"] for row in data["segments"]}
    expected_anchors |= {"water-" + row["id"] for row in data["waters"]}
    expected_anchors |= {"guide-" + row["id"] for row in data["guides"]}
    expected_anchors |= {"finding-" + finding["id"] for node in data["nodes"] for finding in node["findings"]}
    assert expected_anchors <= anchors, ("Missing reader anchors", sorted(expected_anchors - anchors))
    expected_downloads = [*FIGURES, CSV, DATA, MANIFEST, BUNDLE]
    assert document.downloads == meta["download_files"] == expected_downloads
    for node in data["nodes"]:
        for source in node["source_refs"]:
            assert source["url"] in document.links, (node["id"], source["id"], "Source not exposed to readers")
    for guide in data["guides"]:
        assert guide["link"].removeprefix("#") in anchors, guide["id"]
    # Full indexes are usable links, not merely copied identifiers in a JSON file.
    target_ids = {}
    for index in ("entity_index", "road_index", "water_index"):
        for row in data[index]:
            assert row["url"].startswith(BASE)
            target = urlsplit(row["url"][len(BASE):])
            if target.path not in target_ids:
                target_ids[target.path] = set(Document(get(target.path)).ids)
            assert target.fragment in target_ids[target.path], (index, row["id"], "Coverage link has no target")
    figures = {}
    for path in FIGURES:
        key = Path(path).stem
        figures[key] = verify_figure(ET.fromstring(get(path)), key, data, anchors)
    homepage = verify_homepage(meta, hashes, get)
    with ZipFile(io.BytesIO(get(BUNDLE))) as archive:
        members = archive.namelist()
        assert len(members) == len(set(members)), "ZIP contains duplicate members"
        assert all(not p.startswith("/") and ".." not in Path(p).parts for p in members), "Unsafe ZIP paths"
        assert archive.testzip() is None
        expected = set(resources) | {"index.html", MANIFEST}
        assert set(members) == expected, ("Incomplete offline bundle", sorted(expected - set(members)), sorted(set(members) - expected))
        for path in members:
            if path != "index.html":
                assert archive.read(path) == get(path), (path, "Offline resource differs from live")
        offline = verify_links(archive.read("index.html"), set(members), current="index.html")
        assert expected_anchors <= set(offline.ids)
        assert meta["hero"]["full"] in members and meta["hero"]["small"] in members, "Offline guide omitted the approved full or small image"
    return dict(status="passed", source_commit=info["source_commit"], **report,
                csv_rows=csv_rows, figures=figures, homepage=homepage,
                protected_files=len(protected) + len(build_controls), protected_public_files=len(protected),
                build_control_files=len(build_controls), build_control_content_verified=build_control_reader is not None,
                downloads=len(expected_downloads), offline_members=len(members),
                distinct_resources=get.cache_info().misses)
