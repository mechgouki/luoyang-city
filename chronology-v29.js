/* Same-place reading, not a model of unobserved persistence. */
let chronology29=null, chronologySVG29='', view29=[2000,2200,9000,8200];
const routeBefore29=route, entityBefore29=renderEntity;
pageIds.push('compare');
const c29escape=v=>escapeHTML(String(v??''));
const c29href=(site,year)=>'#compare?site='+encodeURIComponent(site)+'&year='+year;
route=function(){
 const [page,query='']=(location.hash||'#map').slice(1).split('?');
 if(page==='compare'){
  setRoute('compare');document.title='同址时层对照 v2.9 · 北魏洛阳';
  if(chronology29){const q=new URLSearchParams(query);renderChronology29(q.get('site')||'D29-01',Number(q.get('year')||547))}
 }else{routeBefore29();if(page==='map')document.title='研究整合地图 '+(window.ATLAS_RELEASE?.release||'v2.9')+' · 北魏洛阳'}
};
renderEntity=function(entity){
 const old=entityBefore29(entity);if(!chronology29)return old;
 const d=chronology29.dossiers.find(d=>d.site_id===entity.id||d.related_ids.includes(entity.id));if(!d)return old;
 return `<section class="c29-inline"><strong>同址时层对照 · v2.9</strong><p>${c29escape(d.change_reading)}</p><a href="${c29href(d.id,547)}">看同一地点的早期记述与后续变化 ↗</a><small>事件发生不等于547年仍维持相同状态。</small></section>`+old;
};
function c29time(record,year){return record.target_relations[String(year)]||'undated'}
function c29card(record,year){
 const source=chronology29.sources.find(s=>s.id===record.source_id);const state=c29time(record,year);
 return `<article class="c29-record" id="record-${record.id}" data-record="${record.id}" data-time="${state}"><header><b>${record.id} · ${c29escape(record.title)}</b><span class="c29-badge ${state}">${c29escape(chronology29.labels[state])}</span></header><p class="c29-date">${c29escape(record.date.label)} · 作用于：${c29escape(record.scope)}</p><blockquote>${c29escape(record.quote)}</blockquote><p>${c29escape(record.interpretation_limit)}</p><small><a href="${c29escape(source.url)}" target="_blank" rel="noopener">${c29escape(source.title)} ↗</a> / ${c29escape(record.locator)}</small>${record.date.kind==='alternatives'?'<p class="c29-warning">保留两个文本纪年，不取平均，不变成连续区间，不计作两次已证事件。</p>':''}${record.prior_event_id?`<small>关联原事件 ${c29escape(record.prior_event_id)}，不是重复的独立证据。</small>`:''}</article>`;
}
function setView29(v){
 if(v.length!==4||!v.every(Number.isFinite)||v[2]<=0||v[3]<=0)return;
 view29=v;document.querySelectorAll('.c29-canvas svg').forEach(s=>s.setAttribute('viewBox',v.join(' ')));
}
function zoom29(f){const [x,y,w,h]=view29;const nw=Math.max(1800,Math.min(15000,w*f)),nh=nw*h/w;setView29([x+(w-nw)/2,y+(h-nh)/2,nw,nh])}
function mountChronologyMap29(node,prefix,dossier,year){
 const parsed=new DOMParser().parseFromString(chronologySVG29,'image/svg+xml');const map=parsed.documentElement;
 if(map.tagName!=='svg')throw Error('Invalid common map');
 const renamed=new Map();map.querySelectorAll('[id]').forEach(el=>{renamed.set(el.id,prefix+'-'+el.id);el.id=prefix+'-'+el.id});
 map.querySelectorAll('*').forEach(el=>{for(const a of [...el.attributes]){let value=a.value;for(const [old,newId] of renamed)value=value.replaceAll('url(#'+old+')','url(#'+newId+')');if(value!==a.value)el.setAttribute(a.name,value)}});
 map.classList.add('c29-svg');node.replaceChildren(document.importNode(map,true));
 const live=node.querySelector('svg');live.setAttribute('viewBox',view29.join(' '));
 live.querySelectorAll('[data-dossier]').forEach(el=>{
  el.classList.toggle('selected',el.dataset.dossier===dossier.id);
  const go=()=>{location.hash=c29href(el.dataset.dossier,year)};
  el.addEventListener('click',event=>{if(!node.dataset.dragged)go();event.stopPropagation()});
  el.addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();go()}});
 });
 let drag=null;
 node.addEventListener('pointerdown',event=>{
  if(event.target.closest('[data-dossier]'))return;
  node.dataset.dragged='';drag={x:event.clientX,y:event.clientY,box:[...view29],id:event.pointerId};node.setPointerCapture(event.pointerId);
 });
 node.addEventListener('pointermove',event=>{
  if(!drag||drag.id!==event.pointerId)return;
  const rect=node.getBoundingClientRect(),scale=Math.min(rect.width/drag.box[2],rect.height/drag.box[3]);
  const dx=(event.clientX-drag.x)/scale,dy=(event.clientY-drag.y)/scale;
  if(Math.abs(dx)+Math.abs(dy)>3)node.dataset.dragged='true';
  setView29([drag.box[0]-dx,drag.box[1]-dy,drag.box[2],drag.box[3]]);
 });
 const stop=()=>{drag=null;setTimeout(()=>{node.dataset.dragged=''},0)};
 node.addEventListener('pointerup',stop);node.addEventListener('pointercancel',stop);
 node.addEventListener('wheel',event=>{event.preventDefault();zoom29(event.deltaY>0?1.15:1/1.15)},{passive:false});
}
function renderChronology29(id,year){
 const d=chronology29.dossiers.find(d=>d.id===id)||chronology29.dossiers[0];
 if(![528,531,532,533,534,546,547].includes(year))year=547;
 const rows=chronology29.records.filter(r=>r.dossier_id===d.id);
 const located=Boolean(d.anchor),known=rows.filter(r=>['before','at'].includes(c29time(r,year))).length;
 view29=located?[d.anchor.x-2200,d.anchor.y-1800,4400,3600]:[3000,3000,4400,3600];
 document.querySelector('#chronology-content').innerHTML=`
 <header class="article-header"><div class="eyebrow">SAME PLACE · DIFFERENT EVIDENCE · v2.9</div><h1>不是把盛时图涂成废墟</h1><p>同一地点，先看早期描述，再看已记变化。首批12处、25条记录；位置不动，证据与时间分别读。</p></header>
 <div class="c29-controls"><label>地点档案 <select id="c29-site">${chronology29.dossiers.map(x=>`<option value="${x.id}" ${x.id===d.id?'selected':''}>${x.id} ${c29escape(x.title)}</option>`).join('')}</select></label><label>对照年份 <select id="c29-year">${[528,531,532,533,534,546,547].map(y=>`<option ${y===year?'selected':''}>${y}</option>`).join('')}</select></label><button id="c29-zoom-in" aria-label="同步放大">＋</button><button id="c29-zoom-out" aria-label="同步缩小">−</button><button id="c29-home">回到所选地点</button><a href="#map?entity=${encodeURIComponent(d.site_id)}">回主地图 ↗</a></div>
 <p id="c29-unlocated" class="c29-warning" ${located?'hidden':''}>${c29escape(d.title)}只在群组名录内，未设置独立点位。两侧保留参考区域，不把群组文字中心变成寺址。</p>
 <div class="c29-pair">
  <section class="c29-pane"><header><small>左 / 文献早期语境</small><h2>盛时综合 · 516—528</h2><p>保留前史及原宅身份，不保证此期任一年全部共存。</p></header><div id="c29-left" class="c29-canvas" aria-label="早期语境的共同地图"></div><div class="c29-reading"><b>${c29escape(d.title)}</b><p>${c29escape(d.early_reading)}</p></div></section>
  <section class="c29-pane c29-late"><header><small>右 / 事件与记述，不是存废快照</small><h2>对照至 ${year} 年</h2><p>${known}条可明确归入此前／当年；其他记录保持不定。</p></header><div id="c29-right" class="c29-canvas" aria-label="后续变化的同参照地图"></div><div class="c29-reading"><b>${year}年完整存废：本批未能确证</b><p>${c29escape(d.change_reading)}</p></div></section>
 </div>
 <p class="c29-key">两侧底图、锚点和视窗同步；空心编号表示已审档案，不表示完好、毁坏或置信范围。淡色地物仅供定位，不能当作所选年的建筑清单。${d.id==='D29-04'?'石经事件挂到关联学堂地点阅读，不新增石经坐标。':''}</p>
 <section class="c29-records"><h2>逐条核对：${c29escape(d.title)}</h2><p>${c29escape(d.purpose)}　<span id="c29-status-note">${c29escape(d.status_note)}</span></p>${rows.map(r=>c29card(r,year)).join('')}</section>
 <details class="c29-ledger"><summary>首批覆盖：12处已做片段核查；其余327个实体不冒充已审</summary><table><thead><tr><th>档案</th><th>主要变化问题</th><th>547完整存废</th></tr></thead><tbody>${chronology29.dossiers.map(x=>`<tr><td><a href="${c29href(x.id,year)}">${c29escape(x.id+' '+x.title)}</a></td><td>${c29escape(x.purpose)}</td><td>未能确证</td></tr>`).join('')}</tbody></table></details>
 <div class="c29-downloads"><a href="./downloads/chronology-v29.csv" download>25条记录 CSV ↓</a><a href="./downloads/chronology-study-v29.html" target="_blank" rel="noopener">完整可打印报告 ↗</a><a href="./data/chronology-v29.json" target="_blank" rel="noopener">数据与339对象审阅账本 ↗</a><a href="./assets/chronology-v29.svg" target="_blank" rel="noopener">共同示意底图 SVG ↗</a></div>
 <p class="c29-method">资料层次：本批核查《洛阳伽蓝记》电子正文及相关校语，未宣称古刻书影逐叶校勘。两种建中寺保留不同实体；异记不取平均、下限不当确年、至今不自动等于547。${c29escape(chronology29.policy.source_family)}</p>`;
 const change=()=>{location.hash=c29href(document.querySelector('#c29-site').value,Number(document.querySelector('#c29-year').value))};
 document.querySelector('#c29-site').addEventListener('change',change);document.querySelector('#c29-year').addEventListener('change',change);
 mountChronologyMap29(document.querySelector('#c29-left'),'left',d,year);mountChronologyMap29(document.querySelector('#c29-right'),'right',d,year);
 document.querySelector('#c29-zoom-in').onclick=()=>zoom29(1/1.3);document.querySelector('#c29-zoom-out').onclick=()=>zoom29(1.3);
 document.querySelector('#c29-home').onclick=()=>setView29(located?[d.anchor.x-2200,d.anchor.y-1800,4400,3600]:[3000,3000,4400,3600]);
 document.documentElement.dataset.chronology29Site=d.id;
}
async function initChronology29(){
 try{
  const [r,s]=await Promise.all([atlasFetch('./data/chronology-v29.json'),atlasFetch('./assets/chronology-v29.svg')]);
  if(!r.ok||!s.ok)throw Error('时层数据未能载入');chronology29=await r.json();chronologySVG29=await s.text();
  for(let i=0;i<600&&document.documentElement.dataset.portal28Ready!=='true';i++)await new Promise(resolve=>setTimeout(resolve,50));
  if(document.documentElement.dataset.portal28Ready!=='true')throw Error('主地图未就绪');
  portal28.release=window.ATLAS_RELEASE.release;document.documentElement.dataset.chronology29Ready='true';route();
 }catch(error){document.documentElement.dataset.chronology29Ready='error';document.querySelector('#chronology-content').textContent='时层档案加载失败：'+error.message;console.error(error)}
}
initChronology29();
