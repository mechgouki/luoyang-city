#!/usr/bin/env python3
"""Build a quotation / literal-reference ledger without changing historical data.

The source cache is intentionally external to the repository: it contains whole
modern editions. Only hashes, locators and necessary ancient excerpts are saved.
An exact text match is a transcription check, never a coordinate or identity proof.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unicodedata

from city_audit_b8 import EVIDENCE_INPUTS, EXTERNAL_REFERENCES

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'research/prosperity-v1/text-review.json'
VERSION = 'prosperity-text-review-v1'
REVIEW_DATE = '2026-11-14'
OTHER_SOURCES = {
    'H': ('https://zh.wikisource.org/wiki/河南志', '《河南志》后魏城阙古迹电子转录', 'H'),
    'W': ('https://zh.wikisource.org/wiki/水經注集釋訂訛_(四庫全書本)/卷16', '《水经注集释订讹》卷十六所载经注', 'W'),
    'W16': ('https://zh.wikisource.org/wiki/水經注_(四部叢刊本)/卷第十六', '《水经注》四部丛刊本卷十六电子转录', 'W'),
    'L3S': ('https://zh.wikisource.org/wiki/洛陽伽藍記_(四部叢刊本)/卷三', '《洛阳伽蓝记》四部丛刊本卷三电子转录', 'L'),
    'LF': ('https://dlbs.liberal.ntu.edu.tw/FULLTEXT/sutra/B/B0078.pdf', '范祥雍校注 CBETA 电子重排 PDF', 'L'),
}


def normalize(text):
    """Remove layout punctuation only; do not silently unify Chinese readings."""
    text = unicodedata.normalize('NFKC', text.replace('【校】', ''))
    return ''.join(c for c in text if not unicodedata.category(c).startswith(('P', 'Z', 'C')))


class CbetaReader(HTMLParser):
    """The site's small.inline-note is modern commentary, not ancient 子注."""
    def __init__(self):
        super().__init__()
        self.stack, self.active, self.units = [], [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.stack.append((tag, attrs))
        if tag == 'span' and 't' in attrs.get('class', '').split():
            self.active.append({
                'depth': len(self.stack), 'line': attrs.get('l'), 'text': '',
                'note': any(t == 'small' and 'inline-note' in a.get('class', '').split()
                            for t, a in self.stack),
            })

    def handle_endtag(self, tag):
        ix = next((i for i in range(len(self.stack) - 1, -1, -1)
                   if self.stack[i][0] == tag), None)
        if ix is None:
            return
        for unit in self.active[:]:
            if unit['depth'] > ix:
                self.units.append({k: unit[k] for k in ('line', 'note', 'text')})
                self.active.remove(unit)
        self.stack = self.stack[:ix]

    def handle_data(self, data):
        for unit in self.active:
            unit['text'] += data


class WikiReader(HTMLParser):
    """Separate edition notes in W/W16; retain 河南志's own small-text entries."""
    def __init__(self, drop_small=False):
        super().__init__()
        self.stack, self.parts = [], []
        self.drop_small = drop_small

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get('class', '').split()
        active = (self.stack[-1][1] if self.stack else False) or 'mw-parser-output' in classes
        skip = ((self.stack[-1][2] if self.stack else False)
                or tag in ('script', 'style') or (self.drop_small and tag == 'small')
                or attrs.get('id') == 'headerContainer' or 'ws-header' in classes)
        if tag not in ('br', 'hr', 'img', 'meta', 'link', 'input', 'wbr'):
            self.stack.append((tag, active, skip))

    def handle_endtag(self, tag):
        for ix in range(len(self.stack) - 1, -1, -1):
            if self.stack[ix][0] == tag:
                self.stack = self.stack[:ix]
                break

    def handle_data(self, data):
        if self.stack and self.stack[-1][1] and not self.stack[-1][2]:
            self.parts.append(data)


def stream(units, note=False):
    text, locators = '', []
    for unit in units:
        if unit['note'] != note:
            continue
        fragment = normalize(unit['text'])
        text += fragment
        locators.extend([unit['line']] * len(fragment))
    return text, locators


def sequence_match(quote, text, locators=None):
    """Each explicitly marked excerpt must occur in order, with no fuzzy edits."""
    parts = [normalize(x) for x in re.split(r'[…⋯]+', quote) if normalize(x)]
    at, hits = 0, []
    for part in parts:
        pos = text.find(part, at)
        if pos < 0:
            return None
        hit = {'normalized_offset': pos, 'normalized_length': len(part),
               'excerpt_start': part[:18]}
        if locators:
            hit.update(line_start=locators[pos], line_end=locators[pos + len(part) - 1])
        hits.append(hit)
        at = pos + len(part)
    return hits or None


def source_key(url):
    m = re.search(r'(B007[78])/(\d)', url)
    if m:
        return m[1] + '-' + m[2]
    for key, (address, _, _) in OTHER_SOURCES.items():
        if url.split('#')[0] == address:
            return key
    return None


def load_sources(cache):
    sources, snapshots = {}, []
    for book in ('B0077', 'B0078'):
        for juan in range(1, 6):
            key = f'{book}-{juan}'
            path = cache / (key + '.html')
            raw = path.read_bytes()
            parser = CbetaReader()
            parser.feed(raw.decode('utf-8'))
            body, body_loc = stream(parser.units)
            note, note_loc = stream(parser.units, True)
            url = f'https://deerpark.app/cbeta/{book}/{juan}'
            sources[key] = {'body': body, 'body_loc': body_loc, 'note': note,
                            'note_loc': note_loc, 'units': parser.units, 'url': url}
            snapshots.append({
                'key': key, 'url': url, 'retrieved_at': REVIEW_DATE,
                'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
                'family': 'L', 'edition': '周祖谟校释' if book == 'B0077' else '范祥雍校注',
                'volume': juan, 'access': 'downloaded_html_and_parsed_text',
                'text_layer_rule': '古籍正文及古书子注保留；small.inline-note现代夹注单列。非夹注流也含前言，匹配位置须结合篇章定位。',
                'manuscript_or_print_scan_checked': False,
            })
    for key, (url, title, family) in OTHER_SOURCES.items():
        path = cache / (key + ('.pdf' if key == 'LF' else '.html'))
        raw = path.read_bytes()
        if key == 'LF':
            raw_text = (cache / 'LF.txt').read_text()
            pages = raw_text.split('\f')
            text, loc = '', []
            for page, value in enumerate(pages, 1):
                value = normalize(value)
                text += value
                loc.extend([f'PDF-file-page-{page};printed-page-{page - 1}' if page > 1 else 'PDF-cover'] * len(value))
            rule = 'pdftotext电子文字含混排校注；只用于页定位，N11另按同版HTML正文分层复核。'
        else:
            parser = WikiReader(drop_small=key in ('W', 'W16'))
            parser.feed(raw.decode('utf-8'))
            text, loc = normalize(''.join(parser.parts)), None
            rule = ('剥离small中的后出集释或校按，保留所载经注正文。' if key in ('W', 'W16')
                    else '河南志自身条目小字保留，限定后魏城阙古迹；不把后出汇编当北魏目击。' if key == 'H'
                    else '电子转录正文；未逐叶核书影。')
        sources[key] = {'body': text, 'body_loc': loc, 'note': '', 'note_loc': None, 'url': url}
        snapshots.append({'key': key, 'url': url, 'title': title, 'family': family,
                          'retrieved_at': REVIEW_DATE, 'sha256': hashlib.sha256(raw).hexdigest(),
                          'bytes': len(raw), 'access': 'downloaded_pdf_text' if key == 'LF' else 'downloaded_html_and_parsed_text',
                          'text_layer_rule': rule, 'manuscript_or_print_scan_checked': False})
    return sources, snapshots


def quote_sources(record):
    if record.get('quote_source'):
        return [record['quote_source']]
    if record.get('source'):
        return [record['source']]
    return record.get('source_ids', record.get('sources', []))


MANUAL_EXCEPTIONS = {
    'v2.5:E06': {
        'kind': 'unmarked_character_normalization', 'finding': '河南志电子本作淩陰里；旧引写凌陰里。字形须记录，不改实体或南北链。',
        'corrected_quote': '太府寺。〈右衛府南。〉將作曹。〈太府寺南。〉太社。〈將作曹南。〉司州。〈太社南。〉淩陰里。〈司州南，四朝藏冰處。〉',
        'source_keys': ['H'], 'locator': '後魏城闕古蹟·城内官署条目·右衛府至淩陰里',
        'new_historical_discovery': False,
    },
    'v2.5:E10': {
        'kind': 'unmarked_character_normalization', 'finding': '所列四库转录作𣲖、于；旧引规范为派、於，未显式说明；不由字形差异重画渠线。',
        'corrected_quote': '門左枝渠東𣲖入城，逕太社前，又東逕太廟南，又東于清陽門右下注陽渠。',
        'source_keys': ['W'], 'locator': '卷十六·穀水·西明门条门左枝渠段',
        'new_historical_discovery': False,
    },
    'v2.7:N02': {
        'kind': 'unmarked_omission', 'finding': '晉太康元年造与橋北大道之间尚有桥南马市等文；旧引缺省略号，不能造成紧邻错觉。',
        'corrected_quote': '出建春門外一里餘，至東石橋。南北而行，晉太康元年造。……橋北大道西有建陽里，大道東有綏民里。',
        'source_keys': ['B0077-2'], 'locator': '卷二·景兴尼寺前东石桥段',
        'new_historical_discovery': False,
    },
    'v2.7:N03': {
        'kind': 'unmarked_omission', 'finding': '两句之间有寺南有租塲，需明示节录；不能删文后让读者以为是连续两句。',
        'corrected_quote': '在建春門外陽渠南。……陽渠北有建陽里。',
        'source_keys': ['B0077-2'], 'locator': '卷二·明悬尼寺开头',
        'new_historical_discovery': False,
    },
    'v2.7:N11': {
        'kind': 'pdf_body_crosscheck', 'finding': '电子PDF正文与夹校在抽取流中混排；印刷页码100（PDF文件第101页）上下文确认，并按同一范本卷四HTML剥离夹注核到正文，不把PDF抽取断裂当引文错误。',
        'corrected_quote': '中朝時以穀水浚急，注於城下，多壞民家，立石橋以限之，長則分流入洛……長分橋西，有千金堰。',
        'source_keys': ['B0078-4'], 'locator': '范卷四长分桥段；电子PDF页内码100，文件计数第101页',
        'new_historical_discovery': False,
    },
    'v2.7:N14': {
        'kind': 'unmarked_omission_and_adopted_reading', 'finding': '旧引把至移到四月七日前，略掉录像段而未标删节，并采用八日校读；使用已在B7:LR05正确列出的周本节录。',
        'corrected_quote': '四月七日京師諸像皆來此寺，……至八日，以次入宣陽門，向閶闔宮前受皇帝散花。',
        'source_keys': ['B0077-3'], 'locator': '卷三·景明寺行像段；采用B7:LR05所用周本，不伪称旧范引逐字无误',
        'new_historical_discovery': False, 'prior_correct_reading': 'B7:LR05',
    },
    'v2.7:N19': {
        'kind': 'adopted_edition_correction', 'finding': '范电子正文显示㯋（鄴）；旧引采用鄴这一校正读法。史事无新增，需显示版本取舍。',
        'corrected_quote': '武定四年，大將軍遷石經於㯋（鄴）。',
        'source_keys': ['B0078-3'], 'locator': 'B12n0078_p0486a05·石经迁邺段',
        'new_historical_discovery': False,
    },
    'B2:G13': {
        'kind': 'substantive_quotation_error_and_paraphrase',
        'finding': '三项不同性质问题：園中有柰林为篇章归属概括而非逐字句；都堂在柰林西，旧引误成碑西；扶桑为海，旧引误成殿。既有实体名录和约束已正确，新工作层修正旧证据卡，不新增实体。',
        'corrected_quote': '柰林南有石碑一所，……高祖於碑北作苗茨堂。……柰林西有都堂，有流觴池。堂東有扶桑海。',
        'source_keys': ['B0077-1', 'B0078-1'],
        'locator': '周B12n0077_p0094a12–14、p0095a11–12；范B12n0078_p0406a11–12、p0407a02',
        'new_historical_discovery': False, 'new_project_error_found': True,
    },
    'B2:G15': {
        'kind': 'inherited_b8_paraphrase_correction', 'finding': 'B8:CB14已判定旧引为压缩概述。本轮重新对电子正文相合，只继承既有更正，不算本阶段新发现。',
        'corrected_quote': '若旱魃為害，穀水注之不竭；離畢滂潤，陽穀泄之不盈。',
        'source_keys': ['B0077-1', 'B0078-1'], 'locator': '周p0095a14–p0096a01；范p0407a03–04',
        'new_historical_discovery': False, 'prior_correction': 'B8:CB14',
    },
    'B2:G16': {
        'kind': 'unmarked_character_normalization', 'finding': '周本作入寺婬穢，旧引转写淫穢；范p0387a03–04还保留入瑤光寺婬穢。字形及删名须说明，侵扰没有提供寺毁明文。',
        'corrected_quote': '永安三年……入寺婬穢。',
        'source_keys': ['B0077-1'], 'locator': 'B12n0077_p0082a04–06·瑶光条',
        'new_historical_discovery': False,
    },
    'B4:NG15': {
        'kind': 'modern_annotation_mixed_into_ancient_quote',
        'finding': '城之西北門也处于周本small.inline-note；有字上疑有脫文亦为周注。旧引把第一条夹注接入古籍正文。古文仍支持瑶光寺北承明门，金墉接句不补空间距离。',
        'corrected_quote': '瑤光寺北有承明門，有金墉城，即魏氏所築。',
        'source_keys': ['B0077-1', 'B0078-1'],
        'locator': '周B12n0077_p0082a09；范B12n0078_p0387a06',
        'editorial_note': {'author': '周祖谟', 'layer': '现代夹注', 'quote': '城之西北門也。',
                           'second_note': '有字上疑有脫文。', 'source_key': 'B0077-1', 'line': '0082a09'},
        'new_historical_discovery': False, 'new_project_error_found': True,
    },
}


EDITION_COMPARISONS = {
    ('v2.5:E04', 'B0077-1'): ('周本补學；本条旧引采用范本国子南，不能当两本无差别同文。', '國子學南有宗正寺，寺南有太廟，廟南有護軍府，府南有衣冠里。'),
    ('v2.5:E18', 'H'): ('河南志是太社—司州—淩陰里条目链，非逐字社南有凌陰里；层级和异名不可压平。', '太社。〈將作曹南。〉司州。〈太社南。〉淩陰里。〈司州南，四朝藏冰處。〉'),
    ('B2:G07', 'B0077-1'): ('周本显式补魏字；旧引采用无补字的范本字面。', '池中猶有〔魏〕文帝九華臺。高祖於臺上造清涼殿。'),
    ('B3:W05', 'B0077-4'): ('周本正文用延酤，范本用退酤；属于既有版本读法差别，不新增第二里。', '市西有延酤、治觴二里，里內之人多醞酒為業。'),
    ('B3:W06', 'B0077-4'): ('周本正文补有字；旧引采用范本未补字句。', '市北〔有〕慈孝、奉終二里，里內之人以賣棺槨為業，賃輀車為事。'),
    ('B3:W07', 'B0078-4'): ('范本电子正文作準財，周本作阜財；名称取舍与既有校注条件保留。', '別有準財、金肆二里，富人在焉。凡此十里，多諸工商貨殖之民。'),
    ('B3:W08', 'B0078-4'): ('范本电子正文作準財里；旧引在周本可定位，不应把两版本相合说成逐字无异。', '準財里內有開善寺，京兆人韋英宅也。……梁氏惶懼，捨宅為寺。'),
    ('B3:W12', 'B0078-4'): ('范本显示中（東）、釗（剛）的校正标记；台东侯刚采用校正读法，不是无条件的原传字面。', '臺中（東）有侍中侯釗（剛）宅。'),
    ('B3:W14', 'B0078-4'): ('范本作退酤，周本作延酤；寿丘界域仍为原里距与范围句，不据此生成现代矩形。', '自退酤以西，張方溝以東，南臨洛水，北達芒山，其間東西二里，南北十五里，並名為壽丘里。'),
    ('B3:W15', 'B0077-4'): ('周本文栢、范本文柏字形不同；两本都不是堂平面或尺度图。', '造文栢堂，形如徽音殿。……造迎風館於後園。'),
}


SOURCE_CONTEXTS = {
    'B2:G13': [
        {'source_key': 'B0077-1', 'layer': '古籍正文', 'locator': '0094a05–06',
         'quote': '景陽山南，有百果園。果別作林，林各有堂。'},
        {'source_key': 'B0077-1', 'layer': '古籍正文', 'locator': '0094a12–14',
         'quote': '柰林南有石碑一所，魏明帝所立也。題云「苗茨之碑」。高祖於碑北作苗茨堂。'},
        {'source_key': 'B0077-1', 'layer': '古籍正文', 'locator': '0095a11–14',
         'quote': '柰林西有都堂，有流觴池。堂東有扶桑海。凡此諸海，皆有石竇流於地下，西通穀水，東連陽渠，亦與翟泉相連。'},
        {'source_key': 'B0078-1', 'layer': '古籍正文', 'locator': '0406a07',
         'quote': '景陽山南有百果園，果列作林，林各有堂。'},
        {'source_key': 'B0078-1', 'layer': '古籍正文', 'locator': '0406a11–12',
         'quote': '柰林南有石碑一所，魏明帝所立也，題云「苗茨之碑。」高祖於碑北作苗茨堂。'},
        {'source_key': 'B0078-1', 'layer': '古籍正文', 'locator': '0407a02–03',
         'quote': '柰林西有都堂，有流觴池，堂東有扶桑海。凡此諸海，皆有石竇流於地下，西通穀水，東連陽渠，亦與翟泉相連。'},
    ],
    'B4:NG15': [
        {'source_key': 'B0077-1', 'layer': '古籍正文', 'locator': '0082a09',
         'quote': '瑤光寺北有承明門，有金墉城，即魏氏所築。'},
        {'source_key': 'B0077-1', 'layer': '现代夹注', 'locator': '0082a09',
         'quote': '城之西北門也。', 'after_body': '瑤光寺北有承明門'},
        {'source_key': 'B0077-1', 'layer': '现代夹注', 'locator': '0082a09',
         'quote': '有字上疑有脫文。', 'after_body': '有金墉城'},
        {'source_key': 'B0078-1', 'layer': '古籍正文', 'locator': '0387a06',
         'quote': '瑤光寺北有承明門，有金墉城，即魏氏所築。'},
    ],
}


# These are semantic reference classes, not new historical entity identifications.
CONTEXT_REFERENCES = {
    '洛阳城': ('regional_reference', [], '全城尺度参照；名录没有独立城点，不新增点或距离起点。'),
    'luoyang_city': ('regional_reference', [], '全城尺度参照；不把字符串解析成未登记实体ID。'),
    '广平王怀宅〔平等寺址〕': ('prior_use_state', [], '平等寺前身宅；不是另一广平王相关寺院的自动同一性证据。'),
    '杨氏家宅': ('prior_use_state', [], '家族宅转换叙事；不自动并到杨椿单宅或景宁寺。'),
    '谷水／阳渠': ('contextual_water_names', ['gushui', 'water_yangqu'], '水段命名语境保留；斜线不等于两条整河同一。'),
    '宫城': ('scope_reference', ['palace_scope'], '只能链接现有宫城范围示意，不落为单一点或精确边界。'),
    '南北': ('orientation_value', [], '朝向值，不是建筑、道路或地名实体。'),
    '建阳里／绥民里': ('compound_both_sides', ['li_jianyang', 'li_suimin'], '两个道路两侧参照并列；不能合成一里或任选其一。'),
    '渠水〔此段〕': ('unresolved_water_segment', [], '此段代词所指尚未独立定位，不自动绑定整条谷水或阳渠。'),
    '庄严寺／东安里': ('ambiguous_antecedent', ['v2_zhuangyan', 'li_dongan'], '北为租场的回指保留寺／里两种范围，不能自动选唯一。'),
    '张伦宅园': ('nested_scope_reference', ['house_zhanglun'], '宅与园的层级关联，仅作导航；私园景阳山不得并入宫苑同名山。'),
    '寺院': ('self_extent_attribute', [], '方五百步是本寺范围描述，目标为自身的属性，不是缺失寺院。'),
    '萧正德宅': ('contextual_name_link', ['house_xiaozhengde'], '归正里萧正德宅名称导航；不以授宅纪年自动确定改寺日期。'),
    '汉濯龙园': ('disputed_period_identity_claim', ['garden_zhuolong'], 'same_site_claim仅是跨时段同址说，不能升级为已证同址。'),
    '秦太上公二寺': ('ambiguous_group_antecedent', ['v3_qintaigong_e', 'v3_qintaigong_w'], '东向关系的上文回指可能指东寺或二寺组，不能强加为两座各自的东向测量。'),
    '永桥／洛水': ('compound_distinct_roles', ['bridge_yong', 'luoshui'], '桥为语境、洛水为岸线参照，二者并非别名。'),
    '四夷馆里区域': ('aggregate_scope_reference', [], '馆里组合范围，无独立实体或确定四至点。'),
    '伊水／洛水': ('compound_boundary_rivers', ['water_yi', 'luoshui'], '伊、洛是两个区间参照，保留集合；不生成河道中心线。'),
    '白象': ('nonbuilt_object', [], '动物对象，不是白象坊；不能按白象二字把饲养史变为坊址关系。'),
    'city_reference_in_jinyong_context': ('ambiguous_city_antecedent', [], '城西的城承接金墉叙事但范围仍须核；不自动选金墉城或洛阳城。'),
}


def literal_references(entities):
    ids = {entity['id'] for entity in entities}
    names = defaultdict(set)
    for entity in entities:
        for name in [entity.get('name'), entity.get('source_name'), *entity.get('aliases', [])]:
            if isinstance(name, str) and name:
                names[name].add(entity['id'])
    result = []
    for entity in entities:
        for index, constraint in enumerate(entity['constraints']):
            target = constraint.get('target_id') or constraint.get('target')
            if target in ids or target in EXTERNAL_REFERENCES or constraint.get('target_id'):
                continue
            candidates = sorted(names.get(target, []))
            if target in CONTEXT_REFERENCES:
                kind, candidates, meaning = CONTEXT_REFERENCES[target]
            elif len(candidates) == 1:
                kind = 'unique_catalog_name_link'
                meaning = '与名录名称或别名唯一字面相合；仅改善导航，不是原文同一性、同期性或位置复核。'
            elif candidates:
                kind, meaning = 'ambiguous_catalog_name', '同名字面对应多个目录对象，保持候选并列。'
            else:
                kind, meaning = 'unresolved_literal', '尚无可用语义分类或目录候选。'
            result.append({
                'reference_key': f'{entity["id"]}:constraint:{index}',
                'entity_id': entity['id'], 'entity_name': entity['name'], 'constraint_index': index,
                'relation': constraint.get('relation'), 'raw_target': target,
                'original_constraint': deepcopy(constraint),
                'resolution_class': kind, 'candidate_entity_ids': list(candidates),
                'meaning': meaning, 'historical_identity_verified': False,
                'adds_spatial_constraint': False, 'adds_entity_or_coordinates': False,
                'navigation_link_allowed': bool(candidates),
                'navigation_link_is_historical_proof': False,
            })
    return result


def build(cache):
    sources, snapshots = load_sources(cache)
    records, inputs = [], []
    entity_data = json.loads((ROOT / 'data/entities.json').read_text())
    entity_ids = {x['id'] for x in entity_data}
    for batch, path, field, entity_field in EVIDENCE_INPUTS:
        raw = (ROOT / path).read_bytes()
        data = json.loads(raw)
        inputs.append({'path': path, 'sha256': hashlib.sha256(raw).hexdigest(), 'records': len(data[field])})
        source_defs = {s['id']: s for s in data['sources']}
        for record in data[field]:
            key, quote = batch + ':' + record['id'], record['quote']
            refs = record.get(entity_field, [])
            if isinstance(refs, str):
                refs = [refs]
            checks = []
            for sid in quote_sources(record):
                declared_url = source_defs[sid]['url']
                sk = source_key(declared_url)
                source = sources.get(sk)
                body_match = sequence_match(quote, source['body'], source['body_loc']) if source else None
                note_match = sequence_match(quote, source['note'], source['note_loc']) if source else None
                comparison = EDITION_COMPARISONS.get((key, sk))
                variant_context = None
                if comparison:
                    variant_hits = sequence_match(comparison[1], source['body'], source['body_loc'])
                    assert variant_hits, (key, sk, 'secondary edition comparison failed')
                    variant_context = {'finding': comparison[0], 'source_quote': comparison[1],
                                       'segments': variant_hits, 'method': 'manual_difference_comparison',
                                       'new_historical_discovery': False}
                checks.append({
                    'declared_source_id': sid, 'declared_url': declared_url, 'source_snapshot_key': sk,
                    'retrieved_url': source['url'] if source else None,
                    'edition_mirror_used': bool(source and source['url'] != declared_url.split('#')[0]),
                    'method': 'ordered_normalized_character_match',
                    'status': ('matched_in_pdf_extraction_context_checked' if sk == 'LF' else 'matched_in_nonmodern_note_text') if body_match else 'not_exactly_matched',
                    'segments': body_match or [],
                    'also_occurs_in_modern_note': bool(note_match) if sk != 'LF' else None,
                    'edition_difference_review': variant_context,
                    'independent_historical_corroboration': False,
                })
            exact = any(c['segments'] for c in checks)
            manual = deepcopy(MANUAL_EXCEPTIONS.get(key))
            if manual:
                manual['method'] = 'manual_context_and_layer_comparison_then_exact_corrected_excerpt_match'
                manual['corrected_excerpt_checks'] = []
                for sk in manual['source_keys']:
                    source = sources[sk]
                    matches = sequence_match(manual['corrected_quote'], source['body'], source['body_loc'])
                    manual['corrected_excerpt_checks'].append({
                        'source_snapshot_key': sk, 'url': source['url'], 'segments': matches or [],
                        'status': 'matched' if matches else 'requires_further_comparison',
                    })
                manual['source_contexts'] = deepcopy(SOURCE_CONTEXTS.get(key, []))
                for context in manual['source_contexts']:
                    source = sources[context['source_key']]
                    layer = 'note' if context['layer'] == '现代夹注' else 'body'
                    context['url'] = source['url']
                    context['segments'] = sequence_match(context['quote'], source[layer], source[layer + '_loc'])
                    assert context['segments'], (key, 'context excerpt failed')
            pending = ['古刻、写本或书影逐叶校勘未做；电子匹配不等于所有版本同文。',
                       '实体同一性、同一时点存在及古代绝对位置不由字符串相合证明。']
            if any(not c['segments'] and not c['edition_difference_review'] for c in checks) and not manual:
                pending.append('部分同时列出的版本未逐差裁决；本条只以成功匹配的版本确认引文字面。')
            reading = (record.get('reading') or record.get('interpretation') or record.get('limit')
                       or record.get('claim') or record.get('note'))
            markers = any(ch in quote for ch in ('〈', '〔', '（'))
            quotation_class = (manual['kind'] if manual else 'edited_reading_with_visible_markers' if markers
                               else 'explicit_excerpt' if re.search('[…⋯]', quote) else 'continuous_short_quote')
            risks = ['no_metric_or_absolute_location_from_quote_match']
            if re.search(r'[一二三四五六七八九十百千]+[里步丈尺]', quote):
                risks.append('original_distance_or_size_not_modern_metres_or_map_pixels')
            if any(word in quote for word in ('永安', '永熙', '普泰', '武定', '中朝', '晉', '漢', '河陰')):
                risks.append('time_layers_require_separate_interpretation')
            if any(word in quote for word in ('上有', '寺北', '寺南', '山南', '其', '城西')):
                risks.append('antecedent_or_scope_must_be_preserved')
            if markers:
                risks.append('edition_emendation_is_visible_not_new_independent_witness')
            if manual:
                risks.append(manual['kind'])
            records.append({
                'key': key, 'batch': batch, 'legacy_id': record['id'], 'legacy_path': path,
                'affected_entity_ids': refs, 'legacy_title': record.get('title', record.get('short_title', key)),
                'legacy_quote': quote, 'legacy_locator': record.get('locator', record.get('anchor')),
                'quotation_class': quotation_class, 'source_checks': checks,
                'legacy_evidence_layer': record.get('kind', record.get('layer', record.get('textual_layer'))),
                'record_role': ('project_logic_with_ancient_quote' if key == 'v2.5:E18' else
                                'drawing_decision_with_source_quote' if batch == 'B1' else
                                'historical_evidence_excerpt_and_interpretation'),
                'source_families': sorted({next(s['family'] for s in snapshots if s['key'] == c['source_snapshot_key'])
                                           for c in checks if c['source_snapshot_key']}),
                'electronic_text_checked': exact or bool(manual and all(x['segments'] for x in manual['corrected_excerpt_checks'])),
                'legacy_quote_passed_normalized_sequence_check': exact,
                'manual_context_review': manual,
                'checked_scope': '引文字面与明确文本层；不升级空间、身份或年代证据等级。',
                'legacy_reading_preserved': reading,
                'legacy_temporal_note_preserved': record.get('temporal_note'),
                'map_risks': risks, 'pending': pending,
                'geographic_coordinates': None,
            })
    refs = literal_references(entity_data)
    corrections = {r['key']: r for r in records if r['manual_context_review']}
    decisions = map_decisions(corrections)
    result = {
        'schema_version': VERSION, 'reviewed_at': REVIEW_DATE,
        'baseline_commit': '1d541938cb8b21cb218d5bbd934cf41bbdfa9fc8',
        'scope': '盛时文献平面图第一阶段：历批引文复查、字面约束分类、供新工作层使用的更正与制图界限。',
        'method': {
            'downloaded_current_sources': True,
            'normalization': 'NFKC；去标点、空白、控制字符及【校】版式标签；不自动简繁转换，不合并婬/淫、淩/凌、𣲖/派等字。',
            'ellipsis_rule': '仅允许原quote显式省略号分割的片段按原顺序命中；未标省略的拼接不放宽匹配。',
            'body_rule': 'CBETA剥离small.inline-note现代校注，保留古书子注；引用中的现代校补字仍须说明。',
            'source_family_rule': '周、范、四部丛刊及范电子PDF同属伽蓝记文本家族；不同整理本相合不计独立目击票数。',
            'source_list_rule': '旧sources有时是整条证据的支持书目，未逐句指定引本；分别报告实际命中的版本与差异，不能预设列表中每本都应逐字一致。',
            'automation_limit': '匹配是转录追溯检查；不是人工逐字校勘183条、证明236处关系或获得古址定位。',
            'legacy_data_modified': False, 'new_ancient_coordinates': 0,
        },
        'inputs': inputs + [{'path': 'data/entities.json', 'sha256': hashlib.sha256((ROOT / 'data/entities.json').read_bytes()).hexdigest()}],
        'source_snapshots': snapshots, 'records': records,
        'constraint_references': refs, 'map_decisions': decisions,
        'counts': {
            'evidence_records': len(records), 'batches': dict(Counter(r['batch'] for r in records)),
            'legacy_quote_sequence_match_records': sum(r['legacy_quote_passed_normalized_sequence_check'] for r in records),
            'manual_exception_records': len(corrections),
            'electronic_text_checked_records': sum(r['electronic_text_checked'] for r in records),
            'text_check_pending_records': sum(not r['electronic_text_checked'] for r in records),
            'source_snapshots': len(snapshots),
            'source_check_attempts': sum(len(r['source_checks']) for r in records),
            'source_checks_exact_matched': sum(bool(c['segments']) for r in records for c in r['source_checks']),
            'records_with_unmatched_declared_edition': sum(any(not c['segments'] for c in r['source_checks']) for r in records),
            'secondary_edition_difference_reviews': sum(bool(c['edition_difference_review']) for r in records for c in r['source_checks']),
            'unexplained_electronic_quote_mismatch_records': sum(
                any(not c['segments'] and not c['edition_difference_review'] for c in r['source_checks'])
                and not r['manual_context_review'] for r in records),
            'version_readings_identified_not_arbitrated': 10,
            'new_substantive_project_quote_errors': 2,
            'inherited_b8_g15_correction': 1,
            'literal_constraint_references': len(refs),
            'distinct_literal_targets': len({r['raw_target'] for r in refs}),
            'literal_reference_classes': dict(Counter(r['resolution_class'] for r in refs)),
            'literal_links_promoted_to_historical_evidence': 0,
            'new_entity_ids': 0, 'new_ancient_absolute_coordinates': 0,
        },
        'release_rules': ['新工作层展示更正；旧JSON、封存图件和旧ID不覆写。',
                          '图上距离、路网长度、坊界和池岸仍不由电子文字匹配生成。',
                          '盛时综合窗口需保留构件时层，不把后出塔、寺用途或狮子前推。'],
    }
    validate(result, entity_ids)
    return result


def map_decisions(corrections):
    def correction(key, did, title, visual_instruction):
        rec = corrections[key]
        manual = rec['manual_context_review']
        return {
            'id': did, 'title': title, 'evidence_keys': [key],
            'affected_entity_ids': rec['affected_entity_ids'],
            'corrected_quote': manual['corrected_quote'],
            'editorial_note': manual.get('editorial_note'),
            'source_checks': manual['corrected_excerpt_checks'],
            'source_contexts': manual['source_contexts'],
            'locator': manual['locator'], 'finding': manual['finding'],
            'visual_instruction': visual_instruction,
            'new_project_error_found': bool(manual.get('new_project_error_found')),
            'creates_new_entity_or_coordinates': False,
        }
    result = [
        correction('B2:G13', 'TXT01', '都堂参照柰林，扶桑为海',
                   '在宫苑未定位关系插图中将扶桑海明确用水体符号与标签；都堂置于柰林西的关系箭头，不连向碑西。碑在柰林南，苗茨堂在碑北。不要据此填池岸、堂尺寸或把插图点落到全城地理坐标。'),
        correction('B4:NG15', 'TXT02', '承明正文与周氏方位注分层',
                   '瑶光—承明关系显示“正文：寺北”；“城之西北门”为周祖谟夹注独立标签。西墙门序另由NG13/WR01支撑；有金墉城接句不补缺文为精确相邻线。'),
        correction('v2.7:N02', 'TXT03', '东石桥节录补省略标识',
                   '桥北两里与桥南马市保持不同关系记录；证据卡更正删节，不因原引拼接移动桥、里或补密集道路。'),
        correction('v2.7:N03', 'TXT04', '阳渠两岸节录补省略标识',
                   '证据卡用明示删节引文；明悬、建阳里与租场各自原关系保留，不把节录当连续地块边界。'),
        correction('B2:G15', 'TXT05', '继承B8水情引文更正',
                   '继续把旱时注水、雨时泄水与地下集合联系分列；保留正文陽穀及改渠校注，不画常流或逐池全网。标签明确“B8已更正，本轮复核”。'),
        correction('v2.7:N14', 'TXT06', '行像到宣阳不补跨永桥',
                   '行像路线只保留景明集像、次日入宣阳和向宫前这段文献联系；不将永桥编入必经路线。'),
        correction('B2:G16', 'TXT07', '瑶光事件与寺毁分开',
                   '事件标签保留530侵扰，不能据此把寺或五层塔绘为废墟；正文显示婬字，转写可在释文使用淫。'),
    ]
    result.extend([
        {'id': 'TXT08', 'title': '文字约束导航不升级为史证',
         'evidence_keys': [], 'affected_entity_ids': [], 'corrected_quote': None, 'editorial_note': None,
         'finding': '236处旧字面目标并非236个缺失地点；名称匹配、范围、对象与回指必须分开。',
         'visual_instruction': '唯一名称可加跳转；复合目标展示全部角色；歧义目标列候选；南北、寺院、白象分别作为朝向、自身尺寸、动物，不放地理点。',
         'creates_new_entity_or_coordinates': False},
        {'id': 'TXT09', 'title': '城门—御道—水系骨架的可用层次',
         'evidence_keys': ['B4:NG01', 'B5:WR01', 'B6:EO01', 'v2.7:N04', 'v2.7:N08', 'v2.7:N10', 'B7:LR04'],
         'affected_entity_ids': ['gate_daxia', 'gate_guangmo', 'gate_chengming', 'gushui', 'water_yangqu', 'bridge_yong'],
         'corrected_quote': None, 'editorial_note': None,
         'finding': '门序与明确方向可以作关系骨架；水经注叙事先后、原里距及伊洛间区域不提供现代度量或确切古河线。',
         'visual_instruction': '分别呈现城门序、道侧和水段联系；桥下流水不等于沿河道路，地下池联系不绘地表河道。一里余、四里、周回八里等保留原单位与语境。',
         'creates_new_entity_or_coordinates': False},
        {'id': 'TXT10', 'title': '盛时寺本体与后出构件分别呈现',
         'evidence_keys': ['B5:WR09', 'B5:WR18', 'B5:WR20', 'B6:EO11', 'B6:EO13', 'B6:EO18', 'B7:LR14'],
         'affected_entity_ids': ['w_dajue', 'v2_pingdeng', 'v2_jianzhong', 'v2_guijue'],
         'corrected_quote': None, 'editorial_note': None,
         'finding': '532年以后塔、529年以后改寺、531年以后建中状态及永安末到京狮子不能并进516—528河阴前主景。',
         'visual_instruction': '默认盛时只画有相应时层支持的用途与构件；未定年建筑保持未定，后出塔和活狮不放入盛时全景。不能由寺名出现推得全套构件在窗口全程竣工。',
         'creates_new_entity_or_coordinates': False},
        {'id': 'TXT11', 'title': '相对地势与人工园山保持不同来源',
         'evidence_keys': ['B4:NG08', 'B2:G08', 'B2:G10'],
         'affected_entity_ids': ['n_ningxuan', 'ic_penglai', 'ic_jingyang_hill'],
         'corrected_quote': None, 'editorial_note': None,
         'finding': '凝玄地形高显是相对高差线索；蓬莱是海内营作山，景山殿名物仍有校读条件。',
         'visual_instruction': '历史地形阶段可保留相对高地假说，但不能用现代DSM高点匹配宫苑人工山或由诗性高显推算塔高和坡面。',
         'creates_new_entity_or_coordinates': False},
    ])
    return result


def validate(data, entity_ids=None):
    if entity_ids is None:
        entity_ids = {x['id'] for x in json.loads((ROOT / 'data/entities.json').read_text())}
    records, refs = data['records'], data['constraint_references']
    assert len(records) == 183, 'Evidence coverage changed; review the intended input set.'
    assert len({r['key'] for r in records}) == 183, 'Repeated evidence key.'
    assert len(refs) == 236, 'Literal-reference coverage changed.'
    assert len({r['reference_key'] for r in refs}) == 236
    assert all(not r['historical_identity_verified'] and not r['adds_spatial_constraint'] for r in refs)
    assert all(set(r['candidate_entity_ids']) <= entity_ids for r in refs)
    assert all(r['geographic_coordinates'] is None for r in records)
    assert all(set(d['affected_entity_ids']) <= entity_ids for d in data['map_decisions'])
    assert data['counts']['literal_links_promoted_to_historical_evidence'] == 0
    assert data['counts']['new_ancient_absolute_coordinates'] == 0
    keys = {r['key'] for r in records}
    assert all(set(d['evidence_keys']) <= keys for d in data['map_decisions'])
    g13 = next(d for d in data['map_decisions'] if d['id'] == 'TXT01')
    assert '柰林西有都堂' in g13['corrected_quote'] and '堂東有扶桑海' in g13['corrected_quote']
    assert '碑西有都堂' not in g13['corrected_quote'] and '扶桑殿' not in g13['corrected_quote']
    ng15 = next(d for d in data['map_decisions'] if d['id'] == 'TXT02')
    assert '城之西北門' not in ng15['corrected_quote'] and ng15['editorial_note']['layer'] == '现代夹注'
    assert next(r for r in records if r['key'] == 'B2:G15')['manual_context_review']['prior_correction'] == 'B8:CB14'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-cache', type=Path, help='Directory with 10 CBETA HTML, H/W/W16/L3S HTML and LF.pdf/LF.txt; not committed.')
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--check', action='store_true', help='Validate existing output without accessing source cache.')
    args = parser.parse_args()
    if args.check:
        data = json.loads(args.output.read_text())
        validate(data)
    else:
        if not args.source_cache:
            parser.error('--source-cache is required when generating the ledger')
        data = build(args.source_cache)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(data['counts'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
