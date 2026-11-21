"""Publish the approved autumn 519 panorama after the historical site has been built."""

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY = "homepage_approved_v10"
VERSION = "homepage-approved-v10"
REVISION = "panorama-approved-v10"
PREVIOUS = "panorama-approved-v9"
APPROVED = "2026-11-21"
SOURCE_SHA = "262e0797c09788f7871bca81c05d5e2c15d5ebc7ab8cf6c559ced68cf883a41e"
METADATA = "homepage/approval-v10.json"
PAGES = ("index.html", "v3.0-dual.html")
FULL_SHA = "d8acc2686d3410c418109c60e4ccee9be78263fcce7168c69ab04efc2e7d6c7c"
SMALL_SHA = "5ac9f5a121a0fee2ea9d73741cf3c6b2c651074b860436aa42318680e31f8d4e"
FULL = f"_assets/{FULL_SHA[:20]}-luoyang-{REVISION}.webp"
SMALL = f"_assets/{SMALL_SHA[:20]}-luoyang-{REVISION}-small.webp"
ALT = "北魏神龟二年（519）秋的洛阳复原图。从洛水永桥向北望，御道经景明寺入宣阳门，城内可见永宁寺九层塔与宫城。"
PREVIOUS_ALT = "北魏洛阳盛时艺术复原全景：宫城大殿、礼仪道路、寺院高塔、街巷、市集与远山。建筑外观、古代河道及具体院墙位置包含研究性推定与艺术表现。"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def archive_path(page):
    return "homepage/history/" + page.replace(".html", "-before-v10.html")


def replace_hero(html, *, restore=False):
    fields = (
        ("data-hero-revision", PREVIOUS, REVISION),
        ("src", "./_assets/6465657667ba740d3fc9-luoyang-panorama-approved-v9.webp", "./" + FULL),
        ("srcset", "./_assets/98459529d0a2d8210aaf-luoyang-panorama-approved-v9-small.webp", "./" + SMALL),
        ("alt", PREVIOUS_ALT, ALT),
    )
    for attr, old, new in fields:
        source, target = (new, old) if restore else (old, new)
        old_attr = f'{attr}="{source}"'.encode()
        if html.count(old_attr) != 1:
            raise ValueError(f"Expected one approved homepage {attr}")
        html = html.replace(old_attr, f'{attr}="{target}"'.encode(), 1)
    return html


def publish(site):
    from homepage_v1 import dump

    info = json.loads((site / "build-info.json").read_bytes())
    release = json.loads((site / "release.json").read_bytes())
    hashes = info["files_sha256"]
    for name, target, expected in (
        (f"luoyang-{REVISION}.webp", FULL, FULL_SHA),
        (f"luoyang-{REVISION}-small.webp", SMALL, SMALL_SHA),
    ):
        source = ROOT / "web/assets" / name
        if digest(source.read_bytes()) != expected:
            raise ValueError(f"Approved artwork mismatch: {source}")
        shutil.copyfile(source, site / target)
        hashes[target] = expected

    previous_html = {}
    for name in PAGES:
        page = site / name
        html = page.read_bytes()
        archive = site / archive_path(name)
        if f'data-hero-revision="{REVISION}"'.encode() in html:
            previous = archive.read_bytes()
            if replace_hero(previous) != html:
                raise ValueError(f"Current artwork does not match its predecessor in {name}")
        else:
            previous = html
            html = replace_hero(previous)
            archive.write_bytes(previous)
            page.write_bytes(html)
        previous_html[name] = hashes[archive_path(name)] = digest(previous)
        hashes[name] = digest(html)

    hero = dict(revision=REVISION, status="approved", approval_date=APPROVED,
                season="神龟二年（519）秋", alt=ALT, source_sha256=SOURCE_SHA,
                asset=FULL, asset_sha256=FULL_SHA, width=1672, height=941,
                small_asset=SMALL, small_asset_sha256=SMALL_SHA, small_width=960, small_height=540,
                generated_image=True, measured_reconstruction=False)
    approval = dict(version=VERSION, source_commit=info["source_commit"], hero=hero,
                    scope="homepage_visual_only", previous_revision=PREVIOUS,
                    previous_metadata="homepage/approval-v9.json", previous_html_sha256=previous_html)
    dump(site / METADATA, approval)
    hashes[METADATA] = digest((site / METADATA).read_bytes())
    info[KEY] = dict(version=VERSION, hero_revision=REVISION, hero_status="approved", metadata=METADATA,
                     source_commit=info["source_commit"], approval_date=APPROVED)
    release.update(homepage_hero_revision=REVISION, homepage_hero_status="approved",
                   homepage_hero_approval_date=APPROVED)
    release["extensions"] = sorted(set(release["extensions"]) | {VERSION})
    dump(site / "release.json", release)
    hashes["release.json"] = digest((site / "release.json").read_bytes())
    dump(site / "build-info.json", info)


def verify(info, release, get):
    approval = json.loads(get(METADATA))
    hero = approval["hero"]
    hashes = info["files_sha256"]
    assert approval["version"] == info[KEY]["version"] == VERSION
    assert approval["source_commit"] == info["source_commit"] == info[KEY]["source_commit"]
    assert hero["source_sha256"] == SOURCE_SHA and hero["alt"] == ALT
    assert hero["revision"] == release["homepage_hero_revision"] == info[KEY]["hero_revision"] == REVISION
    assert hero["status"] == release["homepage_hero_status"] == "approved"
    assert hero["approval_date"] == release["homepage_hero_approval_date"] == APPROVED
    assert approval["previous_revision"] == PREVIOUS and VERSION in release["extensions"]
    assert (hero["width"], hero["height"], hero["small_width"], hero["small_height"]) == (1672, 941, 960, 540)
    assert hero["asset"] == FULL and hero["small_asset"] == SMALL
    assert digest(get(FULL)) == hashes[FULL] == hero["asset_sha256"] == FULL_SHA
    assert digest(get(SMALL)) == hashes[SMALL] == hero["small_asset_sha256"] == SMALL_SHA
    for page in PAGES:
        old = get(archive_path(page))
        assert digest(old) == approval["previous_html_sha256"][page] == hashes[archive_path(page)]
        assert get(page) == replace_hero(old) and digest(get(page)) == hashes[page]
