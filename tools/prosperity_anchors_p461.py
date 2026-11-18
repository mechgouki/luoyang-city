"""Publish the P4.6.1 primary-source readings after the P4.6 inventory."""
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from dual_cartography import dump, load, sha

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/prosperity-v4/anchor-461"
SITE = ROOT / "_site"
OFFICIAL = "https://mechgouki.github.io/luoyang-city/"
PAGE = "prosperity-anchors-p461.html"
PREVIOUS = "prosperity-hydro-roads.html"
BUNDLE = "downloads/anchor-461.zip"
ATLAS = "downloads/anchor-461.pdf"
PLATES = ("trench.svg", "roads.svg", "hongchi.svg", "fig25.svg", "qianqiu.svg")
ARCHIVE = ROOT / "research/prosperity-v4/archive/anchor-461.zip"
ARCHIVE_SHA256 = "e84193d952d8a025bac2c580d8728f801f9e4b88528bfbe98f1c8480ac273f82"
VERSION = "prosperity-anchors-p461"
ENTRY = f'<p id="p461-entry"><a href="./{PAGE}">P4.6.1 · 查看河湖与主干道的原图核读</a></p>\n'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def offline_page(html, asset_dir="anchor-461", atlas=ATLAS):
    """Keep study assets and in-page anchors local; link earlier site pages online."""
    def resolve(match):
        url = match.group(2)
        path = urlsplit(url).path
        if path.removeprefix("./") == atlas:
            return match.group(0)
        if url.startswith(("#", "//")) or urlsplit(url).scheme or path.removeprefix("./").startswith(asset_dir + "/"):
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
    if sha(ARCHIVE) != ARCHIVE_SHA256:
        raise ValueError("The archived P4.6.1 delivery has changed")
    manifest_name = "anchor-461/bundle-manifest.json"
    with zipfile.ZipFile(ARCHIVE) as archive:
        manifest = json.loads(archive.read(manifest_name))
        attachments = manifest["files_sha256"]
        local_html = offline_page(page.read_text(encoding="utf-8")).encode()
        if local_html != archive.read("index.html"):
            raise ValueError("The P4.6.1 study differs from its approved offline edition")
        (site / "downloads").mkdir(exist_ok=True)
        for name in [*attachments, manifest_name]:
            target = site / name
            target.parent.mkdir(parents=True, exist_ok=True)
            data = archive.read(name)
            if name.startswith("anchor-461/") and name != manifest_name:
                if data != (source / Path(name).relative_to("anchor-461")).read_bytes():
                    raise ValueError(f"Archived P4.6.1 source changed: {name}")
            target.write_bytes(data)
    shutil.copyfile(ARCHIVE, site / BUNDLE)

    previous.write_text(html.replace(marker, ENTRY + marker, 1), encoding="utf-8")
    release["extensions"] = sorted(set(release["extensions"]) | {VERSION})
    release["prosperity_anchors_p461_version"] = VERSION
    release["current_milestone"] = "盛时 P4.6.1 · 河湖与主干道原图核读"
    dump(site / "release.json", release)
    info["prosperity_anchors_p461"] = {
        "version": VERSION, "source_commit": manifest["source_commit"], "page": PAGE,
        "bundle": BUNDLE, "manifest": manifest_name, "previous_html_sha256": before_hash,
        "atlas": ATLAS, "atlas_plates": list(PLATES),
    }
    for name in [*attachments, PAGE, PREVIOUS, BUNDLE, manifest_name, "release.json"]:
        checksums[name] = sha(site / name)
    dump(site / "build-info.json", info)


if __name__ == "__main__":
    build()
