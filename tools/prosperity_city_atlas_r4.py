"""Publish the integrated atlas after the R1 western study."""
import csv
import hashlib
import io
import json
import shutil
from zipfile import ZIP_DEFLATED, ZipFile

import cairosvg
from pypdf import PdfReader, PdfWriter

from city_atlas_r4_data import ROOT, SOURCES, build_data, subset
from city_atlas_r4_maps import LIVE, PAGE, literary_plate, markup, relationship_plate, source_plate
from city_atlas_r4_page import DOWNLOADS, FOLDER, page
from prosperity_anchors_p461 import offline_page
from prosperity_city_common_p470 import dump, load, sha

KEY = "prosperity_city_atlas_r4"
VERSION = "prosperity-city-atlas-r4.1"
PDF, ZIP, MANIFEST = "downloads/city-atlas.pdf", "downloads/city-atlas.zip", "city-atlas/manifest.json"
ASSETS = [p for p in DOWNLOADS if p not in (ZIP,MANIFEST)]+["city-atlas/atlas.css","city-atlas/atlas.js"]
WEST = "prosperity-city-west.html"
ARCHIVED_HOME = "homepage/history/index-before-r4.html"
ENTRY = '<p id="r4-atlas-entry"><a href="./prosperity-city-atlas.html"><strong>盛时洛阳城市分布总图 · 查阅全城对象与定位依据 →</strong></a></p>\n'
MARKERS = {"index.html":'<p id="core-scale-home-link">', WEST:'<section id="source">'}
COVERAGE = ("id","map_id","name","source_name","type","juan","level","period","temporal_label","temporal_state","review_note",
            "focus_regions","evidence_regions","crop_regions","current_topics","feature_ids","context_features","evidence","decisions",
            "cases","literal_targets","placement","location_reading_ref","next_evidence","source_ref","source_url","source_quote")
BASIS = ("id","kind","name","frame","period","meaning","scale_or_metrics","absolute_ground_accuracy_m","source","next_evidence")


def csv_file(path,fields,rows):
    with path.open("w", encoding="utf-8-sig",newline="") as f:
        out=csv.DictWriter(f,fieldnames=fields)
        out.writeheader()
        for row in rows:
            out.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in row.items()})


def bases(data):
    out=[]
    for f in data["features"]:
        app=f["approximation"]
        out.append(dict(id=f["id"],kind=f["layer"],name=f["label"],frame="06a-PDF / EPSG:4610",
            period=f["source_historical_period"],meaning=f["placement_note"],
            scale_or_metrics={"working_display_tolerance_m":app["working_display_tolerance_m"]},
            absolute_ground_accuracy_m=app["absolute_ground_accuracy_m"],source=f["source_id"]+" / "+str(f["source_pages"]),
            next_evidence="按原图图例、符号和时层复读；实址精化需独立控制。"))
    for w in data["waters"]:
        b=w["basis"]
        out.append(dict(id=w["id"],kind="water_register",name=w["name"],frame=w["geographic_frame"],period=b["period"],
            meaning=w["current_record"].get("状态","")+" "+b["relative_topology_note"],source=b["source_ids"],
            next_evidence="按现行图段核同层河槽、池岸与原测剖面。",scale_or_metrics=None))
    for r in data["roads"]:
        out.append(dict(id=r["id"],kind="road_register",name=r["name"],frame=r["registered_source_feature_id"],
            meaning=r["scope"],period=(r.get("sourced_metrics") or {}).get("phase") or "按原报告分层；全程同期未证。",
            scale_or_metrics=r["sourced_metrics"],source=r["source_ids"],next_evidence="需核有同层端点与共同控制的原测路线。"))
    for t in data["terrain"]:
        out.append(dict(id=t["id"],kind="terrain_evidence",name=t["title"],frame=None,period=t["temporal_scope"],meaning=t["layout_implication"],
            source=t["source_url"],next_evidence=t["limitations"]))
    for g in data["gaps"]:
        out.append(dict(id=g["id"],kind="gap",name=g["label"],frame=None,meaning=g["reason"],source="prosperity/geographic-evidence.json",
                        next_evidence=g["next_evidence"]))
    q=data["qian_frame"]
    out.append(dict(id=q["id"],kind="separate_source_frame",name="钱氏复原图独立读图",frame="image pixels",
        period="2018年复原图，2024年转载",meaning=q["use"],scale_or_metrics={"endpoints_px":q["scale_endpoints_px"],"represents_m":q["scale_represents_m"]},
        source=q["source"],next_evidence="跨图联测需独立同物控制与误差核验。"))
    return out


def annotate_entries(site,info):
    entries={}
    for path,marker in MARKERS.items():
        original=(site/path).read_text()
        prior=info.get(KEY,{}).get("entry_predecessors",{}).get(path,info["files_sha256"][path])
        original=original.replace(ENTRY,"")
        if hashlib.sha256(original.encode()).hexdigest()!=prior or marker not in original:
            raise ValueError("Review R4 entry on "+path)
        if path == "index.html":
            (site/ARCHIVED_HOME).write_text(original)
        (site/path).write_text(original.replace(marker,ENTRY+marker,1))
        entries[path]=prior
    return entries


def build(site=ROOT/"_site"):
    info,release=load(site/"build-info.json"),load(site/"release.json")
    commit=info["source_commit"]
    data=build_data(site)
    dest=site/FOLDER
    dest.mkdir(exist_ok=True)
    source=source_plate(data)
    core=source_plate(data,core=True)
    relations=relationship_plate(data)
    literary=literary_plate((site/"prosperity/literary-plan.svg").read_bytes())
    plates={k:markup(v) for k,v in {"city":source,"core":core,"relations":relations,"literary":literary}.items()}
    for name,svg in plates.items():
        (dest/(name+".svg")).write_text(svg+"\n")
    shutil.copyfile(site/"backbone-469/frame-qian2018.svg",dest/"qian.svg")
    for name in ("atlas.css","atlas.js"):
        shutil.copyfile(SOURCES/name,dest/name)
    writer=PdfWriter()
    for key in ("city","core","relations"):
        content=cairosvg.svg2pdf(bytestring=plates[key].encode())
        writer.add_page(PdfReader(io.BytesIO(content)).pages[0])
    writer.add_metadata({"/Title":"盛时洛阳城市分布总图","/Subject":"全城、内城与十一片区的文献关系"})
    with (site/PDF).open("wb") as f:
        writer.write(f)
    dump(dest/"atlas.json",data)
    csv_file(dest/"coverage.csv",COVERAGE,(subset(e,COVERAGE) for e in data["entities"]))
    csv_file(dest/"basis.csv",BASIS,bases(data))
    html=page(data,{k:v.replace(LIVE+"#","#") for k,v in plates.items()},commit)
    (site/PAGE).write_text(html)
    entries=annotate_entries(site,info)
    study={"version":VERSION,"source_commit":commit,"page":PAGE,"manifest":MANIFEST,"bundle":ZIP,
           "download_files":list(DOWNLOADS),"counts":data["counts"],"entry_predecessors":entries,
           "files_sha256":{p:sha(site/p) for p in ASSETS}}
    dump(site/MANIFEST,study)
    offline=offline_page(html,FOLDER,PDF)
    # In the offline edition the PDF keeps its original path. The ZIP link opens the published archive.
    with ZipFile(site/ZIP,"w",ZIP_DEFLATED) as z:
        z.writestr("index.html",offline)
        for p in (*ASSETS,MANIFEST):
            z.write(site/p,p)
    release["extensions"]=sorted(set(release["extensions"])|{VERSION})
    release[KEY+"_version"]=VERSION
    release["current_milestone"]="盛时 R4.1 · 洛阳城市分布总图"
    dump(site/"release.json",release)
    info[KEY]=study
    for p in (*ASSETS,MANIFEST,ZIP,PAGE,ARCHIVED_HOME,*MARKERS,"release.json"):
        info["files_sha256"][p]=sha(site/p)
    dump(site/"build-info.json",info)
    return study


if __name__=="__main__":
    print(build()["counts"])
