"""Publish the three Yongning study images without replacing a panorama attempt.

The source, geometry and review documents remain original downloadable bytes.
Publication checks bind those documents to the displayed files; they do not
turn a local geometry observation into approval of the whole panorama.
"""
import argparse
import hashlib
from html import escape
import io
import json
from pathlib import Path, PurePosixPath
import re
import xml.etree.ElementTree as ET

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = "research/panorama-r12/yongning-triptych-20261124"
PAGE = "luoyang-yongning-study.html"
FOLDER = "panorama-v14/yongning-study"
MANIFEST = FOLDER + "/manifest.json"
VERSION = "yongning-triptych-20261124"
IMAGE_FILES = {
    "overlay": "overlay.png",
    "corrected_local": "corrected-local.png",
    "reintegration_preview": "reintegration-preview.png",
}
IMAGE_TITLES = {
    "overlay": "基址叠加对照",
    "corrected_local": "修正局部图",
    "reintegration_preview": "全景回嵌预览",
}
ANCHORS = {
    "overlay": "overlay",
    "corrected_local": "corrected-local",
    "reintegration_preview": "reintegration-preview",
}
INPUT_FILES = (*IMAGE_FILES.values(), "overlay.svg", "source.json", "geometry.json", "review.json")
DOWNLOAD_NAMES = {
    **{filename: IMAGE_TITLES[role] + " · PNG" for role, filename in IMAGE_FILES.items()},
    "overlay.svg": "基址叠加 · SVG",
    "source.json": "图像与来源记录",
    "geometry.json": "几何核对记录",
    "review.json": "实际审查记录",
    "manifest.json": "发布文件清单",
}
ENTRY = ('<a id="yongning-study-entry" href="./luoyang-yongning-study.html">'
         '永宁寺三图审查 · 基址、局部与回嵌预览</a>')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source_file(relative, root=ROOT):
    path = PurePosixPath(relative)
    assert not path.is_absolute() and ".." not in path.parts and "\\" not in relative, relative
    resolved = (root / relative).resolve()
    assert resolved.is_relative_to(root.resolve()) and resolved.is_file(), (relative, "Missing study input")
    return resolved


def text_list(value, label):
    assert isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value), label
    return value


def validate_inputs(root=ROOT):
    raw = {name: source_file(SOURCE_DIR + "/" + name, root).read_bytes() for name in INPUT_FILES}
    source, geometry, review = (json.loads(raw[name + ".json"]) for name in ("source", "geometry", "review"))
    inputs = source["inputs_sha256"]
    assert isinstance(inputs, dict) and inputs, "The study must identify its actual source inputs"
    assert {"research/panorama-r12/projection.json", "research/panorama-r12/projection-yongning-clean.svg"} <= set(inputs), "Frozen common projection inputs are required"
    for path, checksum in inputs.items():
        assert re.fullmatch(r"[a-f0-9]{64}", checksum), path
        assert digest(source_file(path, root).read_bytes()) == checksum, (path, "Study source changed")
    assert set(source["images"]) == set(IMAGE_FILES), "Exactly the three named study images are required"
    for role, filename in IMAGE_FILES.items():
        item = source["images"][role]
        assert item["path"] == SOURCE_DIR + "/" + filename, (role, "Image path differs from this study")
        assert item["sha256"] == digest(raw[filename]), (role, "Image identity differs from source record")
        assert all(type(item[key]) is int and item[key] > 0 for key in ("width", "height")), role
        assert isinstance(item["alt"], str) and item["alt"].strip(), role
        if "caption" in item:
            assert isinstance(item["caption"], str) and item["caption"].strip(), role
        with Image.open(io.BytesIO(raw[filename])) as image:
            assert image.format == "PNG" and image.size == (item["width"], item["height"]), (role, "Original PNG dimensions differ")
            image.verify()
    svg = ET.fromstring(raw["overlay.svg"])
    assert svg.tag == "{http://www.w3.org/2000/svg}svg" and svg.get("viewBox"), "Overlay must be an actual SVG"
    for node in svg.iter():
        assert node.tag.rsplit("}", 1)[-1] not in {"script", "foreignObject"}, "Overlay must remain a static drawing"
        for key, value in node.attrib.items():
            if key.rsplit("}", 1)[-1] == "href":
                assert value.startswith(("#", "data:image/")), "Overlay must be self-contained"
    assert isinstance(geometry, dict) and geometry, "The actual geometry review is required"
    projection_path = "research/panorama-r12/projection.json"
    projection = json.loads(source_file(projection_path, root).read_bytes())
    assert geometry["source_projection_path"] == projection_path
    assert geometry["source_projection_sha256"] == inputs[projection_path]
    assert geometry["ground_homography"] == projection["source_xy_m_to_canvas_homography"], "Frozen homography changed"
    assert geometry["ground_homography_modified"] is source["ground_homography_modified"] is False
    assert geometry["per_object_transform_fitted"] is source["per_object_transform_fitted"] is False
    assert geometry["field_registration_verified"] is False and geometry["new_ancient_coordinates"] == 0
    assert isinstance(review["status"], str) and review["status"].strip()
    assert review["homepage_replacement_approved"] is False
    assert review["full_panorama_accepted"] is False
    assert review["image_sha256"] == {role: source["images"][role]["sha256"] for role in IMAGE_FILES}, "Review describes different study images"
    assert geometry["image_sha256"] == review["image_sha256"], "Geometry record describes different study images"
    assert geometry["whole_ground_geometry_passed"] is review["whole_ground_geometry_passed"] is False
    assert source["homepage_replacement_approved"] is source["full_panorama_accepted"] is False
    assert set(review["audit_paths"]) <= set(inputs), "Original audit identities are missing"
    assert isinstance(review["summary"], str) and review["summary"].strip()
    assert text_list(review["findings"], "Review findings")
    assert text_list(review["remaining_limits"], "Remaining limits")
    return source, geometry, review, raw


def make_page(meta, source, geometry, review):
    """Keep the complete figures and their actual review readable without JS."""
    figures = []
    for number, role in enumerate(IMAGE_FILES, 1):
        image = meta["images"][role]
        description = source["images"][role]
        anchor = ANCHORS[role]
        figures.append(f'''<section id="{anchor}" class="image-panel panel-{anchor}" aria-labelledby="{anchor}-title">
<header class="panel-heading"><p class="eyebrow">{number:02d} / 03</p><h2 id="{anchor}-title">{IMAGE_TITLES[role]}</h2></header>
<figure data-study-image="{role}" data-source-sha256="{image['sha256']}"><a class="original-image" href="./{image['path']}" aria-label="打开{IMAGE_TITLES[role]}原图"><img src="./{image['path']}" width="{image['width']}" height="{image['height']}" alt="{escape(description['alt'], quote=True)}" {'fetchpriority="high"' if number == 1 else 'loading="lazy"'}></a>
<figcaption><p>{escape(description.get('caption', IMAGE_TITLES[role] + '，保留完整原幅供核对；具体判断见本轮实际审查记录。'))}</p><a href="./{image['path']}">打开原尺寸图</a></figcaption></figure></section>''')
    findings = "".join(f"<li>{escape(item)}</li>" for item in review["findings"])
    limits = "".join(f"<li>{escape(item)}</li>" for item in review["remaining_limits"])
    downloads = "".join(f'<a download href="./{escape(path, quote=True)}">{escape(DOWNLOAD_NAMES[PurePosixPath(path).name])}</a>' for path in meta["download_files"])
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>盛时洛阳 · 永宁寺三图审查</title><meta name="description" content="永宁寺基址叠加对照、修正局部图和全景回嵌预览。实际图像、几何核对与审查记录分别保留。">
<link rel="stylesheet" href="./{FOLDER}/study.css"></head>
<body data-study-version="{VERSION}" data-review-status="{escape(review['status'], quote=True)}"><a class="skip-link" href="#main">跳到正文</a>
<header class="site-header"><nav class="wrap" aria-label="网站导航"><a class="brand" href="./index.html">盛时洛阳</a><div><a href="./luoyang-panorama-v14.html">V14 试绘审查</a><a href="./luoyang-city-plan.html?view=yongning#plan-reader">永宁寺共同平面</a></div></nav></header>
<main id="main"><div class="intro wrap"><p class="eyebrow">永宁寺局部研究 · 2026-11-24</p><h1>从基址核对到全景回嵌</h1>
<p class="lead">先对照地面轮廓，再查看局部修正，最后回到完整画面。三幅图保留各自原始比例，实际审查结果与图像同时展示。</p>
<aside id="study-review-status" class="review-status" data-status="{escape(review['status'], quote=True)}" aria-labelledby="review-status-title"><h2 id="review-status-title">局部研究预览</h2><p>{escape(review['summary'])}</p><p>本页未批准替换全景或首页。既有六次 V14 试绘仍未通过，主显示第五次、第六次保留在附录；当前首页继续采用已批准的 V12。</p></aside>
<nav class="reading-path" aria-label="三图阅读顺序"><a href="#overlay">01 基址叠加</a><a href="#corrected-local">02 修正局部</a><a href="#reintegration-preview">03 全景回嵌</a><a href="#review">实际审查</a><a href="#downloads">下载原件</a></nav></div>
<div class="triptych wrap">{''.join(figures)}</div>
<section id="review" class="wrap evidence-section" aria-labelledby="review-title"><div class="section-heading"><p class="eyebrow">从实际图像与核对记录读取</p><h2 id="review-title">本轮审查记录</h2></div><ul id="review-findings" class="findings">{findings}</ul><p>核对位置与计算过程保留在<a href="./{FOLDER}/geometry.json">几何记录</a>；图像身份与输入见<a href="./{FOLDER}/source.json">来源记录</a>，完整判断见<a href="./{FOLDER}/review.json">审查原件</a>。</p>
<div class="geometry-note"><h3>地面关系与建筑表现分开判断</h3><p>{escape(geometry.get('summary', '可见基脚、遮挡范围与辅助引导线分别登记，完整坐标和显示变换见几何记录。'))}</p><p>共同透视底稿约束本轮图像对照；图中位置不产生新的实测坐标，上部建筑表现也不构成已证的历史复原。</p></div></section>
<section id="limits" class="wrap limits-section" aria-labelledby="limits-title"><h2 id="limits-title">仍保留的限制</h2><ul>{limits}</ul><p>局部观察不覆盖既有全景拒用结论，也不改变当前首页的批准状态。</p></section>
<section id="downloads" class="wrap downloads-section" aria-labelledby="downloads-title"><h2 id="downloads-title">下载三图与核对原件</h2><p>图像、来源、几何和审查分别下载。发布清单记录每项实际文件的大小与 SHA-256。</p><div class="download-links">{downloads}</div></section>
</main><footer class="wrap"><p>盛时洛阳 · 永宁寺三图审查 · 局部研究预览</p><p><a href="./luoyang-panorama-v14.html#attempt-history">回查六次全景试绘</a> · <a href="./index.html">返回 V12 首页</a></p></footer></body></html>'''


def build(site, source_commit, *, root=ROOT):
    source, geometry, review, raw = validate_inputs(root)
    assert re.fullmatch(r"[a-f0-9]{40}", source_commit), "Study publication needs the actual source commit"
    destination = site / FOLDER
    destination.mkdir(parents=True, exist_ok=True)
    for filename, content in raw.items():
        (destination / filename).write_bytes(content)
    css_path = "web/yongning-study.css"
    css = source_file(css_path, root).read_bytes()
    (destination / "study.css").write_bytes(css)
    files = [FOLDER + "/" + filename for filename in INPUT_FILES]
    images = {role: {key: item[key] for key in ("sha256", "width", "height")}
              | {"path": FOLDER + "/" + IMAGE_FILES[role]}
              for role, item in source["images"].items()}
    meta = dict(schema="luoyang-yongning-triptych-publication-v1", version=VERSION,
                source_commit=source_commit, page=PAGE, manifest=MANIFEST,
                source=FOLDER + "/source.json", geometry=FOLDER + "/geometry.json", review=FOLDER + "/review.json",
                review_status=review["status"], homepage_replacement_approved=False,
                full_panorama_accepted=False, homepage_revision="panorama-approved-v12",
                field_registration_verified=False, new_ancient_coordinates=0,
                images=images, download_files=[*files, MANIFEST],
                source_inputs_sha256={**source["inputs_sha256"], **{SOURCE_DIR + "/" + name: digest(content) for name, content in raw.items()}, css_path: digest(css)})
    (site / PAGE).write_text(make_page(meta, source, geometry, review), encoding="utf-8")
    files.extend((FOLDER + "/study.css", PAGE))
    meta["files_sha256"] = {path: digest((site / path).read_bytes()) for path in files}
    meta["files_bytes"] = {path: (site / path).stat().st_size for path in files}
    dump(site / MANIFEST, meta)
    return meta


def verify(info, reader, *, root=ROOT):
    from city_nodes_r7_verify import verify_links
    parent = info["panorama_review_v14"]
    meta, hashes = parent["yongning_study"], info["files_sha256"]
    assert meta["version"] == VERSION and meta["page"] == PAGE and meta["manifest"] == MANIFEST
    assert meta["source_commit"] == parent["source_commit"] == info["source_commit"]
    assert meta["homepage_replacement_approved"] is meta["full_panorama_accepted"] is False
    assert meta["homepage_revision"] == parent["homepage_revision"] == "panorama-approved-v12"
    assert meta["field_registration_verified"] is False and meta["new_ancient_coordinates"] == 0
    assert parent["status"] == "needs_revision" and parent["review_status"] == "rejected_needs_revision"
    source, geometry, review, raw = validate_inputs(root)
    assert meta["review_status"] == review["status"]
    assert json.loads(reader(MANIFEST)) == meta
    assert digest(reader(MANIFEST)) == hashes[MANIFEST]
    expected = {FOLDER + "/" + name for name in INPUT_FILES} | {PAGE, FOLDER + "/study.css"}
    assert set(meta["files_sha256"]) == set(meta["files_bytes"]) == expected, "Study inventory escaped its exact publication scope"
    assert {path for path in hashes if path.startswith(FOLDER + "/")} == expected - {PAGE} | {MANIFEST}
    for path, checksum in meta["files_sha256"].items():
        content = reader(path)
        assert digest(content) == checksum == hashes[path] == parent["files_sha256"][path], (path, "Published study bytes changed")
        assert len(content) == meta["files_bytes"][path], path
    for filename, content in raw.items():
        assert reader(FOLDER + "/" + filename) == content, (filename, "Published study differs from actual source")
    expected_inputs = {**source["inputs_sha256"], **{SOURCE_DIR + "/" + name: digest(content) for name, content in raw.items()},
                       "web/yongning-study.css": digest(source_file("web/yongning-study.css", root).read_bytes())}
    assert meta["source_inputs_sha256"] == expected_inputs, "Study input inventory is incomplete"
    for path, checksum in meta["source_inputs_sha256"].items():
        assert digest(source_file(path, root).read_bytes()) == checksum, (path, "Source input changed")
    assert set(meta["images"]) == set(IMAGE_FILES)
    for role, filename in IMAGE_FILES.items():
        expected_image = {key: source["images"][role][key] for key in ("sha256", "width", "height")}
        assert meta["images"][role] == expected_image | {"path": FOLDER + "/" + filename}
    assert reader(FOLDER + "/study.css") == source_file("web/yongning-study.css", root).read_bytes()
    assert reader(PAGE) == make_page(meta, source, geometry, review).encode("utf-8"), "Visible study or review differs from the actual records"
    assert meta["download_files"] == [*(FOLDER + "/" + name for name in INPUT_FILES), MANIFEST]
    doc = verify_links(reader(PAGE), hashes, current=PAGE)
    assert doc.downloads == meta["download_files"]
    assert {"main", "study-review-status", "review", "limits", "downloads", *ANCHORS.values()} <= set(doc.ids)
    assert len(doc.ids) == len(set(doc.ids))
    assert reader(parent["page"]).count(ENTRY.encode()) == 1, "V14 must have one exact study entry"
    previous = json.loads(reader(parent["record"]))["candidate"]
    assert previous["total_attempts"] == previous["latest_attempt"] == 6 and previous["displayed_attempt"] == 5
    assert previous["all_attempts_rejected"] is True
    return dict(status="passed", source_commit=info["source_commit"], review_status=review["status"],
                original_images=3, downloads=len(meta["download_files"]),
                source_files=len(meta["source_inputs_sha256"]), homepage_replacement_approved=False,
                full_panorama_accepted=False, prior_panorama_attempts_rejected=6)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=ROOT / "_site")
    parser.add_argument("--verify", action="store_true", required=True)
    args = parser.parse_args()
    info = json.loads((args.site / "build-info.json").read_bytes())
    print(json.dumps(verify(info, lambda path: (args.site / path).read_bytes()), ensure_ascii=False, indent=2))
