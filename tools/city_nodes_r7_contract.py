"""Exact, reversible navigation additions; approved artwork is never rewritten."""

KEY = "city_nodes_r7"
VERSION = "city-nodes-r7.1"
PAGE = "luoyang-city-nodes.html"
FOLDER = "city-nodes"
MANIFEST = FOLDER + "/manifest.json"
BUNDLE = "downloads/luoyang-city-nodes.zip"
BASE = "https://mechgouki.github.io/luoyang-city/"

HOME_EDITS = tuple((a.encode(), b.encode()) for a, b in (
    ("北魏洛阳 · 研究性复原示意 · 全幅取景版</figcaption>",
     '北魏洛阳 · 研究性复原示意 · 全幅取景版　<a id="r7-home-guide" href="./luoyang-city-nodes.html#panorama">查看画面依据 →</a></figcaption>'),
    ("当前公开版本 · 双图 B1+B2 / 文献图继续深化",
     "盛时洛阳 · 文献关系地图 / 516—528年"),
    ('<a href="./luoyang-water-atlas.html">查看河流与水系定位 ↗</a>',
     '<a href="./luoyang-water-atlas.html">查看河流与水系定位 ↗</a>'
     '<a id="r7-research-entry" href="./luoyang-city-nodes.html">四处城市节点 · 图面与证据联读 ↗</a>'),
))
ROAD_ENTRY = ('<p id="r7-road-entry" class="wrap"><a href="./luoyang-city-nodes.html">'
              '四处关键城市节点：把道路、城门、水系与年代一起读 →</a></p>').encode()


def restore_home(content):
    if b'id="r7-home-guide"' not in content:
        return content
    for before, after in reversed(HOME_EDITS):
        if content.count(after) != 1:
            raise ValueError("R7 homepage changes are not exactly reversible")
        content = content.replace(after, before, 1)
    return content


def add_home(content):
    content = restore_home(content)
    for before, after in HOME_EDITS:
        if content.count(before) != 1:
            raise ValueError("Review the R7 homepage insertion point")
        content = content.replace(before, after, 1)
    return content
