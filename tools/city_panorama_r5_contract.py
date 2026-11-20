"""Release identifiers and the reversible insertion into the two published entry points."""
import hashlib
import re

KEY="prosperity_city_panorama_r5"
VERSION="prosperity-city-panorama-r5.1"
BASELINE="1a7df53882eca40a44777b6e0717969a09f0f634"
HOME="index.html"
ATLAS="prosperity-city-atlas.html"
FINGERPRINTS={HOME:"56ef9a73b382863b6e7de427c56f2a132319de118fac4627db95bee8bac86ef3",
              ATLAS:"068059f596c7321e4a5ff4db77d6f60341214c73ba863b5957263c938e8fa5cc"}
ENTRY=('<p id="r5-panorama-entry"><a href="./prosperity-city-panorama.html"><strong>'
       '盛时洛阳全景 · 从永宁寺望向宫城 →</strong></a></p>\n').encode()


def digest(b):
    return hashlib.sha256(b).hexdigest()


def before_r5(info,path,content):
    assert content.count(ENTRY)==1,path
    original=content.replace(ENTRY,b"")
    if KEY in info:
        assert digest(original)==info[KEY]["entry_predecessors"][path]
    if path==HOME:
        runtime,=re.findall(rb'<script src="\./(_assets/[0-9a-f]{20}-runtime.js)"',original)
        baseline=original.replace(runtime,b"_assets/55037b42abb3a1401f13-runtime.js")
    else:
        commit=info["source_commit"].encode()
        assert commit in original
        baseline=original.replace(commit,BASELINE.encode()).replace(commit[:12],BASELINE[:12].encode())
    assert digest(baseline)==FINGERPRINTS[path],path
    return original
