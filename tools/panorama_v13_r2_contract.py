"""Exact, reversible R9 entries; the approved homepage artwork stays intact."""
from panorama_v13_contract import HOME_ENTRY as HOME_ANCHOR

KEY = 'panorama_review_v13_r2'
VERSION = 'panorama-review-v13-r2'
RESEARCH_VERSION = 'R9.1'
PAGE = 'luoyang-panorama-v13-r2.html'
FOLDER = 'panorama-v13-r2'
MANIFEST = FOLDER + '/manifest.json'
RECORD = FOLDER + '/review.json'
SOURCE_RECORD = 'research/city-spatial-r9/panorama-image-record.json'
HOME_PAGES = ('index.html', 'v3.0-dual.html')
SPATIAL_ENTRY = ('<a id="r9-spatial-entry" href="./luoyang-city-spatial.html">'
                 '城市空间总图 · 判断与图面变化</a>').encode()
PANORAMA_ENTRY = ('<a id="r9-panorama-entry" href="./luoyang-panorama-v13-r2.html">'
                  '审看 V13 二修 · 南门与空间依据</a>').encode()
HOME_ENTRIES = SPATIAL_ENTRY + PANORAMA_ENTRY
CURRENT_MILESTONE = '盛时 R9.1 · 城市空间总图与V13二修候选联读'


def strip_current_entries(content):
    from city_layout_r10_contract import strip_current_entries as strip_r10_entries
    content = strip_r10_entries(content)
    markers = (b'id="r9-spatial-entry"', b'id="r9-panorama-entry"')
    if not any(marker in content for marker in markers):
        return content
    if any(content.count(marker) != 1 for marker in markers):
        raise ValueError('R9 homepage entries must each occur exactly once')
    if content.count(HOME_ENTRIES) != 1 or content.count(HOME_ANCHOR + HOME_ENTRIES) != 1:
        raise ValueError('R9 homepage edits differ from the exact reversible insertion')
    return content.replace(HOME_ENTRIES, b'', 1)


restore_home = strip_current_entries


def add_home(content):
    content = strip_current_entries(content)
    if content.count(HOME_ANCHOR) != 1:
        raise ValueError('R9 requires exactly one existing V13 review entry')
    return content.replace(HOME_ANCHOR, HOME_ANCHOR + HOME_ENTRIES, 1)


def predecessor_reader(info, reader):
    """Read the exact state immediately before the R9 panorama insertion."""
    meta = info.get(KEY)
    if not meta:
        return reader
    def read(path):
        if path == 'release.json':
            return reader(meta['predecessor_release']['path'])
        value = reader(path)
        return strip_current_entries(value) if path in HOME_PAGES else value
    return read
