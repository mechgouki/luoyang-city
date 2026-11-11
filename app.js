/* 北魏洛阳文献地图 · GitHub Pages MVP · 无第三方运行时依赖 */
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const safeURL = url => /^https?:\/\//i.test(String(url || '')) ? url : null;
const typeLabel = {temple:'寺院',palace:'宫城宫苑',official:'官署',bureau:'官署',residence:'宅第',market:'市集',ward:'里坊',gate:'城门',bridge:'桥梁',water:'水系',garden:'宫苑',school:'学校',ritual:'礼制设施'};
const relationLabel = {has_east:'其东有',has_west:'其西有',has_north:'其北有',has_south:'其南有',faces_west:'西对',faces:'相对',neighbors_north:'北邻',bounds_south:'南界',southwest_of:'西南于',northeast_of:'东北于',northwest_of:'西北于',southeast_of:'东南于',inside_gate:'门内',outside_gate:'门外',at_region:'大致在',in_ward:'属于里坊',within_region:'区域内',converted_from:'从…改建',later_became:'后来改为',same_site_claim:'有同址说',not_identical:'不可直接视同',associated_access_via:'通行关联',south_of:'南于',north_of:'北于',east_of:'东于',west_of:'西于',inside:'位于…内',within:'位于…内',near:'附近',adjacent_to:'接邻',opposite:'相对',part_of:'属于',on_road:'沿道路',across:'跨越'};
const stateLabel = {attested_by_528:'盛时已有记载',later_temple:'盛时为宅第／后改寺',undated:'年代未详',historical:'历史旧迹',retrospective:'后世追记'};
const pageIds = ['map','atlas','issues','about'];
let entities=[], markers=[], disputes=[], regions=[], sheets=[];
let svg=null, viewport=null, viewBox=[0,0,12400,12030], homeView=[0,0,12400,12030], selectedEntity=null, drag=null;
let drawingGroup=null, drawingMatrix=null;
let entityById=new Map(), selectedRegion=null, selectedIssue=null, suppressClick=false;

function setHash(page, query='') { location.hash = page + (query ? '?' + query : ''); }
function setRoute(page) {
  if(!pageIds.includes(page)) page='map';
  pageIds.forEach(id => { $('#page-'+id).hidden = (id!==page); });
  $$('[data-nav]').forEach(a=>a.classList.toggle('is-current',a.dataset.nav===page));
  document.title = (page==='map'?'交互地图':page==='atlas'?'分区图册':page==='issues'?'史料争议':'研究说明')+' · 北魏洛阳文献地图';
}
function route(){
  const fragment=(location.hash||'#map').slice(1);
  const [page='map', qs='']=fragment.split('?');
  const query=new URLSearchParams(qs);
  setRoute(page);
  if(page==='map') {
    const reg=query.get('region'),id=query.get('entity');
    if(reg) focusRegion(reg,false);
    else if(!id && svg && selectedRegion) focusFull(false);
    if(id) selectEntity(id,false,true);
  } else if(page==='issues') {
    const id=query.get('issue'); if(id) showIssue(id,false);
  }
}

function currentViewBox(){return viewBox.map(x=>+x).join(' ')}
function clampView(b) {
 const [fullX,fullY,fullW,fullH]=homeView;
 const w=Math.max(280,Math.min(fullW,b[2]));
 const h=Math.max(270,Math.min(fullH,b[3]));
 const x=Math.min(fullX+fullW-w,Math.max(fullX,b[0]));
 const y=Math.min(fullY+fullH-h,Math.max(fullY,b[1]));
 return [x,y,w,h];
}
function setView(b){if(!svg)return;viewBox=clampView(b);svg.setAttribute('viewBox',currentViewBox())}
function zoom(factor,cx=null,cy=null) {
 const [x,y,w,h]=viewBox;
 const rx=cx ?? x+w/2,ry=cy ?? y+h/2;
 const nw=w*factor,nh=h*factor;
 setView([rx-(rx-x)*factor,ry-(ry-y)*factor,nw,nh]);
}
function focusBounds(x,y,w,h,pad=.20){
 if(!svg)return;
 const container=$('#map-viewport').getBoundingClientRect();
 const ratio=container.width/Math.max(1,container.height);
 const sw=Math.max(750,w*(1+pad*2));let sh=Math.max(750,h*(1+pad*2));
 const width=Math.max(sw,sh*ratio),height=Math.max(sh,sw/ratio);
 setView([x+w/2-width/2,y+h/2-height/2,width,height]);
}
function screenToWorld(clientX,clientY){
 if(!svg)return {x:0,y:0};
 const pt=svg.createSVGPoint();pt.x=clientX;pt.y=clientY;
 const ctm=svg.getScreenCTM();if(!ctm)return {x:0,y:0};
 return pt.matrixTransform(ctm.inverse());
}
function drawingBounds(x,y,width,height){
 const m=drawingMatrix;if(!m)return [x,y,width,height];
 const corners=[[x,y],[x+width,y],[x,y+height],[x+width,y+height]];
 const points=corners.map(([px,py])=>[m.a*px+m.c*py+m.e,m.b*px+m.d*py+m.f]);
 const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]);
 return [Math.min(...xs),Math.min(...ys),Math.max(...xs)-Math.min(...xs),Math.max(...ys)-Math.min(...ys)];
}
function focusRegion(code,update=true){
 const r=regions.find(x=>x.code===code);if(!r)return;
 selectedRegion=code;
 const [x,y,width,height]=r.bbox;
 // v2.4 区域框是 [左,上,宽,高]，不是两角坐标。
 focusBounds(...drawingBounds(x,y,width,height),.22);
 $$('.region-btn').forEach(b=>b.classList.toggle('active',b.dataset.code===code));
 $('#map-status').textContent=code+' · '+r.title;
 $('#filters-panel').classList.remove('open');
 if(update)setHash('map','region='+encodeURIComponent(code));
}
function focusFull(update=true){ selectedRegion=null;setView(homeView);$('#map-status').textContent='全城 · 文献关系图';$$('.region-btn').forEach(b=>b.classList.remove('active'));if(update)setHash('map'); }
function focusMarker(id){
 const match=markers.find(m=>m.ids.includes(id));if(!match)return;
 // 按示意绘图坐标局部放大，不作为真实地理配准
 const w=3000,h=2500;focusBounds(...drawingBounds(match.x-w/2,match.y-h/2,w,h),0);
}
function markerOverlay(){
 const ns='http://www.w3.org/2000/svg',layer=document.createElementNS(ns,'g');
 layer.setAttribute('id','atlas-click-targets');
 for(const [i,m] of markers.entries()){
  const group=document.createElementNS(ns,'g');group.setAttribute('class','feature-target');group.dataset.ids=m.ids.join(',');
  const ring=document.createElementNS(ns,'circle');ring.setAttribute('class','feature-ring');ring.setAttribute('cx',m.x);ring.setAttribute('cy',m.y);ring.setAttribute('r',m.kind==='compound'?145:95);
  const hit=document.createElementNS(ns,'circle');hit.setAttribute('class','feature-hit');hit.setAttribute('cx',m.x);hit.setAttribute('cy',m.y);hit.setAttribute('r',m.kind==='compound'?170:110);hit.setAttribute('tabindex','0');hit.setAttribute('role','button');hit.setAttribute('aria-label',m.label||'查看地点');
  const open=()=>{if(drag?.moved||suppressClick)return;selectEntity(m.ids[0],true,false);};
  hit.addEventListener('click',open);
  hit.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open()}});
  hit.addEventListener('pointerenter',e=>{const tt=$('#map-tooltip');tt.textContent=m.label||entityById.get(m.ids[0])?.name||'地点';tt.hidden=false;updateTooltip(e)});
  hit.addEventListener('pointermove',updateTooltip);
  hit.addEventListener('pointerleave',()=>{$('#map-tooltip').hidden=true});
  group.append(ring,hit);layer.appendChild(group);
 }
 (drawingGroup||svg).appendChild(layer);
}
function updateTooltip(e){const t=$('#map-tooltip');if(t.hidden)return;const r=$('#map-viewport').getBoundingClientRect();t.style.left=Math.min(r.width-180,Math.max(8,e.clientX-r.left+15))+'px';t.style.top=Math.max(6,e.clientY-r.top-48)+'px';}
async function installSVG(){
 const resp=await fetch('./assets/master-v24.svg');if(!resp.ok)throw Error('无法加载 SVG 母图');
 const text=await resp.text(),parsed=new DOMParser().parseFromString(text,'image/svg+xml');
 if(parsed.querySelector('parsererror'))throw Error('SVG 格式有误');
 svg=document.importNode(parsed.documentElement,true);
 svg.removeAttribute('width');svg.removeAttribute('height');svg.setAttribute('class','atlas-svg');
 const v=svg.getAttribute('viewBox')?.split(/\s+/).map(Number);if(v?.length===4)homeView=v;
 viewBox=[...homeView];
 // 母图另有页边与标题平移；标记和相机必须采用同一坐标变换。
 const groups=[...svg.children].filter(el=>el.localName==='g'&&el.hasAttribute('transform'));
 if(groups.length!==1)throw Error('母图绘图坐标组不唯一，需核对导出格式');
 drawingGroup=groups[0];drawingMatrix=drawingGroup.transform.baseVal.consolidate()?.matrix||null;
 viewport=$('#map-viewport');viewport.replaceChildren(svg);
 markerOverlay();
 svg.addEventListener('wheel',e=>{e.preventDefault();const at=screenToWorld(e.clientX,e.clientY);zoom(e.deltaY>0?1.16:1/1.16,at.x,at.y);},{passive:false});
 viewport.addEventListener('pointerdown',e=>{
    if((e.button!==0&&e.pointerType!=='touch')||!e.isPrimary)return;
    const matrix=svg.getScreenCTM();if(!matrix)return;
    drag={id:e.pointerId,x:e.clientX,y:e.clientY,view:[...viewBox],world:screenToWorld(e.clientX,e.clientY),inverse:matrix.inverse(),moved:false};
    // 普通点击必须交给建筑标记；真正拖动后才捕获指针。
 });
 viewport.addEventListener('pointermove',e=>{
    if(!drag||e.pointerId!==drag.id)return;
    const dx=e.clientX-drag.x,dy=e.clientY-drag.y;
    if(!drag.moved&&Math.abs(dx)+Math.abs(dy)>5){
      drag.moved=true;viewport.setPointerCapture(e.pointerId);
    }
    if(!drag.moved)return;
    viewport.classList.add('is-panning');
    const point=svg.createSVGPoint();point.x=e.clientX;point.y=e.clientY;
    const world=point.matrixTransform(drag.inverse);
    setView([drag.view[0]+drag.world.x-world.x,drag.view[1]+drag.world.y-world.y,drag.view[2],drag.view[3]]);
 });
 viewport.addEventListener('pointerup',e=>{
    if(!drag||e.pointerId!==drag.id)return;
    suppressClick=drag.moved;setTimeout(()=>suppressClick=false,50);
    drag=null;viewport.classList.remove('is-panning');
    if(viewport.hasPointerCapture(e.pointerId))viewport.releasePointerCapture(e.pointerId);
 });
 viewport.addEventListener('pointercancel',()=>{drag=null;viewport.classList.remove('is-panning')});
 viewport.addEventListener('pointerleave',()=>{if(drag&&!drag.moved)drag=null});
 $('#zoom-in').addEventListener('click',()=>zoom(1/1.4));
 $('#zoom-out').addEventListener('click',()=>zoom(1.4));
 $('#home-map').addEventListener('click',()=>focusFull());
 $('#filter-toggle').addEventListener('click',()=>$('#filters-panel').classList.add('open'));
 $('#close-filters').addEventListener('click',()=>$('#filters-panel').classList.remove('open'));
 $('#close-inspector').addEventListener('click',()=>$('#inspector').classList.remove('open'));
 return true;
}
function renderRegions(){
 $('#region-list').innerHTML=regions.map(r=>`<button class="region-btn" data-code="${escapeHTML(r.code)}"><span class="region-code">${escapeHTML(r.code)}</span><span class="region-name">${escapeHTML(r.title)}</span></button>`).join('');
 $$('.region-btn').forEach(b=>b.addEventListener('click',()=>{setRoute('map');focusRegion(b.dataset.code)}));
}
function showSearch(){
 const q=$('#place-search').value.trim().toLocaleLowerCase();const list=$('#search-results');
 if(!q){list.hidden=true;list.replaceChildren();return;}
 const found=entities.filter(e=>[e.name,e.source_name,e.map_id,e.id].some(x=>String(x||'').toLocaleLowerCase().includes(q))|| (Array.isArray(e.aliases) && e.aliases.some(a=>String(typeof a==='string'?a:a?.name||'').toLocaleLowerCase().includes(q)))).slice(0,12);
 list.innerHTML=found.map(e=>`<button class="search-item" data-id="${escapeHTML(e.id)}"><span>${escapeHTML(e.name)}</span><span>${escapeHTML(e.map_id||'未编号')}</span></button>`).join('')||( `<div style="padding:13px;font-size:11px;color:#8c9288">无匹配名称。可尝试别名或原书用字。</div>`);
 list.hidden=false;
 $$('.search-item',list).forEach(b=>b.addEventListener('click',()=>{list.hidden=true;setRoute('map');selectEntity(b.dataset.id,true,true)}));
}
function renderEntity(e){
 const quote=(e.source_quote||'').trim();const isLocated=markers.some(m=>m.ids.includes(e.id));
 const sourceURL=safeURL(e.source_url);
 const constraints=(e.constraints||[]).slice(0,12);
 return `<div class="inspector-head"><div class="entity-id">${escapeHTML(e.map_id||e.id)} · ${escapeHTML(typeLabel[e.type]||e.type||'地点对象')}</div><h2 class="inspector-name">${escapeHTML(e.name)}</h2><div class="mini-tags"><span class="mini-tag">卷${escapeHTML(e.juan||'未详')}</span><span class="mini-tag ${isLocated?'':'warn'}">${isLocated?'已在母图关联标记':'具体位置未定'}</span>${e.temporal_state?`<span class="mini-tag warn">${escapeHTML(stateLabel[e.temporal_state]||e.temporal_state)}</span>`:''}</div></div>
 <div class="detail-section"><h3>文献原句</h3>${quote?`<div class="source-quote">${escapeHTML(quote)}</div>`:'<p class="muted" style="font-size:12px">当前资料无可展示的原句，不能以位置替代证据。</p>'}<div class="ref-line">${escapeHTML(e.source_ref||'出处索引待补')}</div>${sourceURL?`<p style="margin:12px 0 0"><a class="source-link" href="${escapeHTML(sourceURL)}" target="_blank" rel="noopener noreferrer">打开原始文本 ↗</a></p>`:''}</div>
 <div class="detail-section"><h3>空间关系与依据</h3>${constraints.length?constraints.map(c=>`<div class="relation-item"><strong>${escapeHTML(relationLabel[c.relation]||c.relation||'关系')}</strong> · ${escapeHTML(entityById.get(c.target_id)?.name||c.target_id||'参考对象')}${c.distance_text?` · ${escapeHTML(c.distance_text)}`:''}${c.source_quote?`<div class="ref-line">${escapeHTML(c.source_quote)}</div>`:''}</div>`).join(''):'<p class="muted" style="font-size:12px">尚未登记可单独核验的定位关系。</p>'}</div>
 <div class="detail-section"><h3>读图提醒</h3><div class="related-notice">${isLocated?'当前标记表示文献关系下的绘图候选；图形大小、距离及院落轮廓不代表实测。':'此对象可能有分区归属，但尚无独立、可靠的街址；不会自动生成一个地图点。'}</div></div>
 <div class="detail-section"><button class="primary-btn" id="copy-entity">复制此处链接 <span>↗</span></button></div>`;
}
function selectEntity(id,update=true,focus=false){
 const e=entityById.get(id);if(!e)return;
 selectedEntity=id;
 $('#inspector-body').innerHTML=renderEntity(e);
 $$('#atlas-click-targets .feature-target').forEach(g=>g.classList.toggle('selected',g.dataset.ids.split(',').includes(id)));
 if(focus)focusMarker(id);
 $('#inspector').classList.add('open');
 $('#copy-entity')?.addEventListener('click',async()=>{
   const url=location.origin+location.pathname+'#map?entity='+encodeURIComponent(id);
   try{await navigator.clipboard.writeText(url);$('#copy-entity').textContent='链接已复制 ✓'}
   catch{prompt('复制以下链接',url)}
 });
 if(update)setHash('map','entity='+encodeURIComponent(id));
}
function renderSheets(category='全部'){
 $('#sheets-grid').innerHTML=sheets.filter(s=>category==='全部'|| (category==='附图'?s.category==='附图':s.category===category)).map(s=>`<article class="sheet-card"><div class="sheet-photo"><img loading="lazy" src="./${escapeHTML(s.thumbnail)}" alt="${escapeHTML(s.title)}"/></div><div class="sheet-card-body"><div class="sheet-card-header"><span>${escapeHTML(s.code)} · ${escapeHTML(s.category)}</span><span>第${escapeHTML(s.page||'-')}页</span></div><h3>${escapeHTML(s.title)}</h3><div class="sheet-card-actions"><a href="./${escapeHTML(s.svg)}" target="_blank" rel="noopener">放大 SVG ↗</a>${s.code.startsWith('R')?`<a href="#map?region=${escapeHTML(s.code)}">定位地图</a>`:''}</div></div></article>`).join('');
}
function renderIssues(){
 $('#issues-list').innerHTML=disputes.map(d=>`<button class="issue-item" data-id="${escapeHTML(d.id)}"><span class="issue-code">${escapeHTML(d.id)}</span><span>${escapeHTML(d.title)}</span></button>`).join('');
 $$('.issue-item').forEach(b=>b.addEventListener('click',()=>showIssue(b.dataset.id,true)));
}
function showIssue(id,update=true){
 const d=disputes.find(x=>x.id===id);if(!d)return;
 selectedIssue=id;
 $$('.issue-item').forEach(b=>b.classList.toggle('selected',b.dataset.id===id));
 $('#issue-detail').innerHTML=`<div class="eyebrow">${escapeHTML(d.id)} · ${escapeHTML(d.category||'史料校读')}</div><h2>${escapeHTML(d.title)}</h2>
 <h3>现有证据</h3><p>${escapeHTML(d.evidence_summary||'材料待整理')}</p><div class="issue-divider"></div>
 <h3>本版采用的绘图处理</h3><p>${escapeHTML(d.current_drawing_policy||'未确定')}</p><div class="issue-divider"></div>
 <h3>仍待判断</h3><p>${escapeHTML(d.decision_question||'未列明确待决问题')}</p><div class="issue-divider"></div>
 <p class="ref-line">材料索引：${escapeHTML(d.source_ids||'待补')}</p><div class="related-notice">这一条记录的是本版研究判断，不应当被误读为史学界已经达成共识。</div>`;
 if(update)setHash('issues','issue='+encodeURIComponent(id));
}

async function start(){
 try{
  const paths=['entities','markers','disputes','regions','sheets'];
  const data=await Promise.all(paths.map(async name=>{const r=await fetch('./data/'+name+'.json');if(!r.ok)throw Error('数据文件加载失败：'+name);return r.json()}));
  [entities,markers,disputes,regions,sheets]=data;
  entityById=new Map(entities.map(x=>[x.id,x]));
  renderRegions();renderIssues();renderSheets();
  await installSVG();
  $('#place-search').addEventListener('input',showSearch);
  $('#place-search').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();const first=$('#search-results .search-item');if(first)first.click()}});
  $$('#sheet-tabs button').forEach(b=>b.addEventListener('click',()=>{$$('#sheet-tabs button').forEach(x=>x.classList.toggle('selected',x===b));renderSheets(b.dataset.category)}));
  $('#explore-yongning')?.addEventListener('click',()=>selectEntity('ic_yongning',true,true));
  window.addEventListener('hashchange',route);route();
 }catch(error){ console.error(error);$('#map-viewport').innerHTML=`<div class="map-loading" style="padding:20px;text-align:center">地图或数据加载失败：${escapeHTML(error.message)}。请使用本地 HTTP 服务打开网站，而不是直接双击 file:// 页面。</div>`; }
}
start();
