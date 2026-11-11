/* Existing positions are review anchors, not newly determined archaeological sites. */
let portal28=null;
let layer28='review', year28=534;
const renderBefore28=renderEntity, routeBefore28=route, hashBefore28=setHash;
setHash=function(page,query=''){
 if(page==='map'&&layer28!=='review'){const q=new URLSearchParams(query);if(!q.has('layer'))q.set('layer',layer28);if(layer28==='events'&&!q.has('year'))q.set('year',String(year28));query=q.toString()}
 hashBefore28(page,query);
};
function text28(v){return escapeHTML(v)}
function state28(event){return position27(event,year28)}
function eventHTML28(event){
 const state=network27.event_labels[state28(event)];
 const name=event.object&&entityById.get(event.object)?.name;
 return `<div class="v28-event-row"><b>${text28(event.start===null?'年代未定':event.start===event.end?event.start:event.start+'—'+event.end)} · ${text28(event.name)}</b><small>${text28(state)}</small><small>${text28(event.scope)}：${text28(event.state_note)}</small><a href="#network?tab=evidence&item=${encodeURIComponent(event.evidence)}">查看原文 ${text28(event.evidence)}</a>${name?` <a href="#map?entity=${encodeURIComponent(event.object)}&layer=events&year=${year28}">查看${text28(name)}</a>`:'<small>城市总括：不分配地图点位</small>'}</div>`;
}
renderEntity=function(entity){
 const base=renderBefore28(entity);if(!portal28)return base;
 const item=portal28.coverage.find(x=>x.id===entity.id);if(!item)return base;
 const links=[];
 if(item.evidence.length)links.push(`<a href="#research?panel=${item.panel||'A'}&evidence=${item.evidence[0]}">宫前证据 ${item.evidence.length} 条 ↗</a>`);
 if(item.model)links.push('<a href="#model?case=s011">比较约束与候选位置 ↗</a>');
 if(item.network.length)links.push(`<a href="#network?tab=evidence&item=${item.network[0]}">水陆段落 ${item.network.length} 条 ↗</a>`);
 if(item.events.length)links.push(`<a href="#network?tab=events&entity=${encodeURIComponent(entity.id)}&year=${year28}">事件 ${item.events.length} 项 ↗</a>`);
 if(!links.length)return base;
 const ev=layer28==='events'&&network27?network27.events.filter(e=>e.object===entity.id).map(eventHTML28).join(''):'';
 return `<section class="v28-coverage"><h3>v2.8 整合研究层</h3><p>沿用原示意位置；以下是已经纳入地图阅读的研究成果，不是新增实测定位。</p>${links.join(' ')}${ev}</section>`+base;
};
function summary28(){
 if(!portal28)return;
 const body=document.querySelector('#inspector-body');
 if(layer28==='events'){
  const ordered=[...network27.events].sort((a,b)=>Math.abs((a.start??year28)-year28)-Math.abs((b.start??year28)-year28));
  body.innerHTML=`<section class="v28-related"><h2>${year28}年：读取事件，不猜现状</h2><p>橙色方标表示有事件记录的既有示意点，不表示该地点在所选年已毁坏或仍存在。</p>${ordered.map(eventHTML28).join('')}</section>`;
 }else{
  body.innerHTML=`<section class="v28-related"><div class="eyebrow">当前整合版 ${text28(portal28.release)}</div><h2>地图已经接入的新成果</h2><p>绿色圆环：有专题证据。橙色方标：有事件记录。点击原有地点即可沿同一实体查看新研究。</p><a href="#map?entity=ic_yongning"><b>永宁寺与太尉府 →</b><small>四邻、官署路侧与候选平面</small></a><a href="#map?entity=bridge_jianchun"><b>建春门石桥 →</b><small>桥水关系、527年毁损及作用范围</small></a><a href="#map?entity=v3_jingming"><b>景明寺 →</b><small>立寺与塔始造分开，完工时间仍未定</small></a><a class="v28-unplaced" href="#network?tab=events&year=547"><b>547年事件阅读 →</b><small>城市总括不下传为每处建筑的现状</small></a><p>${portal28.stats.marked}组原有图符附加了研究覆盖标记；没有可靠单独示意点的记录只进入资料栏。</p></section>`;
 }
}
function applyLayer28(refresh=true){
 if(!svg||!portal28||!network27)return;
 const q=new URLSearchParams(location.hash.split('?')[1]||'');
 layer28=['review','events','baseline'].includes(q.get('layer'))?q.get('layer'):'review';
 year28=[516,527,534,546,547].includes(Number(q.get('year')))?Number(q.get('year')):534;
 const group=svg.querySelector('#review-layer-v28');
 if(group){group.style.display=layer28==='baseline'?'none':'';group.querySelectorAll('[data-review-event]').forEach(n=>{n.style.display=layer28==='events'&&n.dataset.reviewEvent!=='true'?'none':''})}
 document.querySelectorAll('[data-v28-layer]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.v28Layer===layer28)));
 const yearSelect=document.querySelector('#v28-year');if(yearSelect){yearSelect.value=String(year28);yearSelect.disabled=layer28!=='events'}
 const legend=document.querySelector('#v28-layer-legend');if(legend)legend.textContent=layer28==='baseline'?'档案底图模式：关闭研究标记，保留原图面。':layer28==='events'?`${year28}年事件阅读：标记只表示存在相关记录，不表示当年建筑存废。`:'绿色圆环＝专题覆盖；橙色方标＝事件记录。均沿用原图符位置，不新增定位。';
 if(refresh){const id=q.get('entity');if(id&&entityById.has(id))selectEntity(id,false,false);else summary28()}
 document.documentElement.dataset.portal28Layer=layer28;
}
route=function(){routeBefore28();if((location.hash||'#map').startsWith('#map')&&portal28){applyLayer28();document.title='研究整合地图 v2.8 · 北魏洛阳'}};
function setLayer28(layer){const q=new URLSearchParams(location.hash.startsWith('#map?')?location.hash.split('?')[1]:'');q.set('layer',layer);if(layer==='events')q.set('year',String(year28));setHash('map',q.toString());applyLayer28()}
async function checkRelease28(){
 const status=document.querySelector('#v28-online-status');const next=document.querySelector('#v28-update-link');
 try{
  const response=await fetch('./release.json?check='+Date.now(),{cache:'no-store'});if(!response.ok)throw Error('HTTP '+response.status);
  const latest=await response.json();status.classList.remove('v28-status-error');
  if(latest.source_commit!==window.ATLAS_RELEASE.source_commit){
   status.textContent='检测到另一个发布版本，请加载最新入口。';
   const url=new URL(latest.entrypoint,location.href);if(url.origin!==location.origin||!url.pathname.startsWith(new URL('.',location.href).pathname))throw Error('更新地址不在本站');
   url.searchParams.set('build',latest.source_commit);url.hash=location.hash;next.href=url.href;next.hidden=false;
  }else{status.textContent='已核对在线发布 · '+latest.source_commit.slice(0,7);next.hidden=true}
 }catch(err){status.textContent='在线版本暂未核对；当前页面 '+window.ATLAS_RELEASE.release;status.classList.add('v28-status-error')}
}
async function initPortal28(){
 try{
  const response=await atlasFetch('./data/review-layer-v28.json');if(!response.ok)throw Error('整合层加载失败');portal28=await response.json();
  for(let i=0;i<600&&(!svg||!network27||document.documentElement.dataset.model26Ready!=='true'||document.documentElement.dataset.researchReady!=='true');i++)await new Promise(r=>setTimeout(r,50));
  if(!svg||!network27)throw Error('基础研究模块未就绪');
  document.querySelectorAll('[data-v28-layer]').forEach(b=>b.addEventListener('click',()=>setLayer28(b.dataset.v28Layer)));
  document.querySelector('#v28-year').addEventListener('change',e=>{year28=Number(e.target.value);setLayer28('events')});
  document.querySelector('#v28-check-release').addEventListener('click',checkRelease28);
  applyLayer28();document.documentElement.dataset.portal28Ready='true';
  checkRelease28();window.addEventListener('pageshow',e=>{if(e.persisted)checkRelease28()});
 }catch(err){console.error(err);document.documentElement.dataset.portal28Ready='error';document.querySelector('#v28-online-status').textContent='整合层加载失败：'+err.message}
}
initPortal28();
