#!/usr/bin/env python3
"""H1: add the public reading entrance after the complete B8 build.

Only the current entry HTML and publishing metadata are replaced. Source data,
geometry, historical entry points and downloadable research remain byte-exact.
"""
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import json
import re

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / '_site'
MUTABLE = {'index.html', 'v3.0-dual.html', 'release.json', 'build-info.json'}
VERSION = 'homepage-v1'
QUESTIONS = [
    {'id': 'yongning', 'number': '01', 'theme': '寺院与建筑',
     'title': '永宁寺里除了高塔还有什么？',
     'description': '从高塔读到塔北佛殿，看寺院的构成怎样进入文献地图。',
     'action': '进入永宁寺',
     'href': './dual-b2.html#literary?region=L01&entity=ic_yongning',
     'evidence': ['B01', 'B02'], 'research_module': 'B1+B2'},
    {'id': 'markets', 'number': '02', 'theme': '市场与日常',
     'title': '洛阳人到哪里买鱼？',
     'description': '读归正里鱼鳖市与洛水南四通市的记载，分清生活场景与方位线索。',
     'action': '走进洛南市场',
     'href': './dual-luonan.html#markets?id=LR10',
     'evidence': ['LR07', 'LR10'], 'research_module': 'B7'},
    {'id': 'identity', 'number': '03', 'theme': '同名与辨认',
     'title': '书里同名的寺是否就是同一座？',
     'description': '从宝明、白马寺的不同记载，看看同名为什么还需要身份核对。',
     'action': '打开身份核对案例',
     'href': './dual-city-review.html#view=cases&case=CB01',
     'evidence': ['CB01'], 'research_module': 'B8'},
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def fingerprint(name, body):
    dest = '_assets/' + hashlib.sha256(body).hexdigest()[:20] + '-' + name
    path = SITE / dest
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return './' + dest


class Elements(HTMLParser):
    """Keep exact source slices, including nested divs and inline scripts."""
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
            'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.offsets = [0]
        self.offsets.extend(m.end() for m in re.finditer('\n', source))
        self.stack = []
        self.nodes = []
        self.feed(source)

    def source_position(self):
        line, col = self.getpos()
        return self.offsets[line - 1] + col

    def handle_starttag(self, tag, attrs):
        start = self.source_position()
        node = {'tag': tag, 'attrs': dict(attrs), 'start': start,
                'content_start': start + len(self.get_starttag_text())}
        if tag in self.VOID:
            node['content_end'] = node['content_start']
            node['end'] = node['content_start']
            self.nodes.append(node)
        else:
            self.stack.append(node)

    def handle_endtag(self, tag):
        match = next((i for i in range(len(self.stack) - 1, -1, -1)
                      if self.stack[i]['tag'] == tag), None)
        if match is None:
            return
        node = self.stack[match]
        self.stack = self.stack[:match]
        node['content_end'] = self.source_position()
        node['end'] = self.source.index('>', node['content_end']) + 1
        self.nodes.append(node)

    def one(self, *, ident=None, cls=None, tag=None):
        hits = [n for n in self.nodes
                if (ident is None or n['attrs'].get('id') == ident)
                and (cls is None or cls in n['attrs'].get('class', '').split())
                and (tag is None or n['tag'] == tag)]
        assert len(hits) == 1, (ident, cls, tag, len(hits))
        return hits[0]


def home_intro(large, small, width, height):
    cards = []
    for q in QUESTIONS:
        cards.append(
            f'<a class="home-question" data-question="{q["id"]}" href="{escape(q["href"], quote=True)}">'
            f'<span class="home-question-index"><b>{q["number"]}</b><span>{q["theme"]}</span></span>'
            f'<h3>{q["title"]}</h3><p>{q["description"]}</p>'
            f'<span class="home-question-action"><span>{q["action"]}</span><span aria-hidden="true">↗</span></span></a>')
    return f'''
<div id="home-introduction">
  <section id="home-hero" class="home-hero" aria-labelledby="home-title">
    <figure><picture><source media="(max-width: 600px)" srcset="{small}">
      <img src="{large}" width="{width}" height="{height}" fetchpriority="high" decoding="async" alt="北魏洛阳研究性复原示意：木塔、坊里与长街向远处宫城展开，前景城门和人物显示城市尺度。">
    </picture><figcaption class="home-image-note">北魏洛阳 · 研究性复原示意</figcaption></figure>
    <div class="home-hero-copy"><p class="home-kicker">NORTHERN WEI · LUOYANG　/　516—528</p>
      <h1 id="home-title">走进一千五百年前的洛阳</h1>
      <p class="home-hero-deck">从一座寺院、一处市场、一段记载，读懂一座都城。</p>
      <div class="home-hero-actions"><a id="home-start" class="home-primary" href="#map" data-home-scroll="page-map">开始探索 <span aria-hidden="true">→</span></a>
        <a class="home-secondary" href="#home-questions" data-home-scroll="home-questions">从三个问题出发 <span aria-hidden="true">↓</span></a></div>
    </div>
  </section>
  <section id="home-questions" class="home-questions" aria-labelledby="home-questions-title">
    <div class="home-section-heading"><div><p class="home-kicker">从文字走进城市</p><h2 id="home-questions-title">一座城，许多读法</h2></div><p>带着一个问题出发，沿地图找到记载，再看看文字能告诉我们什么。</p></div>
    <div class="home-question-grid">{''.join(cards)}</div>
  </section>
</div>
'''


def research_hub(navigation, updates):
    return f'''
<section id="home-research" class="home-research" aria-labelledby="home-research-title">
  <div class="home-section-heading"><div><p class="home-kicker">史料、方法与持续修订</p><h2 id="home-research-title">这座城，怎样被读出来？</h2></div><p>回到原文，核对方位、身份与年代。每一步复原，都留下可以继续追问的线索。</p></div>
  <div class="home-methods"><div><h3>从《洛阳伽蓝记》出发</h3><p>先读记载，再区分校注、研究解释与绘图安排。首页主图用于呈现城市意象；互动文献地图保留文献依据与未定之处。516—528 年为盛时综合时层。</p></div><div class="home-methods-links"><a href="#about">阅读研究方法与来源说明 ↗</a><a href="#issues">查看史料争议与当前解释 ↗</a><a href="./dual-city-review.html">浏览全城总校核 B8 ↗</a></div></div>
  <nav class="home-library-nav" aria-label="研究专题">{navigation}</nav>
  <div class="home-research-updates">{updates}</div>
  <p class="home-research-footnote">研究持续修订 · 当前成果 B1—B8。历史版本、图册与逐条来源继续保留；下一研究批次为 B9 引文核对。</p>
</section>
'''


def main():
    info = json.loads((SITE / 'build-info.json').read_text())
    release = json.loads((SITE / 'release.json').read_text())
    assert info.get('city_review_b8', {}).get('entities') == 339, 'Run the complete B8 build first'
    index = (SITE / 'index.html').read_text(encoding='utf-8')
    assert 'id="home-introduction"' not in index, 'Rebuild preceding stages before H1'
    protected = {str(p.relative_to(SITE)): digest(p) for p in SITE.rglob('*')
                 if p.is_file() and str(p.relative_to(SITE)) not in MUTABLE}
    image_source = ROOT / 'web/assets/luoyang-panorama.webp'
    small_source = ROOT / 'web/assets/luoyang-panorama-small.webp'
    with Image.open(image_source) as source:
        width, height = source.size
    large = fingerprint('luoyang-panorama.webp', image_source.read_bytes())
    small = fingerprint('luoyang-panorama-small.webp', small_source.read_bytes())
    css = fingerprint('homepage-v1.css', (ROOT / 'web/homepage-v1.css').read_bytes())
    js = fingerprint('homepage-v1.js', (ROOT / 'web/homepage-v1.js').read_bytes())
    parsed = Elements(index)
    nav = parsed.one(tag='nav', cls='topnav')
    navigation = index[nav['content_start']:nav['content_end']]
    header = parsed.one(cls='map-header')
    workspace = parsed.one(cls='workspace')
    page = parsed.one(ident='page-map')
    assert header['start'] > page['start'] and workspace['end'] < page['end']
    updates = index[header['end']:workspace['start']]
    assert 'id="city-b8-entry"' in updates and 'id="luonan-b7-entry"' in updates
    fresh_nav = '''<a href="#home" data-home-nav="home" data-home-scroll="home-hero">首页</a><a href="#map" data-home-nav="map" data-home-scroll="page-map">探索地图</a><a href="#atlas" data-home-nav="atlas">图册</a><a href="#home-research" data-home-nav="home-research" data-home-scroll="home-research">研究进展</a>'''
    changes = [
        (nav['content_start'], nav['content_end'], fresh_nav),
        (header['end'], workspace['start'], '\n'),
        (page['content_end'], page['content_end'], research_hub(navigation, updates)),
        (page['start'], page['start'], home_intro(large, small, width, height)),
    ]
    for start, end, replacement in sorted(changes, reverse=True):
        index = index[:start] + replacement + index[end:]
    index = index.replace('<body>', '<body>\n<a class="home-skip" href="#map" data-home-scroll="page-map">跳到互动地图</a>', 1)
    index = re.sub(r'<title>[^<]+</title>', '<title>北魏洛阳 · 走进一千五百年前的都城</title>', index, count=1)
    index = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="从一座寺院、一处市场、一段记载走进北魏洛阳。探索文献地图、历史问题与可追溯的研究证据。">', index, count=1)
    boot = "document.documentElement.dataset.homeView=(!location.hash||/^#home(?:$|-questions$)/.test(location.hash))?'home':'detail';"
    index = index.replace('</head>', f'<script>{boot}</script><link rel="stylesheet" href="{css}"></head>', 1)
    index = index.replace('</body>', f'<script defer src="{js}"></script></body>', 1)
    for current in ('index.html', 'v3.0-dual.html'):
        (SITE / current).write_text(index, encoding='utf-8')
    metadata = {
        'version': VERSION, 'interface_milestone': 'H1', 'source_commit': info['source_commit'],
        'research_milestone': 'B8', 'next_research_milestone': 'B9',
        'research_release_unchanged': release['release'], 'questions': QUESTIONS,
        'hero': {'asset': large.removeprefix('./'), 'small_asset': small.removeprefix('./'),
                 'width': width, 'height': height, 'description': '研究性复原示意',
                 'generated_image': True, 'measured_reconstruction': False},
        'new_historical_claims': 0, 'new_ancient_coordinates': 0,
        'research_data_changed': False, 'source_geometry_changed': False,
    }
    dump(SITE / 'homepage/metadata.json', metadata)
    assert all(digest(SITE / path) == expected for path, expected in protected.items()), 'H1 changed protected research resource'
    dump(SITE / 'homepage/preservation.json', {
        'version': VERSION, 'source_commit': info['source_commit'],
        'protected_unchanged': True, 'protected_files': len(protected), 'sha256': protected,
        'intentional_updates': sorted(MUTABLE),
    })
    release['extensions'] = sorted(set(release.get('extensions', [])) | {VERSION})
    release['homepage_version'] = VERSION
    release['current_milestone'] = 'H1 首页阅读入口；研究工作层保持 B8'
    dump(SITE / 'release.json', release)
    info['homepage'] = {key: metadata[key] for key in ('version', 'interface_milestone', 'source_commit',
                                                    'research_milestone', 'new_historical_claims',
                                                    'new_ancient_coordinates', 'research_data_changed',
                                                    'source_geometry_changed')}
    info['homepage']['question_count'] = len(QUESTIONS)
    info['homepage']['protected_files'] = len(protected)
    info['homepage']['metadata'] = 'homepage/metadata.json'
    info['files_sha256'] = {str(p.relative_to(SITE)): digest(p) for p in sorted(SITE.rglob('*'))
                           if p.is_file() and p.name != 'build-info.json'}
    dump(SITE / 'build-info.json', info)
    dump(ROOT / 'artifacts/homepage-build.json', {
        'version': VERSION, 'source_commit': info['source_commit'],
        'protected_unchanged': True, 'protected_files': len(protected), 'questions': QUESTIONS,
        'hero': metadata['hero'], 'interface_only': True,
    })
    print(f'H1: panoramic homepage, 3 evidence routes, research after the map; {len(protected)} research assets preserved.')


if __name__ == '__main__':
    main()
