"""Vector PDF sheets from the exact published shared-coordinate SVG views."""
import io
from pathlib import Path
from xml.etree import ElementTree as ET

import cairosvg
from pypdf import PdfReader, PdfWriter
from city_plan_r11_maps import H, W, text


def build_pdf(path, maps, method, data):
    plates=[(v['title'],maps[v['id']],v['id']) for v in data['views']]
    plates.append(('图例、来源与坐标方法',method,'method'))
    writer=PdfWriter()
    for i,(title,source,vid) in enumerate(plates):
        root=ET.fromstring(source)
        root.set('width','594mm' if vid=='all' else '420mm')
        root.set('height','420mm' if vid=='all' else '297mm')
        text(root,W-67,H-38,f'{i+1:02d} / {len(plates):02d}',14,fill='#69786a',text_anchor='end')
        raw=cairosvg.svg2pdf(bytestring=ET.tostring(root,encoding='utf-8'))
        reader=PdfReader(io.BytesIO(raw))
        assert len(reader.pages)==1
        writer.add_page(reader.pages[0])
        writer.add_outline_item(title,i)
    writer.add_metadata({'/Title':'北魏洛阳 · 全城统一坐标复原工作平面 R11.1',
                         '/Subject':'516–528年综合；来源轮廓、候选接入与完整对象登记；非全城同期实测平面',
                         '/Creator':'luoyang-city / CairoSVG / pypdf',
                         '/Keywords':'R11.1; source_commit='+data['source_commit']})
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('wb') as f:writer.write(f)
    actual=PdfReader(target)
    assert len(actual.pages)==len(plates)
    return {'pages':len(plates),'view_pages':{vid:i for i,(_,_,vid) in enumerate(plates)},
            'formats':['A2-landscape']+['A3-landscape']*(len(plates)-1),'vector_pages':True}
