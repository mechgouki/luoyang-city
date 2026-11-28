#!/usr/bin/env python3
"""Validate the approved full-frame image at both entrances and four screen widths."""
import argparse
import functools
import hashlib
import http.server
import json
import os
import tempfile
import threading
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument("--base-url")
parser.add_argument("--output",default="artifacts/homepage-approved-v9-browser")
args=parser.parse_args()
out=ROOT/args.output
out.mkdir(parents=True,exist_ok=True)
server=None
temporary=None
checks=[]
errors=[]
report={"schema":"luoyang-homepage-full-frame", "status":"running",
        "checks":checks, "errors":errors, "layouts":[], "screenshots":{}, "asset_sha256":{}}
active_page=None
if args.base_url:
    base=args.base_url.rstrip("/")+"/"
else:
    temporary=tempfile.TemporaryDirectory()
    folder=Path(temporary.name)
    (folder/"luoyang-city").symlink_to(ROOT/"_site",target_is_directory=True)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*unused):pass
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),
      functools.partial(Quiet,directory=folder))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}/luoyang-city/"

def ok(name):
    checks.append(name)
    print("PASS",name,flush=True)
def no_overflow(page):
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
def ready(page):
    page.wait_for_function("document.documentElement.dataset.homepageReady==='true'")

def checksum(raw):
    return hashlib.sha256(raw).hexdigest()

def screenshot(target, name):
    raw=target.screenshot(path=str(out/name), animations="disabled")
    report["screenshots"][name]=checksum(raw)

def full_frame_layout(page):
    geometry=page.evaluate("""() => {
        const image=document.querySelector('#home-hero img');
        const caption=document.querySelector('#home-hero figcaption');
        const copy=document.querySelector('#home-hero .home-hero-copy');
        const rect=node => {
            const r=node.getBoundingClientRect();
            return {top:r.top,bottom:r.bottom,left:r.left,right:r.right,width:r.width,height:r.height};
        };
        return {image:rect(image),caption:rect(caption),copy:rect(copy),
                object_fit:getComputedStyle(image).objectFit,
                current_source:image.currentSrc,natural_width:image.naturalWidth,natural_height:image.naturalHeight};
    }""")
    image=geometry["image"]
    assert geometry["object_fit"]=="contain",geometry
    assert abs(image["height"]-image["width"]*geometry["natural_height"]/geometry["natural_width"])<=1,geometry
    assert image["left"]>=-1 and image["right"]<=page.viewport_size["width"]+1,geometry
    assert image["width"]>=page.viewport_size["width"]*.75,geometry
    assert geometry["caption"]["top"]>=image["bottom"]-1,geometry
    assert geometry["copy"]["top"]>=image["bottom"]-1,geometry
    assert geometry["caption"]["height"]>0 and geometry["copy"]["height"]>0,geometry
    no_overflow(page)
    return geometry

try:
    with sync_playwright() as pw:
        opts={"headless":True}
        if os.environ.get("CHROMIUM_PATH"):
            opts["executable_path"]=os.environ["CHROMIUM_PATH"]
        browser=pw.chromium.launch(**opts)
        with browser.new_context() as metadata_context:
            def get_json(path):
                response=metadata_context.request.get(base+path)
                assert response.status==200,path
                return response.json()
            info=get_json("build-info.json")
            v12=get_json("homepage/approval-v12.json")
            legacy=v12["hero"]
            assert v12["source_commit"]==info["source_commit"]
            previous_approval=get_json(v12["previous_metadata"])
            previous=previous_approval["hero"]
            assert previous["revision"]==v12["previous_revision"]=="panorama-approved-v11"
            assert previous["selection_number"]=="07"
            assert previous["source_sha256"]=="4d45e831b59f2f7550fe7129455f1da823098e8f34cf633223cd584d5b64a5bf"
            earlier=get_json(previous_approval["previous_metadata"])["hero"]
            assert earlier["revision"]=="panorama-approved-v10"
            assert earlier["source_sha256"]=="262e0797c09788f7871bca81c05d5e2c15d5ebc7ab8cf6c559ced68cf883a41e"
            old=get_json("homepage/history/panorama-interim-v8.json")
            assert old["hero"]["revision"]=="panorama-interim-v8"
            assert legacy["revision"]=="panorama-approved-v12" and legacy["status"]=="approved"
            assert legacy["selection_label"]=="全幅取景版" and legacy["display_mode"]=="full_frame"
            assert legacy["based_on_revision"]==previous["revision"]
            assert legacy["source_sha256"]=="c7954dfc3ee659de756c62d0f634e40eddfd2ecc93cc8b833f53f6c0e0dc69ca"
            assert legacy["approval_date"]=="2026-11-21"
            current_home=info.get("homepage_yongning_v15")
            approval=get_json(current_home["metadata"]) if current_home else v12
            h=approval["hero"]
            assert approval["source_commit"]==info["source_commit"]
            assert h["status"]=="approved"
            if current_home:
                assert h["revision"]==current_home["hero_revision"]=="panorama-yongning-v15"
                assert h["approval_date"]=="2026-11-28"
            else:
                assert h["revision"]=="panorama-approved-v12"
            report.update(source_commit=info["source_commit"],hero_revision=h["revision"],source_sha256=h["source_sha256"],
                          source_kind=h.get("source_kind", "approved_source_png"),
                          preserved_v12_revision=legacy["revision"],preserved_v12_source_png_sha256=legacy["source_sha256"])
            for artwork in [legacy]+([h] if current_home else []):
                for asset_key,sha_key in (("asset","asset_sha256"),("small_asset","small_asset_sha256")):
                    asset=artwork[asset_key]
                    response=metadata_context.request.get(base+asset)
                    assert response.status==200 and response.headers.get("content-type","").startswith("image/"),asset
                    actual=checksum(response.body())
                    assert actual==artwork[sha_key]==info["files_sha256"][asset],asset
                    report["asset_sha256"][asset]=actual
            for entry in ("index.html","v3.0-dual.html"):
                response=metadata_context.request.get(base+entry)
                assert response.status==200,entry
                raw=response.body()
                assert raw.count(f'data-hero-revision="{h["revision"]}"'.encode())==1
                assert h["asset"].encode() in raw and h["small_asset"].encode() in raw
                archived=metadata_context.request.get(base+"homepage/history/"+entry.replace(".html","-before-v12.html"))
                assert archived.status==200,entry
                assert b'data-hero-revision="panorama-approved-v11"' in archived.body()
                assert checksum(archived.body())==v12["previous_html_sha256"][entry]
            ok("Both homepage URLs use the current approved full-frame source; current and V12 WebP hashes, the V12 provenance chain and V11 archive remain verified")

        devices=(("desktop",1500,960),("wide",1920,1080),("tablet",768,1024),("mobile",390,844))
        for label,width,height in devices:
            is_mobile=label=="mobile"
            with browser.new_context(viewport={"width":width,"height":height},is_mobile=is_mobile,has_touch=is_mobile,
                                     reduced_motion="reduce",device_scale_factor=1) as context:
                page=context.new_page()
                active_page=page
                page.on("pageerror",lambda error:errors.append(str(error)))
                for entry,url in (("index",base),("dual",base+"v3.0-dual.html#home")):
                    response=page.goto(url,wait_until="networkidle")
                    assert response.status==200
                    ready(page)
                    image=page.locator("#home-hero img")
                    image.wait_for(state="visible")
                    expected_size=(h["small_width"],h["small_height"]) if is_mobile else (h["width"],h["height"])
                    expected_width=expected_size[0]
                    page.wait_for_function("width=>{const im=document.querySelector('#home-hero img');return im&&im.complete&&im.naturalWidth===width;}",arg=expected_width)
                    assert page.locator("#home-hero").get_attribute("data-hero-revision")==h["revision"]
                    assert image.get_attribute("src").endswith(h["asset"])
                    assert image.get_attribute("alt")==h["alt"]
                    expect(page.locator("#home-hero")).to_contain_text("研究性复原示意")
                    assert page.locator("#home-questions a[data-question]").count()==3
                    geometry=full_frame_layout(page)
                    assert (geometry["natural_width"],geometry["natural_height"])==expected_size
                    expected_asset=h["small_asset"] if is_mobile else h["asset"]
                    assert geometry["current_source"].endswith("/"+expected_asset),geometry
                    # Check the image response the page actually selected, in addition to the declared asset.
                    actual_image=context.request.get(geometry["current_source"])
                    assert actual_image.status==200
                    assert checksum(actual_image.body())==report["asset_sha256"][expected_asset]
                    suffix="" if entry=="index" else "-dual"
                    filename=f"approved-{label}{suffix}.png"
                    screenshot(page,filename)
                    report["layouts"].append(dict(device=label,entry=entry,viewport={"width":width,"height":height},
                                                  url=page.url,screenshot=filename,geometry=geometry))
                    if entry=="index" and label in ("desktop","mobile"):
                        screenshot(page.locator("#home-hero"),f"approved-{label}-full-hero.png")
                    ok(f"{width}px {entry} displays the entire panorama in proportion, with its title and caption below the image")
                    if is_mobile:
                        page.locator("#home-start").tap()
                        page.wait_for_function('location.hash === "#map"')
                        expect(page.locator("#home-hero")).to_be_hidden()
                        expect(page.locator("#map-viewport")).to_be_in_viewport()
                        no_overflow(page)
                        ok(f"390px {entry} opens the actual map from the full-frame homepage")
        with browser.new_context() as closing_context:
            ending=closing_context.request.get(base+"build-info.json")
            assert ending.status==200
            assert ending.json()["source_commit"]==info["source_commit"],"Deployment changed during homepage acceptance"
        assert not errors,errors
        report["status"]="passed"
        browser.close()
except Exception as error:
    report.update(status="failed",error=str(error))
    if active_page is not None and not active_page.is_closed():
        try:screenshot(active_page,"failure.png")
        except Exception:pass
    raise
finally:
    report["base_url"]=base
    (out/"results.json").write_text(json.dumps(report,
     ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if server:server.shutdown()
    if temporary:temporary.cleanup()
