#!/usr/bin/env python3
"""Publish B8's whole-city association review and explicit correction layer."""
from pathlib import Path
import copy
import csv
import html
import json
import re
import zipfile
import xml.etree.ElementTree as ET

import cairosvg
from city_audit_b8 import build_audit
from dual_cartography import NS, C, load, dump, node, text, para, rect, path, svg, world, crop, write_svg
from north_b4 import sha, fp, heading, render_atlas

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / '_site'
CASES = ROOT / 'research/dual-b8/cross-batch-review.json'
BASE = 'e959da7c16db7cb814bb7460c03e5c7d860be1fa'
MUTABLE = {'build-info.json','release.json','index.html','v3.0-dual.html',
           'dual-b2.html','downloads/dual-map-report.html'}
COLORS = {'case':C['gold'],'evidence':C['green'],'catalog':'#89938e'}


def read_cases():
    data = load(CASES)
    assert [r['id'] for r in data['records']] == [f'CB{i:02}' for i in range(1,15)]
    known = {e['id'] for e in load(ROOT / 'data/entities.json')}
    assert all(set(r['entities']) <= known for r in data['records'])
    assert all(r['geographic_coordinates'] is None for r in data['records'])
    return data


def enrich_ledger(ledger, cases):
    result = copy.deepcopy(ledger)
    for row in result['entities']:
        applicable = [c for c in cases['records'] if row['id'] in c['entities']]
        row['case_ids'] = [c['id'] for c in applicable]
        row['display_name'] = row['name']
        row['current_review'] = {}
        for c in applicable:
            over = c.get('display_overrides', {}).get(row['id'], {})
            if over:
                row['current_review'].update(copy.deepcopy(over))
                row['display_name'] = over.get('name', over.get('display_name', row['display_name']))
        row['review_status'] = 'structure_checked_with_case_links' if applicable else 'structure_checked_history_not_reassessed'
    result['case_count'] = len(cases['records'])
    result['case_linked_entities'] = sum(bool(e['case_ids']) for e in result['entities'])
    result['baseline_commit'] = BASE
    return result


def changed_master(source, ledger):
    root = ET.parse(source).getroot()
    wg = world(root)
    before = [ET.tostring(c) for c in wg]
    targets = {}
    entity_lookup = {e['id']:e for e in ledger['entities']}
    for e in ledger['entities']:
        for t in e['targets']:
            if t['id'] in targets:
                assert targets[t['id']] == t
            targets[t['id']] = t
    assert len(targets) == 179
    overlay = node(wg, 'g', id='city-audit-overlay-b8', data_batch='dual-b8',
                   data_footprint='false', data_coordinate_frame='existing_documentary_targets',
                   style='pointer-events:none')
    ring_counts = {k:0 for k in COLORS}
    for tid, target in sorted(targets.items(), key=lambda kv:kv[1]['source_index']):
        members = [entity_lookup[i] for i in target['member_ids']]
        category = 'case' if any(e['case_ids'] for e in members) else 'evidence' if any(e['direct_evidence_refs'] for e in members) else 'catalog'
        ring_counts[category] += 1
        shared = target['kind'] == 'group' or target['member_count'] > 1
        g = node(overlay, 'g', **{'class':'city-review-target'}, data_target_id=tid,
                 data_entity_ids=' '.join(target['member_ids']), data_review_category=category,
                 data_shared=str(shared).lower(), data_footprint='false',
                 aria_label=target['label'] + '；沿用交互阅读锚点，非地理位置')
        node(g, 'title').text = target['label'] + ('；共享阅读组，成员不拆点。' if shared else '；单实体交互不等于实测定位。')
        node(g, 'circle', cx=target['x'], cy=target['y'], r=108, fill='transparent', **{'class':'b8-hit'})
        node(g, 'circle', cx=target['x'], cy=target['y'], r=64, fill='none',
             stroke=COLORS[category], stroke_width=8, opacity='.82', **{'class':'b8-ring'})
        if shared:
            node(g, 'circle', cx=target['x'], cy=target['y'], r=87, fill='none',
                 stroke=COLORS[category], stroke_width=5, opacity='.7', stroke_dasharray='13 11', **{'class':'b8-ring'})
    assert [ET.tostring(c) for c in list(wg)[:-1]] == before
    for t in root:
        if t.get('class') in ['wt497 tb497','wt498 tb498','wt506 tb506','wt509 tb509']:
            for ch in list(t):
                t.remove(ch)
            t.text = {
                'wt497 tb497':'北魏洛阳 · 全城总校核 B8',
                'wt498 tb498':'339项结构关联逐项登记；跨批史证重点复核，旧字段与当前解释分列。',
                'wt506 tb506':'审校环：单环为单实体交互，双环为共享组；赭色涉及B8案例，绿色有历批引用，灰色仅名录关联。颜色不评定古址真实性。',
                'wt509 tb509':'全城审校 / B8'
            }[t.get('class')]
    audit = {'source_sha256':sha(source),'source_master':'assets/master-dual-b7-luonan.svg',
             'original_world_children':len(before),'all_original_world_children_preserved':True,
             'review_targets':len(targets),'review_target_categories':ring_counts,
             'anchors_moved':False,'new_ancient_coordinates':0,'new_interactive_targets':0,
             'overlay_role':'review_association_not_historical_confidence',
             'marker_catalog_unchanged':True}
    node(root,'metadata',id='city-review-metadata-b8').text = json.dumps(audit,ensure_ascii=False)
    return root, audit


def overview_plate(master, ledger, cases):
    r = svg(2200,1560,'B8 全城审校总览：交互与史证分开计数')
    heading(r,'LUOYANG / CITY REVIEW / B8','全城结构已清点，历史判断逐案复核','339实体保留身份；阅读环沿用179个交互锚点，颜色不评定古址真实性。')
    rect(r,75,240,1375,1170,'#f0f2e9',C['line'],2,8)
    crop(master,r,90,255,1345,1140,[0,0,12000,11160])
    x=1500
    metrics = [('339','实体完成结构清点','未将全部实体标为新获历史确证。'),
               ('136 + 101','单实体与共享组关联','分别关联136个单目标、43个共享或组目标。'),
               ('102','没有交互目标','道路、水体、附录与旁注的状态各自保留。'),
               (str(len(cases['records'])),'跨批次重点审校','身份、构件、方向、迁居与引文逐案登记。')]
    for i,(n,title,body) in enumerate(metrics):
        y=255+i*235
        text(r,x,y+45,n,58,C['green'],weight=500)
        text(r,x,y+92,title,27,C['ink'],weight=500)
        para(r,x,y+138,body,23,23)
        path(r,f'M{x} {y+208}H2125',C['line'],2)
    text(r,x,1250,'阅读环的三个类别',26,C['green'],weight=500)
    for i,(label,color) in enumerate([('涉及本批审校案例',C['gold']),('有历批显式引用',C['green']),('仅名录／既有图示关联','#89938e')]):
        y=1300+i*42
        node(r,'circle',cx=x+12,cy=y-8,r=11,fill='none',stroke=color,stroke_width=3)
        text(r,x+38,y,label,22,color)
    text(r,75,1460,'图上表达、点击关联、分区名录和历史确证是不同维度；无交互目标不等于漏画。',25,C['gold'])
    text(r,75,1510,'完整339项清单及每项出处可在网页与CSV查阅；古代地理坐标新增0。',22,C['muted'])
    return r


def coverage_plate(ledger):
    r=svg(2200,1560,'B8 11分区与339实体结构关联')
    heading(r,'B8 / STRUCTURAL INVENTORY','分区名录与图幅命中，分别记录','焦点名录是人工列举；图幅命中只计算既有点击锚点中心，不反推历史里属。')
    x=[90,230,1320,1570,1790]
    for xx,label in zip(x,['分区','主题','名录实体','图幅命中','地理边界']):
        text(r,xx,275,label,25,C['green'],weight=500)
    for i,reg in enumerate(ledger['regions']):
        y=310+i*76
        rect(r,75,y,2050,70,'#edf1e6' if i%2==0 else C['paper'],None,0,3)
        text(r,x[0],y+45,reg['code'],25,C['gold'])
        title=re.split('[·｜]',reg['title'],maxsplit=1)
        text(r,x[1],y+45,reg['title'],25,C['ink'])
        text(r,x[2],y+45,str(reg['explicit_focus_entities']),27,C['green'])
        text(r,x[3],y+45,str(reg['crop_entities']),27,C['blue'])
        text(r,x[4],y+45,'未据此确定',23,C['muted'])
    c=ledger['counts'];y=1200
    rect(r,75,y,1000,220,'#f1eddf',C['line'],2,8)
    text(r,105,y+50,'125个实体被显式列入分区',29,C['ink'],weight=500)
    para(r,105,y+100,'另214个没有进入focus名录。永宁、永桥各跨两区，名录次数不能直接加作实体数；现有图件仍保留。',36,24)
    rect(r,1110,y,1015,220,'#edf1e6',C['line'],2,8)
    text(r,1140,y+50,'209个实体有历批显式引用',29,C['ink'],weight=500)
    para(r,1140,y+100,'183条历批记录形成506次实体关联；其余130项不因未被引用而失去原始出处。时层事件另列。',36,24)
    text(r,75,1505,'只有现成锚点可以用于图幅命中；共有锚点仍是阅读组，不能为每个成员生成不同地址。',23,C['muted'])
    return r


def cases_plate(cases, chunk, number):
    r=svg(2200,1560,f'B8 跨批次审校索引 {number}')
    heading(r,'B8 / CROSS-BATCH REVIEW','跨批次审校：'+('身份、构件与前后时层' if number==1 else '道路、水体、里属与引文'),'每案保留旧记录、当前图示、本次处理和未决条件；这里是索引，完整原句见网页记录。')
    state={'display_resolved':'显示关系已厘清','separate_layers_required':'须保持分层','evidence_pending':'史证仍待核'}
    for i,c in enumerate(chunk):
        col=i%2;row=i//2;x=75+col*1040;y=245+row*298
        rect(r,x,y,1010,275,'#eef1e7',C['line'],2,8)
        text(r,x+25,y+42,c['id']+' · '+c['short_title'],29,C['green'],weight=500)
        text(r,x+25,y+80,state.get(c['review_state'],c['review_state']),20,C['gold'])
        body=c.get('plate_summary') or c['finding']
        if len(body)>99:body=body[:97]+'……'
        end=para(r,x+25,y+118,body,42,22)
        refs=' / '.join(x['batch']+':'+x['id'] for x in c['evidence_refs'][:5])
        text(r,x+25,y+247,refs,19,C['muted'])
    text(r,75,1508,'每条案例均连接既有实体ID；多个地点有共同人物、同名或相邻叙述，不自动合为同址。',23,C['muted'])
    return r


def corrections_plate(cases):
    r=svg(2200,1560,'B8 更正层：旧概述、基线字段与当前读法')
    heading(r,'B8 / ATTRIBUTED CORRECTIONS','把概述还原为概述，把条件写回显示','历史版本保留；本批增加可追溯更正和当前解释，不静默覆盖旧字段。')
    c=next(c for c in cases['records'] if c.get('errata'))
    er=c['errata']
    rect(r,75,245,2050,555,'#f2eddf',C['line'],2,8)
    text(r,105,300,c['id']+' / B2 G15：引文层更正',32,C['green'],weight=500)
    text(r,105,356,'旧记录 · 压缩概述',23,C['gold'])
    para(r,105,405,er.get('legacy_quote',''),78,29)
    text(r,105,493,'本次复核 · 从正文分离夹注后补录原句',23,C['gold'])
    para(r,105,550,er.get('corrected_source_quote',c.get('corrected_source_quote','')),70,30)
    para(r,105,660,'正文保留“陽穀”；范本所列“穀當作渠”另作校注。地下石窦、谷水与阳渠的关系不因此扩成连续地表河网。',78,24)
    text(r,105,756,'来源：周祖谟、范祥雍整理本卷一末“凡此诸海”段；完整定位与两本校注见CB14。',22,C['muted'])
    rect(r,75,845,1000,470,'#edf1e6',C['line'],2,8)
    text(r,105,902,'宝明寺：前期年代仍需身份条件',31,C['green'],weight=500)
    para(r,105,965,'旧名录保留“盛时已有记载”字段；B6的图符已标同名联接条件。B8在当前侧栏和总清单中优先展示这一条件，并将旧字段注明为基线记录。',36,26)
    rect(r,1110,845,1015,470,'#edf1e6',C['line'],2,8)
    text(r,1140,902,'萧宝夤宅：旧宅与迁居分别记',31,C['green'],weight=500)
    para(r,1140,965,'归正里宅在当前工作层按旧宅附见，后来永安里宅另记。新清单不让旧名录的简写遮住B7已核的迁居关系，也不与萧正德宅改寺合并。',36,26)
    para(r,75,1390,'本批没有据这些更正移动锚点、增加古址或改写年代未定的寺院成立年。具体的更正范围与旧页封存路径写入发布记录。',82,25)
    return r


def policy_plate(ledger,cases,access):
    r=svg(2200,1560,'B8 阅读方法与下一批证据门槛')
    heading(r,'B8 / READING GUIDE','接下来查什么，每一步需要什么证据','结构清点已覆盖全城；历史复核与原图获取按可核对象继续推进。')
    cards=[
        ('01  实体与图示','339项均可查名录、交互、分区、出处、时层和本批案例；这不表示339项均经重新历史认证。'),
        ('02  引文与概述','G15已补正文原句并保存前后读法。下一批优先逐条核引文、删节与夹注边界，避免概述再次进入原句字段。'),
        ('03  图号与接合表','优先取得1931河南五万分一接合表，并由系列目录追到具体图号、版记和馆藏原件。目录编号不是历史图号。'),
        ('04  单一地物连续性','历史11号桥墩遭毁的记录已单列；修复通车不证明原构件、基础和墩位连续存续，须另核工程档案。'),
        ('05  古今位置与时层','原纸图水平基准仍未知，地面控制点0；图内格网校准不替代地面核查，古河道仍须有年代证据。'),
        ('06  可下载的完整记录','本批339项CSV/JSON、14例审校、来源获取状态、图册和保存报告可共同复核；原B1—B7图件继续可查。')
    ]
    for i,(title,body) in enumerate(cards):
        x=75+(i%2)*1040;y=250+(i//2)*360
        rect(r,x,y,1010,325,'#edf1e6',C['line'],2,8)
        text(r,x+28,y+60,title,30,C['green'],weight=500)
        para(r,x+28,y+121,body,36,26)
    text(r,75,1410,'当前研究层：516—528河阴之变前的文献合成语境，非某一年的全城快照。',25,C['gold'])
    text(r,75,1470,'网页：https://mechgouki.github.io/luoyang-city/dual-city-review.html',24,C['muted'])
    text(r,75,1515,'B8 / 2026-11-14 / 新增历史原图0、古址坐标0、获准地面控制点0。',22,C['muted'])
    return r


def install_correction_notices(site,cases):
    c=next(c for c in cases['records'] if c.get('errata'))
    updates=[]
    items=[('dual-b2.html','dual-b2-before-b8.html','./'),
           ('downloads/dual-map-report.html','downloads/dual-map-report-before-b8.html','../')]
    for rel,archive,prefix in items:
        p=site/rel;old=p.read_bytes();(site/archive).write_bytes(old)
        notice=('<section id="b8-quotation-correction" style="margin:20px 4%;padding:18px;border:1px solid #bca479;background:#f2eddf;color:#294139;font:14px/1.8 system-ui,sans-serif">'
                '<strong>B8 引文更正 · B2 G15</strong><p>G15旧“原文”字段是压缩概述。本次已核周、范正文并补录准确原句；旧数据和旧图册作为历史记录保留。'
                '水路关系与古址坐标没有因此增补。</p><p><a href="'+prefix+'dual-city-review.html#view=cases&amp;case='+c['id']+'">查看原句、校注与更正依据</a>　'
                '<a href="'+Path(archive).name+'">查看加注前网页</a></p></section>')
        body=old.decode('utf-8');assert 'id="b8-quotation-correction"' not in body
        body,replacements=re.subn(r'(<body\b[^>]*>)',lambda m:m.group(1)+notice,body,count=1)
        if replacements==0:
            # The preserved B1+B2 report intentionally omits an explicit body tag.
            assert rel=='downloads/dual-map-report.html'
            start=re.search(r'<h1\b',body)
            assert start and '</style>' in body[:start.start()]
            body=body[:start.start()]+notice+body[start.start():]
        assert body.count('id="b8-quotation-correction"')==1
        assert body.replace(notice,'',1).encode('utf-8')==old
        p.write_text(body,encoding='utf-8')
        updates.append({'path':rel,'before_sha256':sha(site/archive),'archive_path':archive,
                        'after_sha256':sha(p),'reason':'B8 G15 quotation-layer correction notice; original data, maps and PDF retained',
                        'case_id':c['id']})
    return updates


def main():
    from source_access_b8 import build_review
    info=load(SITE/'build-info.json')
    assert info.get('luonan_b7',{}).get('records')==25
    assert not (SITE/'dual-city-review.html').exists(),'Rebuild preceding stages before B8'
    protected={str(p.relative_to(SITE)):sha(p) for p in SITE.rglob('*') if p.is_file() and str(p.relative_to(SITE)) not in MUTABLE}
    cases=read_cases();cases['baseline_commit']=cases.get('baseline_commit',cases.get('source_commit',BASE));cases['source_commit']=info['source_commit']
    ledger=enrich_ledger(build_audit(SITE,source_commit=info['source_commit']),cases)
    access=build_review(SITE,info['source_commit'])
    master,audit=changed_master(SITE/'assets/master-dual-b7-luonan.svg',ledger)
    master_file=SITE/'assets/master-dual-b8-review.svg';write_svg(master_file,master)
    out=SITE/'city-review';out.mkdir(exist_ok=True)
    dump(out/'ledger.json',ledger);dump(out/'cases.json',cases)
    errata={'source_commit':info['source_commit'],'baseline_commit':BASE,
            'records':[dict(c['errata'],case_id=c['id']) for c in cases['records'] if c.get('errata')],
            'original_research_data_preserved':True}
    dump(out/'errata.json',errata)
    write_svg(out/'overview.svg',overview_plate(master,ledger,cases))
    write_svg(out/'coverage.svg',coverage_plate(ledger))
    half=(len(cases['records'])+1)//2
    write_svg(out/'cases-1.svg',cases_plate(cases,cases['records'][:half],1))
    write_svg(out/'cases-2.svg',cases_plate(cases,cases['records'][half:],2))
    write_svg(out/'corrections.svg',corrections_plate(cases))
    write_svg(out/'reading-guide.svg',policy_plate(ledger,cases,access))
    plates=[out/'overview.svg',out/'coverage.svg',out/'cases-1.svg',out/'cases-2.svg',out/'corrections.svg',
            SITE/'source-access/access-summary.svg',SITE/'source-access/upstream-summary.svg',out/'reading-guide.svg']
    pdf=SITE/'downloads/luoyang-city-review-b8-atlas.pdf';render_atlas(plates,pdf)
    cairosvg.svg2png(url=str(out/'overview.svg'),write_to=str(out/'overview.png'),output_width=2400)
    csvfile=SITE/'downloads/luoyang-city-review-b8-ledger.csv'
    with csvfile.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['实体ID','图中编号','当前显示名','封存名录名','类型','交互关联','目标ID','显式分区名录','图幅命中','历批显式引用','v2.9事件','B8案例','封存时层字段','当前时层说明','基线出处','地理坐标'])
        for e in ledger['entities']:
            writer.writerow([e['id'],e['map_id'],e['display_name'],e['name'],e['type'],e['marker_state'],
                             ';'.join(t['id'] for t in e['targets']),';'.join(e['explicit_focus_regions']),';'.join(e['crop_regions']),
                             ';'.join(x['key'] for x in e['direct_evidence_refs']),';'.join(x['id'] for x in e['chronology_refs']),
                             ';'.join(e['case_ids']),e['legacy_temporal_state'],e['current_review'].get('temporal_label',''),
                             e.get('source_url',''),'未定位'])
    for dest,src in [('dual-city-review.html','city-review-b8.html'),('city-review-b8.js','city-review-b8.js')]:
        (SITE/dest).write_bytes((ROOT/'web'/src).read_bytes())
    corrections=install_correction_notices(SITE,cases)
    index=(SITE/'index.html').read_text()
    match=re.search(r'<script src="\./([^"]+-runtime\.js)"></script>',index);assert match
    boot=(SITE/match.group(1)).read_text();m=re.search(r'window\.ATLAS_ASSETS=(.*?);\n',boot);assert m
    mapping=json.loads(m.group(1));mapping['assets/master-v28-review.svg']=fp(master_file.name,master_file.read_bytes())
    boot=boot[:m.start(1)]+json.dumps(mapping,ensure_ascii=False)+boot[m.end(1):]
    index=index.replace(match.group(1),fp('runtime.js',boot.encode()),1)
    banner=('<section id="city-b8-entry" style="margin:16px 0;padding:23px;border:1px solid #c6b592;background:#f2eddf;border-radius:8px">'
            '<h2>全城总校核 · B8</h2><p>339项结构关联、14个跨批次审校案例与具体图源获取状态。G15补录准确原句，旧字段与当前解释分别显示。</p>'
            '<p><a href="./dual-city-review.html">进入全城审校 ↗</a>　<a href="./dual-city-review.html#view=sources">原图与来源追查 ↗</a>　'
            '<a href="./downloads/luoyang-city-review-b8-atlas.pdf">下载本批图册 ↗</a></p>'
            '<label style="font-size:13px"><input type="checkbox" id="b8-review-toggle" checked>显示主图审校阅读环（不表示遗址可信度）</label></section>')
    assert index.count('id="luonan-b7-entry"')==1
    index=index.replace('<section id="luonan-b7-entry"',banner+'<section id="luonan-b7-entry"',1)
    index=index.replace('<nav aria-label="主导航" class="topnav">','<nav aria-label="主导航" class="topnav"><a href="./dual-city-review.html">全城总校核 B8 ↗</a>',1)
    mainjs=fp('city-main-b8.js',(ROOT/'web/city-main-b8.js').read_bytes())
    index=index.replace('</body>',f'<script defer src="./{mainjs}"></script></body>')
    (SITE/'index.html').write_text(index);(SITE/'v3.0-dual.html').write_text(index)
    release=load(SITE/'release.json');release['extensions']=sorted(set(release.get('extensions',[])+['city-review-b8','source-access-b8']))
    release['current_milestone']='B8 全城总校核与具体原图获取追查';dump(SITE/'release.json',release)
    assert all(sha(SITE/p)==h for p,h in protected.items()),'B8 changed an undeclared protected resource'
    preservation={'protected_files':len(protected),'protected_unchanged':True,'sha256':protected,'intentional_html_updates':corrections,'drawing_audit':audit}
    dump(out/'preservation.json',preservation)
    outputs=['dual-city-review.html','city-review-b8.js','assets/master-dual-b8-review.svg',
             'city-review/ledger.json','city-review/cases.json','city-review/errata.json','city-review/preservation.json',
             'source-access/metadata.json','source-access/access-summary.svg','source-access/upstream-summary.svg',
             'city-review/overview.svg','city-review/overview.png','city-review/coverage.svg',
             'city-review/cases-1.svg','city-review/cases-2.svg','city-review/corrections.svg','city-review/reading-guide.svg',
             'downloads/luoyang-city-review-b8-atlas.pdf','downloads/luoyang-city-review-b8-ledger.csv',
             'downloads/luoyang-city-review-b8-package.zip','dual-b2-before-b8.html','downloads/dual-map-report-before-b8.html']
    meta={'version':'B8','source_commit':info['source_commit'],'baseline_commit':BASE,'counts':ledger['counts'],
          'case_count':len(cases['records']),'case_linked_entities':ledger['case_linked_entities'],'atlas_pages':8,
          'quotation_corrections':len(errata['records']),'display_override_entities':sum(bool(e['current_review']) for e in ledger['entities']),
          'drawing_audit':audit,'source_access_counts':access['review_counts'],'outputs':outputs,
          'new_ancient_coordinates':0,'new_interactive_targets':0,'historical_full_entity_revalidation_claimed':False,
          'original_master_retained':'assets/master-dual-b7-luonan.svg','intentional_html_updates':corrections,
          'protected_files':len(protected)}
    dump(out/'metadata.json',meta)
    with zipfile.ZipFile(SITE/'downloads/luoyang-city-review-b8-package.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.rglob('*'))+sorted((SITE/'source-access').rglob('*'))+[pdf,csvfile,master_file]:
            if p.is_file():z.write(p,p.relative_to(SITE))
        for rel in ['research/dual-b8/cross-batch-review.json','research/dual-b8/source-access.json',
                    'docs/cross-batch-b8-research.md','docs/source-access-b8-research.md','docs/city-review-b8-release-notes.md']:
            z.write(ROOT/rel,rel)
        z.writestr('README.txt','B8全城总校核。339项结构清单不等于339项全部历史确证；14案例另列。\n'
                   '全部古代地理坐标未定位。保留B7母图与旧字段；G15引文更正见errata.json。\n'
                   '精确构建由GitHub当前发布提交的.github/workflows/pages.yml复现；source_commit见metadata.json。\n')
    info['city_review_b8']={'source_commit':info['source_commit'],'entities':339,'targets':179,'case_count':len(cases['records']),
                           'case_linked_entities':ledger['case_linked_entities'],'atlas_pages':8,'new_ancient_coordinates':0,
                           'new_interactive_targets':0,'protected_files':len(protected),'quotation_corrections':len(errata['records']),
                           'targeted_entities':237,'no_interactive_target_entities':102}
    info['source_access_b8']={'source_commit':info['source_commit'],'metadata':'source-access/metadata.json','review_counts':access['review_counts'],
                             'approved_control_points':0,'project_registration_to_wgs84':False,'original_horizontal_datum':None}
    info['files_sha256']={str(p.relative_to(SITE)):sha(p) for p in sorted(SITE.rglob('*')) if p.is_file() and p.name!='build-info.json'}
    dump(SITE/'build-info.json',info)
    print('Built B8: 339 structural rows, 14 review cases, 179 retained targets, eight-page atlas;',len(protected),'prior resources protected')


if __name__=='__main__':
    main()
