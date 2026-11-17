#!/usr/bin/env python3
"""H2: promote an explicitly approved Northern Wei panorama without touching historical maps.

Runs *after* H1 and all P4 studies. The H1 image, metadata and both full
HTML entry pages are archived verbatim; only the picture-source references,
accessible description and current publication metadata are updated.
"""
from pathlib import Path
import hashlib
import json
import re
from PIL import Image

from homepage_v1 import fingerprint, digest, dump

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"_site"
HISTORY=SITE/"homepage/history"
REVISION="panorama-approved-v9"
VERSION="homepage-approved-v9"
APPROVED_DATE="2026-11-17"
APPROVED_SOURCE="北魏洛阳盛景全景俯瞰.png"
APPROVED_SOURCE_SHA256="2a59bf83886d77f7c9226ec7f5d99c94ea6c63c6e207c2e560ee82f80ed93891"
FULL=ROOT/"web/assets/luoyang-panorama-approved-v9.webp"
SMALL=ROOT/"web/assets/luoyang-panorama-approved-v9-small.webp"
FULL_SHA256="6465657667ba740d3fc99cde2495a864d3a8a446e2086c25984c0c547eed5825"
SMALL_SHA256="98459529d0a2d8210aaf2728b0c1673ca38b46df2f7b761c9064f1c21fe053b6"
OLD_REVISION="panorama-interim-v8"
EXCEPTIONS={"index.html","v3.0-dual.html","homepage/metadata.json","release.json","build-info.json"}

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def require(cond,msg):
    if not cond:
        raise ValueError(msg)

def update_hero_html(html,old,large,small):
    old_big="./"+old["asset"]
    old_small="./"+old["small_asset"]
    require(html.count('src="'+old_big+'"')==1,"Expected one currently published H1 hero image")
    require(html.count('srcset="'+old_small+'"')==1,"Expected one currently published H1 mobile source")
    require(html.count('id="home-hero" class="home-hero"')==1,"Missing H1 landmark")
    html=html.replace('srcset="'+old_small+'"','srcset="'+small+'"',1)
    html=html.replace('src="'+old_big+'"','src="'+large+'"',1)
    html=html.replace('id="home-hero" class="home-hero"',
                      'id="home-hero" class="home-hero" data-hero-revision="'+REVISION+'"',1)
    img=re.compile(r'(<img src="'+re.escape(large)+r'"[^>]*? alt=")([^"]*)(">)')
    new_alt=(
      "北魏洛阳盛时艺术复原全景：宫城大殿、礼仪道路、寺院高塔、街巷、市集与远山。"
      "建筑外观、古代河道及具体院墙位置包含研究性推定与艺术表现。"
    )
    html,n=img.subn(lambda m:m.group(1)+new_alt+m.group(3),html,count=1)
    require(n==1,"Failed to update accessible hero description")
    require('src="'+large+'"' in html and 'srcset="'+small+'"' in html,"Approved assets not referenced")
    require("研究性复原示意" in html,"Historical interpretation warning was lost")
    return html

def main():
    require(FULL.is_file() and SMALL.is_file(),"Missing approved WebP source assets")
    require(digest(FULL)==FULL_SHA256,"Full resolution approved WebP mismatch")
    require(digest(SMALL)==SMALL_SHA256,"Mobile approved WebP mismatch")
    with Image.open(FULL) as f,Image.open(SMALL) as s:
        require((f.size,s.size)==((1672,941),(960,540)),"Unexpected approved artwork dimensions")
        require(f.format==s.format=="WEBP","Approved assets must be WebP")
    info=load(SITE/"build-info.json")
    release=load(SITE/"release.json")
    current=load(SITE/"homepage/metadata.json")
    original=current["hero"]
    require(original["revision"]==OLD_REVISION and original["status"]=="interim",
            "H2 must follow the v8 interim H1 builder")
    require(original["source_sha256"]=="29427da12c869874f8ccd43749dd44f6a851cde8eddb643f31008088b2eeaa39",
            "Unexpected source of the original hero")
    require(info["homepage"]["hero_revision"]==OLD_REVISION,"Unexpected H1 metadata state")
    require(info["prosperity_architecture"]["version"]=="prosperity-architecture-p44",
            "Run P4.4 and the previous research milestones first")
    # All previous researched files, the prior WebPs and the original downloadable
    # source maps must remain byte-exact. Archive the old HTML *after* P4.4 finished
    # updating its links, so the archive represents the last actually published v8 view.
    protected={name:sha for name,sha in info["files_sha256"].items()
               if name not in EXCEPTIONS}
    require(all(digest(SITE/name)==sha for name,sha in protected.items()),
            "Pre-existing research or historical image changed")
    HISTORY.mkdir(parents=True,exist_ok=True)
    dump(HISTORY/"panorama-interim-v8.json",current)
    previous_html={}
    for name in ("index.html","v3.0-dual.html"):
        b=(SITE/name).read_bytes()
        previous_html[name]=hashlib.sha256(b).hexdigest()
        (HISTORY/(name.replace(".html","-before-v9.html"))).write_bytes(b)
    large=fingerprint("luoyang-panorama-approved-v9.webp",FULL.read_bytes())
    small=fingerprint("luoyang-panorama-approved-v9-small.webp",SMALL.read_bytes())
    for name in ("index.html","v3.0-dual.html"):
        path=SITE/name
        current_html=path.read_text(encoding="utf-8")
        next_html=update_hero_html(current_html,original,large,small)
        path.write_text(next_html,encoding="utf-8")
    # Preserve original H1 semantic fields and use a separate, explicitly
    # visual approval record. Approval does not upgrade archaeological evidence.
    hero=dict(original)
    hero.update({
        "asset":large.removeprefix("./"),
        "small_asset":small.removeprefix("./"),
        "width":1672,"height":941,
        "description":"用户批准的北魏洛阳盛时艺术全景；研究性复原示意",
        "revision":REVISION,
        "status":"approved",
        "visual_review":"approved_for_homepage",
        "publication_authorized":True,
        "approval_date":APPROVED_DATE,
        "approval_scope":"homepage_visual_only",
        "note":"2026-11-17明确同意作为网站首页主图；图中的河道、桥位、宫墙、屋顶、人口活动仅作研究综合与艺术表达，不是全城实测。",
        "source_name":APPROVED_SOURCE,
        "source_sha256":APPROVED_SOURCE_SHA256,
        "asset_sha256":FULL_SHA256,
        "small_asset_sha256":SMALL_SHA256,
        "conversion":"Pillow WebP quality 92; 1672×941 original framing; mobile 960×540 Lanczos; no crop or repaint",
        "generated_image":True,
        "measured_reconstruction":False,
        "previous_revision":OLD_REVISION,
        "previous_metadata_archive":"homepage/history/panorama-interim-v8.json",
        "historical_ground_truth_upgraded":False
    })
    current["hero"]=hero
    current["approved_hero_milestone"]=VERSION
    current["approved_hero_date"]=APPROVED_DATE
    dump(SITE/"homepage/metadata.json",current)
    approval={
        "version":VERSION,
        "source_commit":info["source_commit"],
        "approval_date":APPROVED_DATE,
        "scope":"homepage_visual_only",
        "source_name":APPROVED_SOURCE,
        "source_sha256":APPROVED_SOURCE_SHA256,
        "source_dimensions_px":[1672,941],
        "source_is_generated_illustration":True,
        "web_assets":{
          "full":{"path":large.removeprefix("./"),"dimensions_px":[1672,941],"sha256":FULL_SHA256},
          "mobile":{"path":small.removeprefix("./"),"dimensions_px":[960,540],"sha256":SMALL_SHA256}
        },
        "previous_revision":OLD_REVISION,
        "previous_metadata_archive":"homepage/history/panorama-interim-v8.json",
        "previous_html_sha256":previous_html,
        "original_artifact_archived_separately":True,
        "image_geographic_accuracy":"illustrative_unverified",
        "adds_ancient_geographic_control_points":0,
        "adds_reconstructed_roof_height_m":None,
        "changes_research_data":False,
        "changes_city_layout":False,
        "replaces_existing_homepage_hero_only":True
    }
    dump(SITE/"homepage/approval-v9.json",approval)
    require(all(digest(SITE/name)==sha for name,sha in protected.items()),
            "H2 modified a protected published research asset")
    dump(SITE/"homepage/approval-preservation-v9.json",{
        "version":VERSION,"source_commit":info["source_commit"],
        "protected_unchanged":True,"protected_files":len(protected),"sha256":protected,
        "intentionally_changed":sorted(EXCEPTIONS),
        "archived_previous_index_sha256":previous_html,
        "newly_added":["homepage/approval-v9.json","homepage/history/panorama-interim-v8.json",
                       "homepage/history/index-before-v9.html","homepage/history/v3.0-dual-before-v9.html",
                       large.removeprefix("./"),small.removeprefix("./")]
    })
    release["extensions"]=sorted(set(release.get("extensions",[]))|{VERSION})
    release["homepage_hero_revision"]=REVISION
    release["homepage_hero_status"]="approved"
    release["homepage_hero_approval_date"]=APPROVED_DATE
    release["current_milestone"]="H2：正式采用用户批准的盛时洛阳全景；P4.4研究数据不变"
    dump(SITE/"release.json",release)
    info["homepage"]["hero_revision"]=REVISION
    info["homepage"]["hero_status"]="approved"
    info["homepage"]["hero_source_sha256"]=APPROVED_SOURCE_SHA256
    info["homepage_approved_v9"]={
        "version":VERSION,"source_commit":info["source_commit"],
        "approval_date":APPROVED_DATE,
        "hero_status":"approved",
        "hero_revision":REVISION,
        "new_absolute_ancient_coordinates":0,
        "research_data_modified":False,
        "metadata":"homepage/approval-v9.json",
        "protected_files":len(protected)
    }
    info["files_sha256"]={
        str(p.relative_to(SITE)):digest(p)
        for p in sorted(SITE.rglob("*")) if p.is_file() and p.name!="build-info.json"
    }
    dump(SITE/"build-info.json",info)
    dump(ROOT/"artifacts/homepage-approved-v9-build.json",{
        "version":VERSION,"source_commit":info["source_commit"],
        "hero_revision":REVISION,"metadata":approval,
        "protected_files":len(protected)
    })
    print(f"H2: approved panorama {FULL.stat().st_size:,}B desktop + {SMALL.stat().st_size:,}B mobile; "
          f"preserved {len(protected)} historical/research files; legacy v8 archived.")

if __name__=="__main__":
    main()
