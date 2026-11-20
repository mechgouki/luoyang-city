"""Two oblique views projected from the published 06a PDF coordinates."""
from html import escape
from math import cos, radians, sin

WIDTH, HEIGHT = 1600, 950
CAMERAS = {
    "core": {"mode":"perspective", "eye":[319,444,43], "pitch_deg":20, "focal_px":1350,
             "principal_px":[820,580], "south_clip_pdf_y":408, "viewbox":[0,0,WIDTH,HEIGHT]},
    "city": {"mode":"parallel", "origin":[319,355], "scale_x":3.18, "scale_y":1.99,
             "scale_z":3, "principal_px":[800,422], "viewbox":[0,0,WIDTH,HEIGHT]},
}
# Model dimensions are graphic units, independent of the archaeological measurement register.
MODELS = {
    "geo-changhe-palace-gate": {"id":"C01","kind":"gate","size":[5.2,1.9,1.45]},
    "geo-jianchun-gate": {"id":"C02","kind":"gate","size":[1.3,2.1,1.1]},
    "geo-taiji-hall-reference": {"id":"C03","kind":"hall","size":[7.6,3.8,2.5]},
    "geo-yongning-pagoda-reference": {"id":"C04","kind":"pagoda","size":[3.25,3.25,8.2]},
}
R4="prosperity-city-atlas.html"
BASE="https://mechgouki.github.io/luoyang-city/"
PALETTE={"wall":"#826f4f","buried":"#aea08a","road":"#b38b55","outer":"#a59272",
         "temple":"#806d48","gate":"#346861","candidate":"#d9cba9"}


def project(x,y,z,c):
    px,py=c["principal_px"]
    if c["mode"]=="parallel":
        ox,oy=c["origin"]
        return px+(x-ox)*c["scale_x"],py+(y-oy)*c["scale_y"]-z*c["scale_z"]
    ex,ey,ez=c["eye"]
    a=radians(c["pitch_deg"]); north=ey-y; up=z-ez
    depth=north*cos(a)-up*sin(a)
    return px+c["focal_px"]*(x-ex)/depth,py-c["focal_px"]*(north*sin(a)+up*cos(a))/depth


def category(fid):
    if fid=="geo-palace-layout-envelope":return "candidate"
    if fid=="geo-outer-city-related-remains":return "outer"
    if "road-" in fid or "tongtuo-" in fid:return "road"
    if "underground" in fid:return "buried"
    if fid=="geo-yongning-temple-walls":return "temple"
    if "wall" in fid:return "wall"
    return "gate"


def poly(points,color):
    value=" ".join(f"{x:.2f},{y:.2f}" for x,y in points)
    return f'<polygon points="{value}" fill="{color}" stroke="none"/>'


def solid(x,y,w,d,z,h,c,roof=False):
    def shape(box,level):
        return [project(x+u*box[0],y+v*box[1],level,c) for u,v in [(-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5)]]
    lo=shape((w,d),z); hi=shape((w*(.59 if roof else 1),d*(.15 if roof else 1)),z+h)
    shades=["#697575","#465b5d","#506566","#627474"] if roof else ["#e1c599","#a38966","#ba9c72","#cdb18a"]
    out=[]
    for i in [0,3,1,2]:
        k=(i+1)%4; out.append(poly([lo[i],lo[k],hi[k],hi[i]],shades[i]))
    out.append(poly(hi,"#677977" if roof else "#d9caa8"))
    return "".join(out)


def mass(fid,x,y,c):
    m=MODELS[fid];w,d,h=m["size"]
    if m["kind"]=="pagoda":
        parts=[solid(x,y,w*1.08,d*1.08,0,h*.06,c)]
        for i in range(9):
            taper=1-.068*i; z=h*(.06+i*.098)
            parts.extend([solid(x,y,w*taper*.78,d*taper*.78,z,h*.064,c),
                          solid(x,y,w*taper,d*taper,z+h*.063,h*.034,c,True)])
        parts.append(solid(x,y,w*.055,d*.055,h*.94,h*.06,c))
        return "".join(parts)
    def pavilion(cx,cy,wide,deep,height):
        return (solid(cx,cy,wide*1.06,deep*1.06,0,height*.15,c)
                +solid(cx,cy,wide*.84,deep*.84,height*.15,height*.47,c)
                +solid(cx,cy,wide,deep,height*.62,height*.38,c,True))
    if m["id"]=="C01":
        return pavilion(x,y,w*.45,d,h)+pavilion(x-w*.4,y+.28,w*.19,d*.67,h*1.12)+pavilion(x+w*.4,y+.28,w*.19,d*.67,h*1.12)
    return pavilion(x,y,w,d,h)


def clipped_segments(line,limit):
    if limit is None:return [line]
    result=[]; part=[]
    for p,q in zip(line,line[1:]):
        pin,qin=p[1]<=limit,q[1]<=limit
        if pin and not part:part=[p]
        if pin!=qin:
            t=(limit-p[1])/(q[1]-p[1]); cross=[p[0]+t*(q[0]-p[0]),limit]
            if pin:part.append(cross);result.append(part);part=[]
            else:part=[cross]
        if qin:part.append(q)
    if len(part)>1:result.append(part)
    return result


def svg(scene,view):
    c=scene["cameras"][view]; parts=[]
    def node(feature,body):
        fid=feature["id"]
        return f'<a href="{BASE}{R4}#feature-{fid}" data-feature="{fid}" aria-label="{escape(feature["label"],quote=True)}"><title>{escape(feature["label"])}</title>{body}</a>'
    order=sorted(scene["features"],key=lambda f:({"candidate":0,"outer":1,"road":2,"buried":3}.get(category(f["id"]),4)))
    points=[]
    for f in order:
        fid=f["id"];g=f["source_pdf_geometry"];pts=g["coordinates"];layer=category(fid);color=PALETTE[layer]
        if g["type"]=="Point":
            points.append((pts[1],f));continue
        if layer=="candidate":
            parts.append(node(f,poly([project(x,y,0,c) for x,y in pts[0]],color)));continue
        chunks=[]
        for line in pts:
            for section in clipped_segments(line,c.get("south_clip_pdf_y")):
                coords=[project(x,y,0,c) for x,y in section]
                path=" ".join(("M" if i==0 else "L")+f"{x:.2f},{y:.2f}" for i,(x,y) in enumerate(coords))
                if layer in ("wall","temple") and view=="core":
                    raised=[project(x,y,.35,c) for x,y in section]
                    chunks.append(poly(coords+raised[::-1],"#b7a381"))
                pen={"wall":2.4,"temple":2.2,"road":3.3,"outer":1.3,"buried":1.4}[layer]
                dash=' stroke-dasharray="4 4"' if layer=="buried" else ""
                chunks.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{pen}"{dash}/>')
        parts.append(node(f,"".join(chunks)))
    for _,f in sorted(points,key=lambda p:p[0]):
        fid=f["id"];x,y=f["source_pdf_geometry"]["coordinates"];px,py=project(x,y,0,c)
        ground=f'<circle cx="{px:.2f}" cy="{py:.2f}" r="{3.8 if view=="core" else 2.8}" fill="#376e66" stroke="#f8f5ec" stroke-width="1"/>'
        vol=mass(fid,x,y,c) if fid in MODELS else ""
        parts.append(node(f,ground+vol))
    titles={"C01":"宫前阊阖门","C02":"建春门","C03":"太极殿","C04":"永宁寺塔"}
    for _,f in points:
        m=MODELS.get(f["id"])
        if not m:continue
        x,y=f["source_pdf_geometry"]["coordinates"];px,py=project(x,y,0,c)
        dx,dy={"C01":(-24,23),"C02":(18,-9),"C03":(-22,-30),"C04":(-25,34)}[m["id"]]
        end="end" if dx<0 else "start"
        # Include the leader's empty space in the hit target as well as the glyphs.
        label_width=20*len(titles[m["id"]])+6
        edge=px+dx-label_width if dx<0 else px+dx+label_width
        left,right=sorted((px,edge))
        top,bottom=min(py,py+dy-21),max(py,py+dy+5)
        hit=(f'<rect x="{left-2:.2f}" y="{top-2:.2f}" width="{right-left+4:.2f}" '
             f'height="{bottom-top+4:.2f}" fill="transparent" pointer-events="all"/>')
        label=(hit+f'<path d="M{px:.2f},{py:.2f} l{dx},{dy}" stroke="#4a6259" fill="none" stroke-width="1"/>'
               f'<text x="{px+dx:.2f}" y="{py+dy:.2f}" text-anchor="{end}" fill="#21493d" '
               f'stroke="#f1ecdf" stroke-width="5" paint-order="stroke" font-family="sans-serif" font-size="18">{titles[m["id"]]}</text>')
        parts.append(f'<a href="{BASE}{R4}#feature-{f["id"]}" data-label="{m["id"]}">{label}</a>')
    name="宫寺核心" if view=="core" else "全城"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="盛时洛阳{name}布局体量图">'
            f'<title>{name} · 图06a原顶点投影</title><rect width="100%" height="100%" fill="#f1ecdf" pointer-events="none"/>'
            +'<g stroke-linejoin="round" stroke-linecap="round">'+"".join(parts)+'</g></svg>\n')
