"""Publish the illustration and two reproducible projections after the R4 atlas."""
import json
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image
from water_location_atlas import build as build_water_atlas
from homepage_artwork_v10 import publish as publish_homepage_artwork
from city_panorama_sima import compare, plate as sima_plate
from city_panorama_r5_contract import ATLAS, BASELINE, ENTRY, HOME, KEY, VERSION, before_r5, digest
from city_panorama_r5_page import BUNDLE, FILES, FOLDER, MANIFEST, PAGE, make_page
from city_panorama_r5_scene import CAMERAS, MODELS, project, svg
from prosperity_city_common_p470 import dump, load, sha

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"research/prosperity-r5"
ARCH="research/prosperity-v4/city-distribution-p451.json"
ATLAS_JSON="city-atlas/atlas.json"
STATIC=("panorama.webp","panorama-small.webp","panorama.css","panorama.js","palace-east.svg")


def scene_data(site):
    atlas=load(site/ATLAS_JSON);architecture=load(ROOT/ARCH)
    notes=load(SRC/"interpretation.json")
    scene={key:notes[key] for key in ("period","orientation","art_direction","sources")}
    scene.update(version="R5.3",r4_baseline=BASELINE,source_atlas=ATLAS_JSON,source_atlas_sha256=sha(site/ATLAS_JSON),
                 architecture_source=ARCH,architecture_sha256=sha(ROOT/ARCH),cameras=CAMERAS,
                 source_coordinate_space="06a original PDF points. x increases eastward on the sheet, y southward. Camera z is illustrative.",
                 projections={"perspective":"camera looks along decreasing y; rotate by pitch then apply focal length / depth",
                              "parallel":"two independent scales in x and y and a graphic z scale"},
                 elevation_ground_m=None,new_historical_coordinates=0,accepted_jianchun_control_pairs=0,
                 excluded_modern_features=[f["id"] for f in atlas["features"] if f["id"].startswith("geo-modern-")],
                 r4_location_counts=atlas["counts"]["levels"])
    fields=("id","label","source_id","source_historical_period","source_pdf_geometry","approximation","placement_note")
    scene["features"]=[{k:f[k] for k in fields} for f in atlas["features"] if f["id"] not in scene["excluded_modern_features"]]
    index={f["id"]:f for f in scene["features"]}
    models=[]
    for record in architecture["anchored_buildings"]:
        fid=record["feature_id"];model=MODELS[fid]
        assert record["id"]==model["id"] and record["measured_elevation_m"] is None
        x,y=index[fid]["source_pdf_geometry"]["coordinates"]
        item=dict(record,graphic_model=model,source_pdf_point=[x,y],note=notes["notes"][model["id"]])
        item["projected_ground_px"]={key:[round(v,4) for v in project(x,y,0,c)] for key,c in CAMERAS.items()}
        models.append(item)
    scene["models"]=models
    scene["sima_road"]=compare(load(SRC/"sima-road.json"),scene["features"])
    scene["east_palace"]=load(SRC/"palace-east.json")
    scene["image"]=load(SRC/"image-record.json")
    return scene


def build(site=ROOT/"_site"):
    info=load(site/"build-info.json");release=load(site/"release.json");folder=site/FOLDER;folder.mkdir(exist_ok=True)
    scene=scene_data(site)
    for name in STATIC:shutil.copyfile(SRC/name,folder/name)
    with Image.open(folder/"panorama.webp") as img:
        assert img.size==(scene["image"]["width"],scene["image"]["height"])
    plates={key:svg(scene,key) for key in CAMERAS}
    for key,plate in plates.items():(folder/(key+".svg")).write_text(plate)
    (folder/"sima-road.svg").write_text(sima_plate(scene["sima_road"]))
    dump(folder/"scene.json",scene)
    (site/PAGE).write_text(make_page(scene,plates))
    prior={}
    for path,marker in [(HOME,b'<p id="r4-atlas-entry">'),(ATLAS,b'</header>')]:
        original=(site/path).read_bytes()
        if ENTRY in original:original=before_r5(info,path,original)
        assert original.count(marker)==1
        prior[path]=digest(original)
        changed=original.replace(marker,ENTRY+marker,1)
        assert before_r5(info,path,changed)==original
        (site/path).write_bytes(changed)
    assets=[FOLDER+"/"+p for p in (*STATIC,"core.svg","city.svg","scene.json","sima-road.svg")]
    study=dict(version=VERSION,source_commit=info["source_commit"],page=PAGE,manifest=MANIFEST,bundle=BUNDLE,
               download_files=list(FILES),entry_predecessors=prior,files_sha256={p:sha(site/p) for p in assets},
               feature_count=len(scene["features"]),models=len(scene["models"]),artwork_status="published_for_review",
               approved_homepage_hero="panorama-approved-v9")
    dump(site/MANIFEST,study)
    with ZipFile(site/BUNDLE,"w",ZIP_DEFLATED) as z:
        z.writestr("index.html",make_page(scene,plates,offline=True))
        for p in [*assets,MANIFEST]:z.write(site/p,p)
    release["extensions"]=sorted(set(release["extensions"])|{VERSION})
    release[KEY+"_version"]=VERSION
    release["current_milestone"]="盛时 R5.3 · 司马门内道路"
    dump(site/"release.json",release)
    water_files=build_water_atlas(site)
    info["water_locations"]={"version":"1.0","page":water_files[0],"register_count":34,"regional_source_features":10}
    info[KEY]=study
    for p in [*water_files,*assets,MANIFEST,BUNDLE,PAGE,HOME,ATLAS,"release.json"]:info["files_sha256"][p]=sha(site/p)
    dump(site/"build-info.json",info)
    publish_homepage_artwork(site)
    return study


if __name__=="__main__":
    study=build();print(study["version"],study["feature_count"],study["models"])
