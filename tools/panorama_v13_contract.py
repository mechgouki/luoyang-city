"""One exact, reversible link to a candidate image; no hero replacement."""

KEY = "panorama_review_v13"
VERSION = "panorama-review-v13"
RESEARCH_VERSION = "R8.1"
PAGE = "luoyang-panorama-v13.html"
FOLDER = "panorama-v13"
MANIFEST = FOLDER + "/manifest.json"
RECORD = FOLDER + "/review.json"
HOME_ANCHOR = ('<a id="r7-research-entry" href="./luoyang-city-nodes.html">'
               '四处城市节点 · 图面与证据联读 ↗</a>').encode()
HOME_ENTRY = ('<a id="r8-panorama-entry" href="./luoyang-panorama-v13.html">'
              '审看 V13 全景校订 · 对照图与依据</a>').encode()


def restore_home(content):
    if b'id="r8-panorama-entry"' not in content:
        return content
    if content.count(HOME_ENTRY) != 1 or content.count(HOME_ANCHOR + HOME_ENTRY) != 1:
        raise ValueError("V13 homepage entry is not the declared reversible insertion")
    return content.replace(HOME_ENTRY, b"", 1)


def add_home(content):
    content = restore_home(content)
    if content.count(HOME_ANCHOR) != 1:
        raise ValueError("V13 requires exactly one existing R7 research entry")
    return content.replace(HOME_ANCHOR, HOME_ANCHOR + HOME_ENTRY, 1)
