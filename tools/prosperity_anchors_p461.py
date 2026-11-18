"""Publish the P4.6.1 primary-source readings after the P4.6 inventory."""
import hashlib
import re
import shutil
import zipfile
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from dual_cartography import dump, load, sha
from north_b4 import render_atlas

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/prosperity-v4/anchor-461"
SITE = ROOT / "_site"
OFFICIAL = "https://mechgouki.github.io/luoyang-city/"
PAGE = "prosperity-anchors-p461.html"
PREVIOUS = "prosperity-hydro-roads.html"
BUNDLE = "downloads/anchor-461.zip"
ATLAS = "downloads/anchor-461.pdf"
PLATES = ("trench.svg", "roads.svg", "hongchi.svg", "fig25.svg", "qianqiu.svg")
VERSION = "prosperity-anchors-p461"
ENTRY = f'<p id="p461-entry"><a href="./{PAGE}">P4.6.1 · 查看河湖与主干道的原图核读</a></p>\n'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def offline_page(html):
    """Keep study assets and in-page anchors local; link earlier site pages online."""
    def resolve(match):
        url = match.group(2)
        path = urlsplit(url).path
        if path.removeprefix("./") == ATLAS:
            return match.group(0)
        if url.startswith(("#", "//")) or urlsplit(url).scheme or path.startswith(("anchor-461/", "./anchor-461/")):
            return match.group(0)
        return 'href=' + match.group(1) + urljoin(OFFICIAL, url) + match.group(1)
    return re.sub(r'''\bhref=(["'])([^"']+)\1''', resolve, html)


def build(site=SITE, source=SOURCE):
    info = load(site / "build-info.json")
    release = load(site / "release.json")
    checksums = info["files_sha256"]
    previous = site / PREVIOUS
    html = previous.read_text(encoding="utf-8").replace(ENTRY, "")
    marker = '<p class="warning">'
    if html.count(marker) != 1:
        raise ValueError("P4.6 introductory warning changed; review entry placement")
    before_hash = digest(html.encode())
    if before_hash != info.get("prosperity_anchors_p461", {}).get("previous_html_sha256", checksums[PREVIOUS]):
        raise ValueError("P4.6 content differs from the version recorded before this entry")

    page = site / PAGE
    shutil.copyfile(source / "index.html", page)
    attachments = {}
    for path in sorted(source.rglob("*")):
        if path.is_file() and path != source / "index.html":
            name = "anchor-461/" + path.relative_to(source).as_posix()
            target = site / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            attachments[name] = target
    plates = [site / "anchor-461" / name for name in PLATES if (source / name).is_file()]
    if not plates:
        raise ValueError("The study needs at least one source plate for the PDF atlas")
    render_atlas(plates, site / ATLAS)
    attachments[ATLAS] = site / ATLAS
    local_html = offline_page(page.read_text(encoding="utf-8")).encode()
    manifest = {
        "version": VERSION,
        "source_commit": info["source_commit"],
        "files_sha256": {name: sha(path) for name, path in attachments.items()},
        "offline_index_sha256": digest(local_html),
    }
    manifest_name = "anchor-461/bundle-manifest.json"
    dump(site / manifest_name, manifest)
    bundle = site / BUNDLE
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("index.html", local_html)
        archive.write(site / manifest_name, manifest_name)
        for name, path in attachments.items():
            archive.write(path, name)

    previous.write_text(html.replace(marker, ENTRY + marker, 1), encoding="utf-8")
    release["extensions"] = sorted(set(release["extensions"]) | {VERSION})
    release["prosperity_anchors_p461_version"] = VERSION
    release["current_milestone"] = "盛时 P4.6.1 · 河湖与主干道原图核读"
    dump(site / "release.json", release)
    info["prosperity_anchors_p461"] = {
        "version": VERSION, "source_commit": info["source_commit"], "page": PAGE,
        "bundle": BUNDLE, "manifest": manifest_name, "previous_html_sha256": before_hash,
        "atlas": ATLAS, "atlas_plates": [path.name for path in plates],
    }
    for name in [*attachments, PAGE, PREVIOUS, BUNDLE, manifest_name, "release.json"]:
        checksums[name] = sha(site / name)
    dump(site / "build-info.json", info)


if __name__ == "__main__":
    build()
