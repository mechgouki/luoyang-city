/* One source-local plane. Camera changes and labels never mutate feature data. */
(() => {
  'use strict';
  const dataNode = document.getElementById('plan-data');
  if (!dataNode) return;
  const data = JSON.parse(dataNode.textContent);
  const svg = document.getElementById('city-plan-map');
  const ns = 'http://www.w3.org/2000/svg';
  const features = new Map(data.features.map(f => [f.id, f]));
  const views = new Map(data.views.map(v => [v.id, v]));
  const labels = {source:'来源总图骨架', trace:'局部原图轮廓 · 候选接入', scale:'有据尺度片 · 位置含假定', candidate:'文献方位 · 候选点',palace:'2013宫城刊图 · 对照层'};
  const colors = {source:'#315f57', trace:'#815e92', scale:'#ad7134', candidate:'#be8446',palace:'#608198'};
  const selector = document.getElementById('view-select');
  const search = document.getElementById('map-search');
  const layerInputs = [...document.querySelectorAll('[data-layer-toggle]')];
  const bounds = feature => {
    const ps=[]; const walk=c=>{if(typeof c[0]==='number')ps.push(c);else c.forEach(walk);};
    walk(feature.geometry.coordinates);
    return [Math.min(...ps.map(p=>p[0])),Math.min(...ps.map(p=>p[1])),Math.max(...ps.map(p=>p[0])),Math.max(...ps.map(p=>p[1]))];
  };
  const vb = () => svg.getAttribute('viewBox').split(/\s+/).map(Number);
  const svgEl=(tag,attrs,text)=>{const e=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,String(v)));if(text!==undefined)e.textContent=text;return e;};
  const enabled = l => layerInputs.find(i=>i.dataset.layerToggle===l)?.checked !== false;
  let chosen=null;
  let initialBox=null;
  let repaintScheduled=false;
  function schedulePaint(){if(repaintScheduled)return;repaintScheduled=true;requestAnimationFrame(()=>{repaintScheduled=false;paint();});}
  function fitBox(box){
    let [x0,y0,x1,y1]=box;const rect=svg.getBoundingClientRect();const ratio=Math.max(rect.width,1)/Math.max(rect.height,1);
    let w=Math.max(x1-x0,45),h=Math.max(y1-y0,45);const cx=(x0+x1)/2,cy=(y0+y1)/2;
    if(w/h<ratio)w=h*ratio;else h=w/ratio;
    return [cx-w/2,-cy-h/2,w,h];
  }
  function setCamera(box){svg.setAttribute('viewBox',box.join(' '));schedulePaint();}
  function setView(id,{save=true}={}){
    const v=views.get(id)||views.get('all');selector.value=v.id;
    if(save){chosen=null;document.getElementById('selected-title').textContent='选择一个构件';document.getElementById('selected-layer').textContent='当前显示所选取景；点选轮廓或名称可回查依据。';document.getElementById('selected-evidence').replaceChildren(textElement('p','所有视窗使用同一几何；图层和名称开关可继续使用。'));}
    const palaceToggle=layerInputs.find(i=>i.dataset.layerToggle==='palace');
    if(palaceToggle&&save&&v.id==='palace2013')palaceToggle.checked=true;
    const next=fitBox(v.bbox);initialBox=next.slice();setCamera(next);
    document.getElementById('view-note').textContent=v.subtitle||'同一母图的取景；片区窗口不是历史边界。';
    if(save)saveState();
  }
  function saveState(){
    if(location.protocol==='file:')return;
    const url=new URL(location.href);url.searchParams.set('view',selector.value);
    if(search.value.trim())url.searchParams.set('q',search.value.trim());else url.searchParams.delete('q');
    if(chosen)url.searchParams.set('feature',chosen);else url.searchParams.delete('feature');
    const active=layerInputs.filter(i=>i.checked).map(i=>i.dataset.layerToggle).join(',');url.searchParams.set('layers',active);
    history.replaceState(null,'',url);
  }
  function paint(){
    const [x,y,w,h]=vb(),rect=svg.getBoundingClientRect();const unit=w/Math.max(rect.width,1);
    svg.querySelectorAll('[data-screen-symbol]').forEach(e=>e.setAttribute('transform',`scale(${unit})`));
    svg.querySelectorAll('[data-stroke-px]').forEach(e=>{
      e.setAttribute('stroke-width',Number(e.dataset.strokePx)*unit);
      if(e.dataset.dashPx)e.setAttribute('stroke-dasharray',e.dataset.dashPx.split(' ').map(n=>Number(n)*unit).join(' '));
    });
    svg.querySelectorAll('[data-feature-id]').forEach(e=>{
      const f=features.get(e.dataset.featureId);
      e.style.display=enabled(e.dataset.layer)&&(f.default_visible!==false||f.layer==='palace')?'':'none';
      e.classList.toggle('is-selected',e.dataset.featureId===chosen);
    });
    let group=svg.querySelector('[data-annotation-layer="labels"]');if(group)group.remove();
    group=svgEl('g',{'data-annotation-layer':'labels','aria-hidden':'true'});svg.appendChild(group);
    const occupied=[]; const show=document.getElementById('label-toggle').checked;
    if(show){
      const available=data.features.filter(f=>f.geometry&&(f.default_visible!==false||f.layer==='palace')&&enabled(f.layer));
      available.sort((a,b)=>{
        const rank=f=>f.id===chosen?-1:f.layer==='source'&&f.geometry.type==='Point'?0:f.layer==='trace'?1:f.layer==='scale'?2:3;
        return rank(a)-rank(b)||(a.label||'').length-(b.label||'').length||a.id.localeCompare(b.id);
      });
      for(const f of available){
        if(f.geometry.type!=='Point'&&f.layer==='source')continue;
        if(w>2500&&['trace','scale'].includes(f.layer)&&f.id!==chosen)continue;
        const b=bounds(f),ax=(b[0]+b[2])/2,ay=-(b[1]+b[3])/2;
        if(ax<x||ax>x+w||ay<y||ay>y+h)continue;
        let label=f.label||f.id;if(label.length>21)label=label.slice(0,20)+'…';
        const fs=13,tw=Array.from(label).reduce((s,c)=>s+(c.charCodeAt(0)>127?fs:fs*.57),0),ap=(ax-x)/unit,bp=(ay-y)/unit;
        const options=[[ap+10,bp-7],[ap+10,bp+19],[ap-tw-10,bp-7],[ap-tw-10,bp+19],[ap+10,bp-30],[ap+10,bp+42],[ap-tw-10,bp-30],[ap-tw-10,bp+42]];
        let best=null;
        for(let [tx,ty]of options){tx=Math.max(6,Math.min(rect.width-tw-6,tx));ty=Math.max(21,Math.min(rect.height-6,ty));const r=[tx-3,ty-fs-2,tx+tw+3,ty+4];const overlap=occupied.reduce((s,o)=>s+Math.max(0,Math.min(r[2],o[2])-Math.max(r[0],o[0]))*Math.max(0,Math.min(r[3],o[3])-Math.max(r[1],o[1])),0);const score=overlap*100+Math.abs(tx-ap)+Math.abs(ty-bp);if(!best||score<best.score)best={score,tx,ty,r,overlap};}
        if(best.overlap>0&&f.id!==chosen)continue;
        occupied.push(best.r);const wx=x+best.tx*unit,wy=y+best.ty*unit;
        const g=svgEl('g',{'data-label-for':f.id,'data-layer':f.layer});
        if(Math.abs(best.ty-bp)>22||best.tx<ap)g.appendChild(svgEl('path',{d:`M${ax} ${ay}L${wx+Math.min(Math.max(ap-best.tx,0),tw)*unit} ${wy-5*unit}`,stroke:colors[f.layer],'stroke-width':.65*unit,fill:'none'}));
        g.appendChild(svgEl('rect',{x:wx-3*unit,y:wy-(fs+2)*unit,width:(tw+6)*unit,height:(fs+6)*unit,rx:2*unit,fill:'#faf9f4','fill-opacity':.95}));
        g.appendChild(svgEl('text',{x:wx,y:wy,'font-size':fs*unit,fill:colors[f.layer]},label));group.appendChild(g);
      }
    }
    const distance=w>5000?1000:w>2500?500:w>1000?200:w>400?100:20;
    document.getElementById('map-scale').textContent=`当前视宽约 ${Math.round(w)} m · 格网为来源坐标参考`;
    svg.dataset.visibleWidthM=w.toFixed(3);
    svg.dataset.labelCount=String(occupied.length);
  }
  function textElement(tag,value,className){const e=document.createElement(tag);e.textContent=value;if(className)e.className=className;return e;}
  function selectFeature(id,{zoom=false}={}){
    const f=features.get(id);if(!f)return;chosen=id;
    const heading=document.getElementById('selected-title');heading.textContent=f.label||id;
    document.getElementById('selected-layer').textContent=labels[f.layer];
    const body=document.getElementById('selected-evidence');body.replaceChildren();
    const limits=f.limits||[];if(limits.length){const ul=document.createElement('ul');limits.forEach(s=>ul.appendChild(textElement('li',typeof s==='string'?s:JSON.stringify(s))));body.appendChild(ul);}
    const p=document.createElement('p');const a=document.createElement('a');a.href='#feature-'+id;a.textContent='查看完整构件记录与来源';p.appendChild(a);body.appendChild(p);
    const box=bounds(f);
    const coordinateText=f.geometry.type==='Point'?`工作点 E ${box[0].toFixed(1)} / N ${box[1].toFixed(1)} m；该数值不新增考古定位精度。`:`几何包络 E ${box[0].toFixed(1)} 至 ${box[2].toFixed(1)} / N ${box[1].toFixed(1)} 至 ${box[3].toFixed(1)} m；包络不是院心、建筑中心或新的实测边界。`;
    body.appendChild(textElement('p',coordinateText,'coords'));
    const refs=f.source_refs||[];
    if(refs.length){const d=document.createElement('details');d.appendChild(textElement('summary','回查图源'));const ul=document.createElement('ul');ul.className='source-list';refs.forEach(ref=>{const li=document.createElement('li');const link=document.createElement('a');link.href=ref.url||`https://github.com/mechgouki/luoyang-city/blob/${data.source_commit}/${ref.path}`;link.textContent=ref.locator||ref.id||ref.path||'原始来源';link.rel='noopener';li.appendChild(link);if(ref.pointer)li.appendChild(textElement('code',ref.pointer));ul.appendChild(li);});d.appendChild(ul);body.appendChild(d);}
    if(zoom){const pad=f.geometry.type==='Point'?300:Math.max(30,(box[2]-box[0])*.3,(box[3]-box[1])*.3);setCamera(fitBox([box[0]-pad,box[1]-pad,box[2]+pad,box[3]+pad]));}
    if(!enabled(f.layer)){const input=layerInputs.find(i=>i.dataset.layerToggle===f.layer);if(input)input.checked=true;}
    schedulePaint();saveState();
  }
  svg.addEventListener('click',event=>{const link=event.target.closest('[data-feature-id],[data-label-for]');if(!link)return;event.preventDefault();selectFeature(link.dataset.featureId||link.dataset.labelFor);});
  document.querySelectorAll('[data-focus-feature]').forEach(button=>button.addEventListener('click',()=>{const f=features.get(button.dataset.focusFeature);selectFeature(button.dataset.focusFeature,{zoom:f.default_visible!==false||f.layer==='palace'});document.getElementById('plan-reader').scrollIntoView({block:'start'});}));
  document.querySelectorAll('[data-view-link]').forEach(link=>link.addEventListener('click',event=>{event.preventDefault();setView(link.dataset.viewLink);document.getElementById('plan-reader').scrollIntoView({block:'start'});}));
  selector.addEventListener('change',()=>setView(selector.value));
  layerInputs.forEach(i=>i.addEventListener('change',()=>{schedulePaint();saveState();}));
  document.getElementById('label-toggle').addEventListener('change',schedulePaint);
  document.querySelectorAll('[data-map-action]').forEach(b=>b.addEventListener('click',()=>{
    const action=b.dataset.mapAction;const [x,y,w,h]=vb();
    if(action==='reset'){setView(selector.value);return;}
    if(action==='in'||action==='out'){const factor=action==='in'?.67:1.5;const nw=Math.max(45,Math.min(42000,w*factor)),nh=h*nw/w;setCamera([x+(w-nw)/2,y+(h-nh)/2,nw,nh]);}
    else{const dx=action==='left'?-.22:action==='right'?.22:0,dy=action==='up'?-.22:action==='down'?.22:0;setCamera([x+dx*w,y+dy*h,w,h]);}
  }));
  document.getElementById('map-viewport').addEventListener('keydown',event=>{
    const action={ArrowLeft:'left',ArrowRight:'right',ArrowUp:'up',ArrowDown:'down','+':'in','=':'in','-':'out','0':'reset'}[event.key];
    if(action){event.preventDefault();document.querySelector(`[data-map-action="${action}"]`).click();}
  });
  function runSearch(){
    const query=search.value.trim().toLocaleLowerCase(),out=document.getElementById('search-results');out.replaceChildren();
    if(!query){saveState();return;}
    const matchedEntities=data.coverage.filter(e=>[e.name,e.source_name,e.main_scene_name,e.id].filter(Boolean).join(' ').toLocaleLowerCase().includes(query));
    const linked=new Set(matchedEntities.flatMap(e=>e.feature_ids||[]));
    const matches=data.features.filter(f=>linked.has(f.id)||(f.label+' '+f.id+' '+(f.entity_ids||[]).join(' ')).toLocaleLowerCase().includes(query));
    const entities=matchedEntities.filter(e=>!(e.feature_ids||[]).length);
    out.appendChild(textElement('p',`找到 ${matches.length} 个图上构件、${entities.length} 个未落位名录对象。`));
    matches.slice(0,24).forEach(f=>{const b=textElement('button',f.label);b.type='button';b.dataset.resultFeature=f.id;b.addEventListener('click',()=>selectFeature(f.id,{zoom:true}));out.appendChild(b);});
    entities.slice(0,15).forEach(e=>{const a=textElement('a',e.name+' · 名录');a.href='#entity-'+e.id;a.addEventListener('click',()=>{const fold=document.getElementById('coverage-fold');fold.open=true;document.getElementById('coverage-kind').value='all';document.getElementById('coverage-search').value=e.id;filterCoverage();});out.appendChild(a);});
    saveState();
  }
  search.addEventListener('input',runSearch);
  document.getElementById('clear-map-search').addEventListener('click',()=>{search.value='';runSearch();});
  function filterCoverage(){
    const q=document.getElementById('coverage-search').value.trim().toLocaleLowerCase(),kind=document.getElementById('coverage-kind').value;let count=0;
    document.querySelectorAll('.coverage-row').forEach(row=>{const show=(!q||row.dataset.search.toLocaleLowerCase().includes(q))&&(kind==='all'||row.dataset.placement===kind);row.hidden=!show;if(show)count++;});
    const counter=document.getElementById('coverage-count');counter.textContent=`显示 ${count} / ${data.coverage.length} 项`;counter.dataset.visibleCount=String(count);
    document.getElementById('coverage-empty').hidden=count!==0;
  }
  document.getElementById('coverage-search').addEventListener('input',filterCoverage);
  document.getElementById('coverage-kind').addEventListener('change',filterCoverage);
  document.getElementById('coverage-reset').addEventListener('click',()=>{document.getElementById('coverage-search').value='';document.getElementById('coverage-kind').value='all';filterCoverage();});
  function openTarget(){const id=decodeURIComponent(location.hash.slice(1));const target=document.getElementById(id);if(target){if(id.startsWith('entity-')){chosen=null;document.getElementById('coverage-kind').value='all';document.getElementById('coverage-search').value=id.slice(7);filterCoverage();}let parent=target.parentElement;while(parent){if(parent.tagName==='DETAILS')parent.open=true;parent=parent.parentElement;}}if(id.startsWith('feature-')&&features.has(id.slice(8)))selectFeature(id.slice(8));}
  window.addEventListener('hashchange',openTarget);
  const params=new URLSearchParams(location.search);if(params.has('q'))search.value=params.get('q');
  if(params.has('layers')){const active=new Set(params.get('layers').split(','));layerInputs.forEach(i=>i.checked=active.has(i.dataset.layerToggle));}
  const starting=views.has(params.get('view'))?params.get('view'):'all';
  if(!params.has('layers')&&starting==='palace2013'){const p=layerInputs.find(i=>i.dataset.layerToggle==='palace');if(p)p.checked=true;}
  requestAnimationFrame(()=>{setView(starting,{save:false});runSearch();openTarget();if(features.has(params.get('feature')))selectFeature(params.get('feature'),{zoom:true});filterCoverage();document.documentElement.dataset.planReady='true';});
  let viewportSize=null;
  new ResizeObserver(entries=>{const {width,height}=entries[0].contentRect;const next=[width,height];if(!viewportSize){viewportSize=next;return;}if(width===viewportSize[0]&&height===viewportSize[1])return;viewportSize=next;const [x,y,w,h]=vb();const nh=w*height/Math.max(width,1);setCamera([x,y+(h-nh)/2,w,nh]);}).observe(document.getElementById('map-viewport'));
})();
