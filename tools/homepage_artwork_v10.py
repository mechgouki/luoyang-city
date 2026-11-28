"""Publish the selected homepage panorama and preserve earlier artwork and entry pages."""

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPROVED = "2026-11-21"
PAGES = ("index.html", "v3.0-dual.html")


@dataclass(frozen=True)
class Artwork:
    number: int
    full_sha: str
    small_sha: str
    alt: str
    source_sha: str = ""

    @property
    def revision(self):
        return f"panorama-approved-v{self.number}"

    @property
    def metadata(self):
        return f"homepage/approval-v{self.number}.json"

    @property
    def full(self):
        return f"_assets/{self.full_sha[:20]}-luoyang-{self.revision}.webp"

    @property
    def small(self):
        return f"_assets/{self.small_sha[:20]}-luoyang-{self.revision}-small.webp"

    def archive(self, page):
        return "homepage/history/" + page.replace(".html", f"-before-v{self.number}.html")


V9 = Artwork(9,
    "6465657667ba740d3fc99cde2495a864d3a8a446e2086c25984c0c547eed5825",
    "98459529d0a2d8210aaf2728b0c1673ca38b46df2f7b761c9064f1c21fe053b6",
    "北魏洛阳盛时艺术复原全景：宫城大殿、礼仪道路、寺院高塔、街巷、市集与远山。建筑外观、古代河道及具体院墙位置包含研究性推定与艺术表现。")
V10 = Artwork(10,
    "d8acc2686d3410c418109c60e4ccee9be78263fcce7168c69ab04efc2e7d6c7c",
    "5ac9f5a121a0fee2ea9d73741cf3c6b2c651074b860436aa42318680e31f8d4e",
    "北魏神龟二年（519）秋的洛阳复原图。从洛水永桥向北望，御道经景明寺入宣阳门，城内可见永宁寺九层塔与宫城。",
    "262e0797c09788f7871bca81c05d5e2c15d5ebc7ab8cf6c559ced68cf883a41e")
V11 = Artwork(11,
    "905ba057ff5eb2b1ad6b85af0d200ce3634f7d1ab1c23f35185438f55c52a31d",
    "7c53185140885a40b280af3dcb7f26326a5db52b3fbf5038804abf3f22e7bb9e",
    "北魏洛阳高视角复原图。近处是洛水与永桥，御道向北穿过宣阳门，左侧是永宁寺塔，远处是宫城。",
    "4d45e831b59f2f7550fe7129455f1da823098e8f34cf633223cd584d5b64a5bf")
V12 = Artwork(12,
    "d8d5be74d123b5eeaac50ce68955787e26686b92c1a30031f6c3289692fbf4c2",
    "eb836bc7ba458ae392c313c030ee7ed9654bd838bb46b62e8fdf418e5e369f21",
    "北魏洛阳盛时全幅取景复原图：宫城、永宁寺、主要街道、南城门、城外居民区、洛水与完整浮桥共同入画。建筑外观、古岸线、桥头及部分道路连接含研究推定与艺术表达。",
    "c7954dfc3ee659de756c62d0f634e40eddfd2ecc93cc8b833f53f6c0e0dc69ca")
CURRENT = V12
RELEASES = (
    (V9, V10, {"season": "神龟二年（519）秋"}),
    (V10, V11, {"selection_number": "07"}),
    (V11, V12, {"selection_label": "全幅取景版", "display_mode": "full_frame",
                "based_on_revision": V11.revision,
                "source_name": "exec-c8472c14-2738-49a1-bb35-d78a313bf415.png",
                "approval_quote": "好的 就换这张图",
                "historical_ground_truth_upgraded": False,
                "conversion": "Pillow WebP quality 92, method 6; original 1672×941 frame; mobile 960×540 Lanczos; no crop or repaint"}),
)
LAYOUT_SOURCE = ROOT / "web/homepage-full-frame-v12.css"
LAYOUT_SHA = hashlib.sha256(LAYOUT_SOURCE.read_bytes()).hexdigest()
LAYOUT_ASSET = f"_assets/{LAYOUT_SHA[:20]}-homepage-full-frame-v12.css"
LAYOUT_TAG = f'<link rel="stylesheet" href="./{LAYOUT_ASSET}" data-homepage-layout="full-frame-v12">'.encode()
# Every visible V12 change is reversible so older research baselines retain
# their original HTML and stylesheet. These updates belong only to the homepage.
V12_TEXT = tuple((old.encode(), new.encode()) for old, new in (
    ("北魏洛阳 · 研究性复原示意</figcaption>",
     "北魏洛阳 · 研究性复原示意 · 全幅取景版</figcaption>"),
    ('<a href="./dual-city-review.html">浏览全城总校核 B8 ↗</a>',
     '<a href="./dual-city-review.html">浏览全城总校核 B8 ↗</a>'
     '<a href="./luoyang-all-roads.html">查看全城道路与逐路证据 ↗</a>'
     '<a href="./luoyang-water-atlas.html">查看河流与水系定位 ↗</a>'),
    ("研究持续修订 · 当前成果 B1—B8。历史版本、图册与逐条来源继续保留；当前继续完善盛时平面、历史地形依据与城市分布。",
     "研究持续修订 · 已公开城市分布、全景、道路与水系。逐项来源、推定关系和未知位置均可追溯；历史版本与下载图册继续保留。"),
    ("当前整合版 v2.9 · 原始几何底图 v2.4",
     "盛时研究：516—528年 · 原始几何底图 v2.4"),
))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def replace_hero(html, old, new):
    if old == V12:
        if html.count(LAYOUT_TAG) != 1:
            raise ValueError("Expected one V12 full-frame stylesheet")
        html = html.replace(LAYOUT_TAG, b"", 1)
        for before, after in V12_TEXT:
            if html.count(after) != 1:
                raise ValueError("Expected one V12 homepage text replacement")
            html = html.replace(after, before, 1)
    fields = (
        ("data-hero-revision", old.revision, new.revision),
        ("src", "./" + old.full, "./" + new.full),
        ("srcset", "./" + old.small, "./" + new.small),
        ("alt", old.alt, new.alt),
    )
    for attr, source, target in fields:
        old_attr = f'{attr}="{source}"'.encode()
        if html.count(old_attr) != 1:
            raise ValueError(f"Expected one homepage {attr} matching {old.revision}")
        html = html.replace(old_attr, f'{attr}="{target}"'.encode(), 1)
    if new == V12:
        if LAYOUT_TAG in html or html.count(b"</head>") != 1:
            raise ValueError("Cannot append V12 full-frame stylesheet")
        html = html.replace(b"</head>", LAYOUT_TAG + b"</head>", 1)
        for before, after in V12_TEXT:
            if html.count(before) != 1:
                raise ValueError("Expected one pre-V12 homepage text replacement")
            html = html.replace(before, after, 1)
    return html


def restore_baseline(html):
    from panorama_v13_r2_contract import strip_current_entries
    from panorama_v13_contract import restore_home as restore_candidate_entry
    from city_nodes_r7_contract import restore_home
    html = restore_home(restore_candidate_entry(strip_current_entries(html)))
    for previous, artwork, _ in reversed(RELEASES):
        if f'data-hero-revision="{artwork.revision}"'.encode() in html:
            html = replace_hero(html, artwork, previous)
    return html


def publish(site):
    from homepage_v1 import dump

    info = json.loads((site / "build-info.json").read_bytes())
    release = json.loads((site / "release.json").read_bytes())
    hashes = info["files_sha256"]
    pages = {name: restore_baseline((site / name).read_bytes()) for name in PAGES}

    for previous, artwork, details in RELEASES:
        version = f"homepage-approved-v{artwork.number}"
        for target, expected in ((artwork.full, artwork.full_sha), (artwork.small, artwork.small_sha)):
            source = ROOT / "web/assets" / Path(target).name.removeprefix(expected[:20] + "-")
            if digest(source.read_bytes()) != expected:
                raise ValueError(f"Homepage artwork mismatch: {source}")
            shutil.copyfile(source, site / target)
            hashes[target] = expected

        previous_html = {}
        for page in PAGES:
            html = pages[page]
            archive = artwork.archive(page)
            (site / archive).write_bytes(html)
            previous_html[page] = hashes[archive] = digest(html)
            pages[page] = replace_hero(html, previous, artwork)

        hero = dict(revision=artwork.revision, status="approved", approval_date=APPROVED, **details,
                    alt=artwork.alt, source_sha256=artwork.source_sha,
                    asset=artwork.full, asset_sha256=artwork.full_sha, width=1672, height=941,
                    small_asset=artwork.small, small_asset_sha256=artwork.small_sha, small_width=960, small_height=540,
                    generated_image=True, measured_reconstruction=False)
        if artwork == V12:
            shutil.copyfile(LAYOUT_SOURCE, site / LAYOUT_ASSET)
            hashes[LAYOUT_ASSET] = LAYOUT_SHA
            hero.update(layout_asset=LAYOUT_ASSET, layout_asset_sha256=LAYOUT_SHA,
                        title_position="below_image", caption_position="below_image")
        approval = dict(version=version, source_commit=info["source_commit"], hero=hero,
                        scope="homepage_visual_only", previous_revision=previous.revision,
                        previous_metadata=previous.metadata, previous_html_sha256=previous_html)
        dump(site / artwork.metadata, approval)
        hashes[artwork.metadata] = digest((site / artwork.metadata).read_bytes())
        info[f"homepage_approved_v{artwork.number}"] = dict(version=version, hero_revision=artwork.revision,
            hero_status="approved", metadata=artwork.metadata, source_commit=info["source_commit"], approval_date=APPROVED)
        release["extensions"] = sorted(set(release["extensions"]) | {version})

    for name, html in pages.items():
        (site / name).write_bytes(html)
        hashes[name] = digest(html)
    release.update(homepage_hero_revision=CURRENT.revision, homepage_hero_status="approved",
                   homepage_hero_approval_date=APPROVED)
    dump(site / "release.json", release)
    hashes["release.json"] = digest((site / "release.json").read_bytes())
    dump(site / "build-info.json", info)


def verify(info, release, get):
    from homepage_yongning_v15 import restore_v14_context
    info, get = restore_v14_context(info, get)
    release = json.loads(get("release.json"))
    hashes = info["files_sha256"]
    pages = {name: get(V10.archive(name)) for name in PAGES}
    for previous, artwork, details in RELEASES:
        approval = json.loads(get(artwork.metadata))
        entry = info[f"homepage_approved_v{artwork.number}"]
        hero = approval["hero"]
        assert approval["version"] == entry["version"] == f"homepage-approved-v{artwork.number}"
        assert approval["source_commit"] == info["source_commit"] == entry["source_commit"]
        assert approval["previous_metadata"] == previous.metadata and approval["previous_revision"] == previous.revision
        assert entry["version"] in release["extensions"] and entry["metadata"] == artwork.metadata
        assert hero["revision"] == entry["hero_revision"] == artwork.revision
        assert hero["status"] == entry["hero_status"] == "approved" and hero["approval_date"] == APPROVED
        assert hero["alt"] == artwork.alt and hero["source_sha256"] == artwork.source_sha
        assert all(hero[key] == value for key, value in details.items())
        assert (hero["width"], hero["height"], hero["small_width"], hero["small_height"]) == (1672, 941, 960, 540)
        assert hero["asset"] == artwork.full and hero["small_asset"] == artwork.small
        assert digest(get(artwork.full)) == hashes[artwork.full] == hero["asset_sha256"] == artwork.full_sha
        assert digest(get(artwork.small)) == hashes[artwork.small] == hero["small_asset_sha256"] == artwork.small_sha
        if artwork == V12:
            assert hero["layout_asset"] == LAYOUT_ASSET
            assert digest(get(LAYOUT_ASSET)) == hashes[LAYOUT_ASSET] == hero["layout_asset_sha256"] == LAYOUT_SHA
            assert hero["title_position"] == hero["caption_position"] == "below_image"

        for page, html in pages.items():
            archive = artwork.archive(page)
            assert html == get(archive) and digest(html) == hashes[archive] == approval["previous_html_sha256"][page]
            pages[page] = replace_hero(html, previous, artwork)
    for name, html in pages.items():
        from city_nodes_r7_contract import KEY as NODES_KEY, restore_home
        from panorama_v13_contract import restore_home as restore_candidate_entry
        from panorama_v13_r2_contract import strip_current_entries
        current = get(name)
        assert digest(current) == hashes[name]
        current = restore_candidate_entry(strip_current_entries(current))
        assert html == (restore_home(current) if NODES_KEY in info else current)
    assert release["homepage_hero_revision"] == CURRENT.revision
    assert release["homepage_hero_status"] == "approved" and release["homepage_hero_approval_date"] == APPROVED
