"""Compare the excavation team's location map with R4 using a held-out landmark."""
from html import escape
from math import dist
from textwrap import dedent


def compare(readings, features):
    by_id = {f["id"]: f for f in features}
    landmarks = []
    for item in readings["landmarks"]:
        geom = by_id[item["r4_feature"]]["source_pdf_geometry"]
        assert geom["type"] == "Point"
        landmarks.append(dict(item, r4_pdf_point=geom["coordinates"]))
    a, b = [item for item in landmarks if item["role"] == "fit"]
    check, = [item for item in landmarks if item["role"] == "check"]
    source_a, source_b = (complex(*i["r4_pdf_point"]) for i in (a, b))
    dest_a, dest_b = (complex(*i["pixel"]) for i in (a, b))
    factor = (dest_b - dest_a) / (source_b - source_a)
    prediction = dest_a + factor * (complex(*check["r4_pdf_point"]) - source_a)
    observed = complex(*check["pixel"])
    img = readings["image"]
    tick = img["scale_ticks_px"]
    m_per_px = (img["scale_ticks_m"][-1] - img["scale_ticks_m"][0]) / dist(tick[0], tick[-1])
    x0, y0, x1, y1 = img["storage_box_centerline_px"]
    return dict(readings, landmarks=landmarks, diagnostic={
        "predicted_px": [round(prediction.real, 3), round(prediction.imag, 3)],
        "offset_px": round(abs(prediction - observed), 3),
        "map_equivalent_m": round(abs(prediction - observed) * m_per_px, 2),
        "box_graphic_size_m": [round((x1-x0)*m_per_px), round((y1-y0)*m_per_px)],
        "units": "米数仅按2023位置示意图比例尺换读。现场误差与墙线精度未定。"
    })


def plate(survey):
    points = survey["landmarks"]
    result = survey["diagnostic"]
    px, py = result["predicted_px"]
    actual, = [p for p in points if p["role"] == "check"]
    ax, ay = actual["pixel"]
    x0, y0, x1, y1 = survey["image"]["storage_box_centerline_px"]
    ink = survey["image"]["sima_road_ink_px"]
    traces = "".join(f'<path d="M{x} {y}L{u} {v}"/>' for ((x,y),(u,v)) in ink)
    gx, gy = survey["image"]["gate_label_px"]
    marks = []
    for p in points:
        x, y = p["pixel"]
        label_x, anchor = (x-17, "end") if p["r4_feature"] == "geo-changhe-palace-gate" else (x+17, "start")
        marks.append(f'<circle cx="{x}" cy="{y}" r="8" fill="#305f54"/><text x="{label_x}" y="{y+9}" text-anchor="{anchor}" font-size="33">{escape(p["label"])}</text>')
    return dedent(f'''\
    <svg xmlns="http://www.w3.org/2000/svg" width="1000" height="720" viewBox="0 0 1000 720" role="img" aria-labelledby="s-title s-desc">
      <title id="s-title">司马门内道路与两侧墙线</title>
      <desc id="s-desc">左图按考古队位置图摘绘三处图符、司马门内路局部双线和仓区范围；右图放大太极殿检验点，空心为R4两门推算位置，实心为位置图读点。</desc>
      <style>text{{font-family:"Noto Sans CJK SC","PingFang SC",sans-serif;fill:#243e34}}.main{{font-family:"Noto Serif CJK SC",serif;font-size:39px;font-weight:bold}}.section{{font-size:23px;font-weight:bold}}.note{{font-size:17px}}.small{{font-size:15px;fill:#506458}}</style>
      <rect width="1000" height="720" fill="#f9f6ed"/>
      <path d="M44 39h54" stroke="#995533" stroke-width="5"/><text x="112" y="45" class="small">北魏洛阳　/　宫城道路考古</text>
      <text x="44" y="103" class="main">司马门内道路与两侧墙线</text>
      <text x="45" y="139" class="note">太极殿宫院东墙以东为司马门内道路，再向东为宫内仓窖区西墙。</text>
      <path d="M44 163h912" stroke="#b5bbaa"/>
      <text x="44" y="206" class="section">宫城位置图</text><text x="533" y="206" class="section">太极殿独立复核</text>
      <rect x="44" y="225" width="460" height="360" fill="#e9eee4"/>
      <svg x="64" y="238" width="415" height="330" viewBox="190 665 790 822">
        <rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#f5ead7" stroke="#9f7149" stroke-width="5" stroke-dasharray="13 8"/>
        <text x="{(x0+x1)/2}" y="1021" font-size="29" text-anchor="middle">宫城</text>
        <text x="{(x0+x1)/2}" y="1061" font-size="29" text-anchor="middle">仓窖区</text>
        <g stroke="#656b5f" stroke-width="3" fill="none">{traces}</g>
        <text x="{gx+21}" y="{gy-4}" font-size="29">司马门</text>
        {''.join(marks)}
        <circle cx="{px}" cy="{py}" r="10" fill="none" stroke="#a84d34" stroke-width="4"/>
        <path d="M225 1465h176m-176 -10v10 m88 -10v10 m88 -10v10" stroke="#40584d" stroke-width="3" fill="none"/>
        <text x="225" y="1444" font-size="22">0</text><text x="348" y="1444" font-size="22">200 米</text>
      </svg>
      <rect x="530" y="225" width="426" height="232" fill="#f0ede2"/>
      <g transform="translate(624 395) scale(3.2)">
        <line x1="0" y1="0" x2="{px-ax:.3f}" y2="{py-ay:.3f}" stroke="#97654b" stroke-dasharray="3 2"/>
        <circle r="3.3" fill="#305f54"/><circle cx="{px-ax:.3f}" cy="{py-ay:.3f}" r="3.7" fill="none" stroke="#a84d34" stroke-width="1.1"/>
      </g>
      <text x="689" y="280" class="note">用两座宫门推算的殿址</text>
      <text x="689" y="402" class="note">位置图上的殿址图符</text>
      <text x="533" y="497" class="section">相差 {result["offset_px"]:.1f} 像素</text>
      <text x="533" y="531" class="note">按原图比例尺折约 {result["map_equivalent_m"]:.0f} 米。</text>
      <text x="533" y="560" class="small">此值只描述两幅图的差异。</text>
      <text x="45" y="617" class="small">位置图摘读　细双线为原图道路线，虚框为仓区范围标示。右图单独放大。</text>
      <path d="M44 641h912" stroke="#b5bbaa"/>
      <text x="45" y="676" class="note">2024年发掘确认两墙与道路的次序，北魏路面最宽处约40米。</text>
      <text x="45" y="703" class="small">要在全城总图上落线，仍需同一北魏测线上两侧墙缘、路面边缘和可复认的测点。</text>
    </svg>
    ''')
