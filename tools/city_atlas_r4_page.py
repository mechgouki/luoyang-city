"""Render equivalent, linkable research records for online and offline reading."""
import json
from html import escape as esc

from city_atlas_r4_data import LEVELS, PERIODS, index
from city_atlas_r4_maps import LIVE, PAGE

FOLDER = "city-atlas"
GIT = "https://github.com/mechgouki/luoyang-city"
TOPICS = {"P470":"prosperity-city-common.html","P471":"prosperity-city-north.html","P472":"prosperity-city-west.html"}
DOWNLOADS = {
    "downloads/city-atlas.pdf":"总图图册 · 3页 PDF",
    "city-atlas/city.svg":"全城来源总图 · SVG", "city-atlas/core.svg":"内城详图 · SVG",
    "city-atlas/literary.svg":"全城文献平面 · SVG", "city-atlas/relations.svg":"十一片区关系板 · SVG",
    "city-atlas/qian.svg":"钱氏复原图独立读图 · SVG", "city-atlas/coverage.csv":"339 个对象覆盖表 · CSV",
    "city-atlas/basis.csv":"定位与水陆依据表 · CSV", "city-atlas/atlas.json":"全套可追溯数据 · JSON",
    "city-atlas/manifest.json":"文件校验清单 · JSON", "downloads/city-atlas.zip":"可离线使用的整套图件 · ZIP",
}


def a(url,label):
    return f'<a href="{esc(url)}">{esc(str(label))}</a>'


def links(prefix, ids, names=None):
    return " · ".join(a("#"+prefix+i, names.get(i,i) if names else i) for i in ids)


def line(title, content):
    return f"<p><strong>{esc(title)}</strong>　{content}</p>" if content else ""


def card(anchor,title,body,attrs="",style="card"):
    return (f'<details class="{style}" id="{esc(anchor)}" {attrs}><summary>{title}</summary>'
            f'<div class="in">{body}<p>{a("#"+anchor,"本条链接")}</p></div></details>')


def section_group(title,content,anchor):
    return f'<details class="panel" id="{anchor}"><summary>{esc(title)}</summary><div class="in">{content}</div></details>'


def evidence_cards(data, names):
    cards = []
    for r in data["records"]:
        source_links = " · ".join(a(s["retrieved_url"],s["declared_source_id"]+" "+
                         "、".join(p["line_start"]+"–"+p["line_end"] for p in s["segments"] if p.get("line_start") and p.get("line_end"))) for s in r["source_checks"])
        body = f'<blockquote>{esc(r["quote"])}</blockquote>'
        body += line("文本层",esc(r["text_layer"] or "旧表未单列，见出处与校读"))+line("校读",esc(r["reading"] or ""))
        for key,title in (("regional_reading","片区读法"),("period_scope","时期与适用范围"),("temporal_note","年代说明"),("limit","依据边界")):
            if r.get(key):
                body += line(title,esc(r[key]))
        for note in r["annotations"]:
            body += line(note["author"]+" · "+note["layer"],esc(note["quote"])+"　"+a(note["url"],note["locator"]))
        if r.get("variants"):
            body += line("异文"," · ".join(esc(v["source"]+" "+v["reading"]) for v in r["variants"]))
        body += line("原文位置", esc(str(r["locator"] or ""))+"　"+source_links)
        body += line("核读程度","原有人工语境复核" if r["manual_context_review"] else "已作电子追溯，人工语境栏为空")
        body += line("相关对象",links("entity-",r["affected_entity_ids"],names))
        cards.append(card("reading-"+r["key"],esc(r["key"]+"　"+r["title"]),body))
    return section_group("逐条校读 · 183 条","".join(cards),"readings")


def object_cards(data):
    names={e["id"]:e["name"] for e in data["entities"]}
    ref_names={f["id"]:f["label"] for f in data["features"]}
    lit=index(data["literal_targets"],"reference_key")
    region_names={r["region"]:r["label"] for r in data["regions"]}
    cards=[]
    for e in data["entities"]:
        groups=sorted(set(e["focus_regions"]+e["evidence_regions"])) or ["register"]
        search=" ".join(str(s) for s in (e["id"],e["map_id"],e["name"],e["source_name"],*e["aliases"]))
        attrs=(f'data-object="{e["id"]}" data-search="{esc(search)}" data-regions="{" ".join(groups)}" '
               f'data-period="{e["period"]}" data-level="{e["level"]}"')
        title=f'<strong>{esc(e["name"])}</strong> <small>{LEVELS[e["level"]]}</small>'
        body=line("对象",esc(e["map_id"]+" · "+e["id"]))+line("时期",esc(e["temporal_label"]))
        if e["review_note"]:
            body+=line("现行限定",esc(e["review_note"]))
        for c in e["chronology"]:
            body+=line("事件时层",esc(str(c["date"].get("label") or c["date"].get("year") or "")+" · "+str(c["scope"])+" · "+str(c["interpretation_limit"] or "")))
        body+=line("位置",esc(e["placement"]))+line("直接对应",links("feature-",e["feature_ids"],ref_names))
        body+=line("相关参照",links("feature-",e["context_features"],ref_names))
        body+=line("继续定位所需",esc(e["next_evidence"]))
        source=a(e["source_url"],e["source_ref"] or "名录所引来源") if e["source_url"] else esc(e["source_ref"] or "")
        body+=line("名录原引",esc(e["source_quote"] or "")+" "+source)
        body+=line("校读",links("reading-",e["evidence"]))+line("更正与解释",links("decision-",e["decisions"])+" "+links("case-",e["cases"]))
        body+=line("专题"," · ".join(a("./"+TOPICS[k],k) for k in e["current_topics"]))
        body+=line("片区阅读",links("region-",groups,region_names))
        if e["crop_regions"]:
            body+=line("旧画幅取景",esc("、".join(e["crop_regions"])+"（图面裁切索引）"))
        if e["literal_targets"]:
            targets=[esc(lit[k]["raw_target"])+" · "+esc(lit[k]["meaning"]) for k in e["literal_targets"]]
            body+=section_group("字面目标与判定（"+str(len(targets))+"）","<ul>"+"".join("<li>"+v+"</li>" for v in targets)+"</ul>","literal-"+e["id"])
        if e["constraints"]:
            items=[]
            for c in e["constraints"]:
                target=c.get("target_id") or c.get("target") or ""
                items.append(esc(str(c["relation"]))+" · "+esc(str(names.get(target,target)))+
                             ("　"+esc(str(c.get("source_quote") or c.get("basis") or c.get("evidence_kind") or ""))))
            body+=section_group("名录原约束（"+str(len(items))+"）","<ul>"+"".join("<li>"+v+"</li>" for v in items)+"</ul>","constraints-"+e["id"])
        body+=a("./prosperity.html#view=plan&entity="+e["id"],"在文献图中读此对象")
        cards.append(card("entity-"+e["id"],title,body,attrs))
    return '<div class="grid">'+"".join(cards)+"</div>"


def basis_cards(data,names):
    geometry=[]
    for f in data["features"]:
        approx=f["approximation"]
        body=line("来源",a(data["sources"][0]["url"]+"#page="+str(f["source_pages"][0]),"管理规划图06a · "+f["source_feature_code"]))
        body+=line("来源和年代",esc(f["source_period"]+"。"+f["source_historical_period"]))+line("图形含义",esc(f["placement_note"]))
        body+=line("读图尺度",f'展示容差 {approx["working_display_tolerance_m"]} 米。地面绝对精度未给。')
        body+=line("图形坐标","原绘PDF点坐标与西安1980经纬度并列存于数据。")
        body+=line("文献对象",links("entity-",[f["entity_id"]] if f.get("entity_id") else [],names))
        body+=line("只供参照",links("entity-",f.get("related_entity_ids",[]),names))
        geometry.append(card("feature-"+f["id"],esc(f["label"]),body))
    source=index(data["road_sources"])
    def refs(ids):
        def source_link(s):
            if "url" in s:
                return a(s["url"],s["title"])
            return a("./prosperity/"+s["path"].rsplit("/",1)[-1],s["title"])
        return " · ".join(source_link(source[k]) for k in ids)
    streams=[]
    for w in data["waters"]:
        b=w["basis"]
        body=line("旧编号依据",esc(b["relative_topology_note"]))+line("现行对应",esc(str(w["current_record"].get("状态",""))))
        body+=line("图段",links("channel-",w["current_refs"]))+line("参阅来源",refs(b["source_ids"]))
        if w.get("withdrawn_links"):
            body+=line("撤回的旧图段",esc("、".join(w["withdrawn_links"])))
        if b["existing_entity_id"] in names:
            body+=line("名录",links("entity-",[b["existing_entity_id"]],names))
        streams.append(card("water-"+w["id"],esc(w["id"]+"　"+w["name"]),body))
    roads=[]
    for r in data["roads"]:
        body=line("调查或来源图范围",esc(r["scope"]))+line("原报告量",esc(json.dumps(r["sourced_metrics"],ensure_ascii=False)) if r["sourced_metrics"] else "本项无独立量测值")
        body+=line("证据来源",refs(r["source_ids"]))
        if r["registered_source_feature_id"]:
            body+=line("对应图形",links("feature-",[r["registered_source_feature_id"]]))
        roads.append(card("road-"+r["id"],esc(r["id"]+"　"+r["name"]),body))
    channels=[]
    for r in data["water_relations"]:
        body=line("校读",esc(r["reading"] or ""))+line("时期与限制",esc(r["limit"]))+line("原典与图段",
            a("./"+r["page"],r["plate_title"])+" · "+" · ".join(a(s["url"],s["title"]) for s in r["sources"] if s.get("url")))
        channels.append(card("channel-"+r["ref"],esc(r["from_label"]+" → "+r["to_label"]+"　"+r["label"]),body))
    terrain=[card(s["id"],esc(s["title"]),line("时期",esc(s["temporal_scope"]))+line("空间",esc(s["spatial_scope"]))+
                 line("对布局的约束",esc(s["layout_implication"]))+a(s["source_url"],"原件页码 "+str(s["pdf_page"]))) for s in data["terrain"]]
    gaps=[card(g["id"],esc(g["label"]),line("缺口",esc(g["reason"]))+line("有效续查条件",esc(g["next_evidence"]))) for g in data["gaps"]]
    jc=data["jianchun"]
    gaps.append(card("jianchun-control","建春门原图与总图的共同控制",line("确认点对",str(jc["research_accounting"]["accepted_control_pairs"]))+
                     line("续查条件",esc(" ".join(jc["next_evidence_needed"])))+a("./prosperity-backbone-p469.html","原图核读与六项报告量")))
    excluded="".join(line(e["label"],esc(e["source_period"]+"。"+e["reason"])) for e in data["exclusions"])
    grouped=[("图06a的30项来源要素",geometry,"features"),("河湖与水工 · 34 项",streams,"water"),
             ("水路现行关系 · 100 段",channels,"channels"),("主干道调查与原图记录 · 21 项",roads,"roads"),
             ("地形与古河道的五条依据",terrain,"terrain"),("未定位置与续查条件",gaps,"gaps")]
    return "".join(section_group(title,"".join(cards),key) for title,cards,key in grouped)+section_group("分期排除的来源图遗存",excluded,"excluded")


def page(data,maps,commit):
    names={e["id"]:e["name"] for e in data["entities"]}
    regions=data["regions"]; counts=data["counts"]
    options=lambda vals: '<option value="">全部</option>'+"".join(f'<option value="{esc(k)}">{esc(v)}</option>' for k,v in vals.items())
    tabs={"city":"全城来源图","core":"内城详图","literary":"文献平面","relations":"片区关系","qian":"另一来源图框"}
    tabbar="".join(f'<a data-tab="{k}" href="#view-{k}">{v}</a>' for k,v in tabs.items())
    descriptions={"city":"外郭相关遗存范围留有断段。图中虚框标出内城详图的取景范围。",
        "core":"宫城北缘用候选范围填色。点击城门、道路或遗存线，查看来源原页、年代和定位精度。",
        "literary":"图上的位置表达文献关系。点选共享符号，可以查看同组的各个对象。手机可放大并横向浏览。",
        "relations":"十一片区各取一组有出处的关系。点对象看时期，点关系词看现行引文。",
        "qian":"钱国祥2018图一，见朱岩石2024图6。读数保留在该复原图像素坐标系，尚无可与图06a可靠配准的变换。"}
    plates=[]
    for k,v in tabs.items():
        graphic=maps[k] if k!="qian" else '<img src="./city-atlas/qian.svg" alt="钱氏复原图的南北道路、水带与外郭走廊读图"/>'
        plates.append(f'<article id="view-{k}" data-view="{k}"><h3>{v}</h3><p>{descriptions[k]}</p><figure id="plate-{k}" class="plate {k}" '+
            ('data-geoplate' if k in ('city','core') else '')+'>'+graphic+'</figure>'+
            f'<div class="toolbar js-only"><button type="button" class="btn" data-zoom="plate-{k}" aria-pressed="false">放大图面</button></div></article>')
    region_rows=[]
    for r in regions:
        example=(a("#reading-"+r["evidence"],r["relation"])+" · "+a("./"+r["topic"],"原专题")) if "evidence" in r else "按卷次、名称或对象编号查阅。"
        region_rows.append(f'<tr id="region-{r["region"]}"><th>{esc(r["label"])}</th><td>{len(r["entity_ids"])}</td><td>{example}</td>'+
                           f'<td><a data-filter-region="{r["region"]}" href="#members-{r["region"]}">查看本组</a></td></tr>')
    rosters="".join(card("members-"+r["region"],esc(r["label"]+" · 对象名单"),links("entity-",r["entity_ids"],names)) for r in regions)
    groups="".join(card("group-"+k,f"共享符号 {k}",links("entity-",ids,names)) for k,ids in data["targets"].items() if len(ids)>1)
    corrections="".join(card("decision-"+r["id"],esc(r["id"]+"　"+r["title"]),line("核读",esc(r["finding"]))+
               line("对图面的影响",esc(r["visual_instruction"]))+line("对应条目",links("reading-",r["evidence_keys"]))) for r in data["decisions"])
    cases="".join(card("case-"+r["id"],esc(r["id"]+"　"+r["short_title"]),line("校审",esc(r["finding"]))+
                       line("后续问题",esc(r["remaining_question"]))+links("entity-",r["entities"],names)) for r in data["cases"])
    exports="".join(f'<a download href="./{path}">{name}</a>' for path,name in DOWNLOADS.items())
    regions_opt=options({r["region"]:r["label"] for r in regions})
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>盛时洛阳 · 城市分布总图</title><link rel="stylesheet" href="./city-atlas/atlas.css"><script defer src="./city-atlas/atlas.js"></script></head>
<body><header><nav>{a("./","北魏洛阳文献地图")}<div class="links">{a("#objects","查对象")}{a("#basis","定位依据")}{a("#exports","下载图册")}</div></nav>
<h1>盛时洛阳城市分布总图</h1><p>从城墙、宫门与道路遗存，读到《洛阳伽蓝记》里的寺院、里坊和市场。全城 {counts['entities']} 个名录对象共用一套索引，可沿图面追到原文、年代与来源图页。</p>
<small>研究时层　516—528 年河阴事件前　·　统一图册 R4.1</small></header><main>
<section id="maps"><h2>城市图面</h2><div class="tabs">{tabbar}</div>
<div class="toolbar js-only" id="layer-tools"><label><span><input type="checkbox" id="candidate" checked> 宫城候选范围</span></label>
<label><span><input type="checkbox" id="modern"> 近现代洛水与邙山</span></label><button class="btn" id="export-view">下载当前图层 SVG</button></div>
{''.join(plates)}</section><section id="coverage"><h2>片区覆盖</h2>
<p class="section-intro">十一处片区按专题明确点名的对象和证据所涉对象编组。一个对象可跨组，单纯进入旧图裁切范围只另列说明。其余 {len(regions[-1]['entity_ids'])} 个名录对象单列。</p>
<div class="table-wrap"><table><thead><tr><th>阅读片区</th><th>对象数</th><th>关系与原专题</th><th>查看对象</th></tr></thead><tbody>{''.join(region_rows)}</tbody></table></div>
{section_group("各组对象名单",rosters,"rosters")}{section_group("文献平面上的共享符号",groups,"shared")}</section>
<section id="objects"><h2>对象索引</h2><p>直接对应来源图的有 {counts['levels']['source']} 个对象、{counts['direct_bindings']} 项绑定。候选范围 {counts['levels']['candidate']} 个，仅有文献相对关系 {counts['levels']['relative']} 个，位置未定 {counts['levels']['unlocated']} 个。后三类均无直接地理绑定。</p>
<div class="controls js-only" id="filter"><label>名称或编号<input id="q" type="search" placeholder="例如：永宁寺、T01"></label><label>片区<select id="region">{regions_opt}</select></label>
<label>位置依据<select id="level">{options(LEVELS)}</select></label><label>对象时期<select id="period">{options(PERIODS)}</select></label><button type="button" class="btn" id="reset">清除筛选</button></div>
<p class="count" id="matched" role="status">共 {counts['entities']} 个对象</p>{object_cards(data)}</section>
<section id="basis"><h2>位置与水陆依据</h2><p class="section-intro">原图保存各段的来源、时期、坐标框架和展示容差。古河岸、道路全程和古地面仍有缺口。河渠、城门与桥梁可查到具体的读图条件。</p>{basis_cards(data,names)}</section>
<section id="text"><h2>引文与校读</h2><p>183 条有电子文本追溯，其中 11 条另有人工作过语境复核。236 处字面目标逐项保存在对象卡与数据中；据以跳转对象时保留其原判定。</p>
{evidence_cards(data,names)}{section_group("读图更正与解释 · 11 项",corrections,"decisions")}{section_group("跨片区校审 · 14 例",cases,"cases")}</section>
<section id="exports"><h2>地图与数据下载</h2><p>离线包内可检索对象、切换图层、展开校读和查看图册。文献原站与历史专题的链接需要联网。</p><div class="grid downloads">{exports}</div></section>
</main><footer>{a(GIT+"/blob/"+commit+"/docs/city-atlas-r4.md","研究与版本说明")}　·　{a(GIT+"/commit/"+commit,"发布来源 "+commit[:12])}　·　{a("./prosperity-city-west.html","城西专题")}</footer></body></html>'''
