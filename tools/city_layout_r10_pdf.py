"""A3 PDF edition of the R10 SVG atlas, using the existing Cairo/pypdf stack."""
import io
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import cairosvg
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Link

from city_layout_r10_maps import H, NS, W, build_legend, el, text


def _page_svg(source, page_number, page_count, source_commit, y_offset=0):
    root = ET.fromstring(source)
    # Remove whole off-sheet panels and publication text before conversion.
    # Relying on a viewport clip alone can leave invisible text extractable
    # from the other sheet, even though the printed page looks correct.
    if int(root.get("data-pdf-pages", "1")) > 1:
        for child in list(root):
            raw_box = child.get("data-panel-bounds") or child.get("data-link-box")
            if raw_box:
                _, yy, _, hh = json.loads(raw_box)
                if yy + hh <= y_offset or yy >= y_offset + H:
                    root.remove(child)
            elif child.tag == "{" + NS + "}text":
                yy = float(child.get("y", "0"))
                if yy < y_offset or yy > y_offset + H:
                    root.remove(child)
    root.set("width", "420mm")
    root.set("height", "297mm")
    root.set("viewBox", f"0 {y_offset} {W} {H}")
    # A small publication footer is separate from all historical geometry.
    text(root, W - 190, y_offset + H - 23, f"{page_number:02} / {page_count:02}", 16,
         fill="#687571", text_anchor="end")
    el(root, "metadata", data_role="pdf-publication").text = json.dumps(
        {"source_commit": source_commit, "page_number": page_number, "page_count": page_count, "svg_y_offset": y_offset},
        ensure_ascii=False, separators=(",", ":"))
    return root, ET.tostring(root, encoding="utf-8")


def _links(writer, page_index, svg_root, region_pages, y_offset=0):
    page = writer.pages[page_index]
    pw, ph = float(page.mediabox.width), float(page.mediabox.height)
    for anchor in svg_root.iter("{" + NS + "}a"):
        raw = anchor.get("data-link-box")
        if not raw:
            continue
        x, y, width, height = json.loads(raw)
        if y + height <= y_offset or y >= y_offset + H:
            continue
        if y < y_offset - .01 or y + height > y_offset + H + .01:
            raise ValueError("A PDF link would straddle a page boundary")
        y -= y_offset
        rect = (x / W * pw, ph - (y + height) / H * ph, (x + width) / W * pw, ph - y / H * ph)
        region = anchor.get("data-region-link")
        if region in region_pages:
            link = Link(rect=rect, target_page_index=region_pages[region])
        else:
            href = anchor.get("href")
            if not href or not href.startswith("https://"):
                continue
            link = Link(rect=rect, url=href)
        writer.add_annotation(page_number=page_index, annotation=link)


def build_pdf(output_path, overview_svg, region_svgs, data):
    """Write overview + eleven regions + evidence legend as A3 print sheets.

    The fuller regions declare two consecutive sheets in their SVG metadata. Their SVGs stay intact;
    the PDF viewport selects each full-height sheet without changing geometry.

    This function never redraws or rasterizes source geometry. Cairo embeds
    text/vector content; pypdf joins pages and adds explicit navigational links.
    The caller owns final output indexing, hashes and release metadata.
    """
    regions = data["regions"]
    identifiers = [r["id"] for r in regions]
    expected = [f"R{i:02}" for i in range(1, 12)]
    if identifiers != expected or set(region_svgs) != set(expected):
        raise ValueError("R10 PDF requires exactly R01 through R11 in reading order")
    plates = [("全城来源骨架与分区索引", overview_svg, 0)]
    region_pages = {}
    for region in regions:
        identifier = region["id"]
        source = region_svgs[identifier]
        root = ET.fromstring(source)
        count = int(root.get("data-pdf-pages", "1"))
        if count not in {1, 2} or root.get("viewBox") != f"0 0 {W} {H * count}":
            raise ValueError("Region SVG page segmentation does not match its declared canvas")
        region_pages[identifier] = len(plates)
        for part in range(count):
            suffix = ("〔上〕" if part == 0 else "〔下〕") if count == 2 else ""
            plates.append((identifier + " " + region["title"] + suffix, source, part * H))
    plates.append(("图例、证据与未定边界", build_legend(data), 0))
    writer = PdfWriter()
    roots = []
    for i, (_, source, offset) in enumerate(plates, 1):
        root, svg_bytes = _page_svg(source, i, len(plates), data["source_commit"], offset)
        converted = cairosvg.svg2pdf(bytestring=svg_bytes)
        reader = PdfReader(io.BytesIO(converted))
        if len(reader.pages) != 1:
            raise ValueError("Each R10 SVG viewport must yield exactly one PDF page")
        writer.add_page(reader.pages[0])
        roots.append(root)
    for i, (title, _, offset) in enumerate(plates):
        writer.add_outline_item(title, i)
        _links(writer, i, roots[i], region_pages, offset)
    writer.add_metadata({
        "/Title": "盛时洛阳城市布局图集 R10.1",
        "/Subject": "来源骨架、十一片区关系图、证据与未定边界；非完整同期实测城市平面",
        "/Creator": "luoyang-city / CairoSVG and pypdf",
        "/Keywords": "R10.1; 516-528; source_commit=" + data["source_commit"],
    })
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as stream:
        writer.write(stream)
    check = PdfReader(destination)
    if len(check.pages) != len(plates):
        raise ValueError("R10 PDF page count changed")
    for page in check.pages:
        if abs(float(page.mediabox.width) - 420 / 25.4 * 72) > .2 or abs(float(page.mediabox.height) - 297 / 25.4 * 72) > .2:
            raise ValueError("R10 PDF must retain landscape A3 media size")
    return {"pages": len(check.pages), "format": "A3-landscape", "region_pages": region_pages,
            "source_commit": data["source_commit"], "vector_pages": True,
            "page_regions": [next((rid for rid in expected if title.startswith(rid + " ")), "overview" if i == 0 else "legend")
                             for i, (title, _, _) in enumerate(plates)]}
