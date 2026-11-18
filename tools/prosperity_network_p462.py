"""Publish P4.6.2 with one reversible entry on the previous reading page."""
import json
import shutil
from pathlib import Path
import zipfile

from dual_cartography import dump, load, sha
from prosperity_anchors_p461 import PAGE as PREVIOUS
from prosperity_anchors_p461 import ROOT, SITE, digest, offline_page

SOURCE = ROOT / "research/prosperity-v4/network-462"
VERSION = "prosperity-network-p462"
PAGE = "prosperity-network-p462.html"
ATLAS = "downloads/network-462.pdf"
BUNDLE = "downloads/network-462.zip"
MANIFEST = "network-462/bundle-manifest.json"
ENTRY = f'<p id="p462-entry"><a href="./{PAGE}">P4.6.2 · 查看水道、河流与街道复原图</a></p>\n'
PLATE_ORDER = ("network.svg", "roads.svg", "waters.svg", "east.svg", "outer.svg", "crossings.svg")


def build(site=SITE, source=SOURCE):
    info = load(site / "build-info.json")
    release = load(site / "release.json")
    checksums = info["files_sha256"]
    previous = site / PREVIOUS
    html = previous.read_text(encoding="utf-8")
    if html.count(ENTRY) > 1:
        raise ValueError("Duplicate P4.6.2 entry on the P4.6.1 page")
    html = html.replace(ENTRY, "")
    old_sha = digest(html.encode())
    expected = info.get("prosperity_network_p462", {}).get("previous_html_sha256", checksums[PREVIOUS])
    marker = '<p class="meta">北魏洛阳 · 盛时城市骨架 · P4.6.1</p>'
    if old_sha != expected or html.count(marker) != 1:
        raise ValueError("P4.6.1 page differs from its recorded source")

    page = site / PAGE
    template = (source / "index.html").read_text(encoding="utf-8")
    svg = (source / "network.svg").read_text(encoding="utf-8")
    if template.count("<!-- NETWORK_SVG -->") != 1 or "<svg" not in svg or "</svg>" not in svg:
        raise ValueError("P4.6.2 page requires a single marker and a complete network figure")
    figure = svg[svg.index("<svg"):svg.rindex("</svg>") + len("</svg>")]
    page.write_text(template.replace("<!-- NETWORK_SVG -->", figure), encoding="utf-8")
    archived = ROOT / "research/prosperity-v4/archive/network-462.zip"
    if sha(archived) != "1f11c20b3b6417eb1818771dc58b4493c3e93d34ad40cfd8f86ae9147116f1eb":
        raise ValueError("P4.6.2 archive differs from the accepted release")
    with zipfile.ZipFile(archived) as archive:
        manifest = json.loads(archive.read(MANIFEST))
        attachments = manifest["files_sha256"]
        if offline_page(page.read_text(), "network-462", ATLAS).encode() != archive.read("index.html"):
            raise ValueError("P4.6.2 article differs from its accepted offline edition")
        for name in [*attachments, MANIFEST]:
            target = site / name
            data = archive.read(name)
            if name.startswith("network-462/") and name != MANIFEST:
                if data != (source / Path(name).relative_to("network-462")).read_bytes():
                    raise ValueError(f"Archived P4.6.2 source changed: {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    shutil.copyfile(archived, site / BUNDLE)

    previous.write_text(html.replace(marker, ENTRY + marker, 1), encoding="utf-8")
    release["extensions"] = sorted(set(release["extensions"]) | {VERSION})
    release["prosperity_network_p462_version"] = VERSION
    release["current_milestone"] = "盛时 P4.6.2 · 水道、河流与街道复原图"
    dump(site / "release.json", release)
    info["prosperity_network_p462"] = {
        "version": VERSION, "source_commit": manifest["source_commit"], "page": PAGE,
        "bundle": BUNDLE, "atlas": ATLAS, "atlas_plates": list(PLATE_ORDER),
        "manifest": MANIFEST, "previous_html_sha256": old_sha,
    }
    for name in [*attachments, MANIFEST, BUNDLE, PAGE, PREVIOUS, "release.json"]:
        checksums[name] = sha(site / name)
    dump(site / "build-info.json", info)


if __name__ == "__main__":
    build()
