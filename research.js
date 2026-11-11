/* R07 evidence supplement. Original v2.4 data and coordinates remain unchanged. */
let researchData=null;
const statusById=new Map();
const originalRoute=route, originalEntity=renderEntity, originalIssues=renderIssues, originalIssue=showIssue, originalView=setView;
pageIds.push('research');
Object.assign(typeLabel,{office:'官署',ritual_site:'礼制设施',named_place_unknown_function:'功能未详',ice_storage:'藏冰设施'});
const rEscape=value=>escapeHTML(value);
function researchHref(group='A',evidence=''){return '#research?panel='+encodeURIComponent(group)+(evidence?'&evidence='+encodeURIComponent(evidence):'')}
function issueLink(id){return `<a class="r-link" href="#issues?issue=${encodeURIComponent(id)}">${rEscape(id)}</a>`}
function entityLink(id){const e=entityById.get(id);return e?`<a class="r-link" href="#map?entity=${encodeURIComponent(id)}">${rEscape(e.name)}</a>`:''}
function refsForEntity(id){return researchData?.evidence.filter(e=>e.entities.includes(id))||[]}
function updateDetailLevel(){
 if(!svg)return;
 const simplify=document.querySelector('#detail-mode')?.value!=='full'&&viewBox[2]>8000;
 svg.classList.toggle('r-overview',simplify);
 if(!svg.dataset.rLevelReady){
  svg.querySelectorAll('text').forEach(t=>{const n=Number(t.getAttribute('font-size'));if(n&&n<28)t.classList.add('r-minor-label')});
  svg.dataset.rLevelReady='true';
 }
}
setView=function(b){originalView(b);updateDetailLevel()};
route=function(){
 const [p,qs='']=(location.hash||'#map').slice(1).split('?');
 if(p==='research'){
  setRoute('research');document.title='宫前证据专题 v2.5 · 北魏洛阳';
  if(researchData){const q=new URLSearchParams(qs);renderResearch(q.get('panel')||'A',q.get('evidence'))}
 }else originalRoute();
};
renderEntity=function(e){
 let base=originalEntity(e);
 const refs=refsForEntity(e.id);if(!refs.length)return base;
 const related=[...new Set(refs.flatMap(x=>x.issues))];
 const targets=[...new Set((e.constraints||[]).map(x=>x.target_id).filter(id=>entityById.has(id)))];
 return base+`<section class="detail-section r-evidence-links"><h3>v2.5 专题证据</h3><p>底图未移动。下面区分正文、校读和项目推理。</p><div class="r-links">${refs.map(x=>`<a class="r-link" href="${researchHref(x.group,x.id)}">${x.id} · ${rEscape(x.kind)}</a>`).join('')}</div><h3>相关研究问题</h3><div class="r-links">${related.map(issueLink).join('')}</div><h3>沿关系查看地点</h3><div class="r-links">${targets.map(entityLink).join('')}</div></section>`;
};
renderIssues=function(){
 originalIssues();if(!researchData)return;
 let filters=document.querySelector('#issue-status-filters');
 if(!filters){filters=document.createElement('div');filters.id='issue-status-filters';filters.className='r-status-filter';$('#issues-list').before(filters)}
 const active=filters.dataset.active||'all';
 const options=[['all','全部记录'],['open','尚待研究'],['conditional','有条件采用'],['clarified','已澄清'],['unlocated','暂不定位']];
 filters.innerHTML=options.map(([id,name])=>`<button data-state="${id}" aria-pressed="${active===id}">${name} ${id==='all'?30:researchData.status_registry.filter(s=>s.status===id).length}</button>`).join('');
 filters.querySelectorAll('button').forEach(b=>b.onclick=()=>{filters.dataset.active=b.dataset.state;renderIssues()});
 $$('.issue-item').forEach(el=>{const s=statusById.get(el.dataset.id);if(s){el.hidden=active!=='all'&&s.status!==active;el.insertAdjacentHTML('beforeend',`<small class="r-status ${s.status}">${rEscape(s.label)}</small>`)}});
};
showIssue=function(id,update=true){
 originalIssue(id,update);const s=statusById.get(id);if(!s)return;
 const selected=$(`.issue-item[data-id="${id}"]`);if(selected)selected.hidden=false;
 const refs=researchData.evidence.filter(e=>e.issues.includes(id));
 const legacy=s.legacy_refs.map(x=>`<p class="r-legacy">旧引文：${rEscape(x.atlas_version)} 专题图 ${x.plate}。${rEscape(x.note)} 原字段与原页码保留。</p>`).join('');
 const sheetsHTML=s.current_sheets.map(ref=>{const sh=sheets.find(x=>x.code===ref.code);return sh?`<a class="r-link" href="./${rEscape(sh.svg)}" target="_blank" rel="noopener">${ref.atlas_version} · ${ref.code}（第${ref.page}页）↗</a>`:''}).join('');
 $('#issue-detail').insertAdjacentHTML('afterbegin',`<div class="r-review"><span class="r-status ${s.status}">${rEscape(s.label)}</span><p>${rEscape(s.review_scope)}。${rEscape(s.note)}</p>${legacy}</div>`);
 $('#issue-detail').insertAdjacentHTML('beforeend',`<section class="r-evidence-links"><h3>专题证据与当前图页</h3><div class="r-links">${refs.map(e=>`<a class="r-link" href="${researchHref(e.group,e.id)}">${e.id} · ${rEscape(e.kind)}</a>`).join('')}${sheetsHTML}</div>${refs.length?'<p><a href="#map?region=R07">返回 R07 地理底图 ↗</a></p>':'<p>本轮未对这项历史问题增加新裁定。</p>'}</section>`);
};
function renderResearch(panel='A',selected=null){
 if(!['A','B','C'].includes(panel))panel='A';
 const record=researchData.panels.find(x=>x.id==='R07-'+panel);
 const entries=researchData.evidence.filter(x=>x.group===panel);
 $('#research-content').innerHTML=`
 <header class="article-header"><div class="eyebrow">EVIDENCE DOSSIER · R07 · v2.5</div><h1>让宫前布局接受逐条检验</h1><p>地理底图 v2.4 不变；本页为有出处的关系专题。节点框不是院墙，方案不提供新的历史坐标。</p></header>
 <nav class="r-tabs" aria-label="专题方案">${researchData.panels.map(p=>`<a href="${researchHref(p.id.slice(-1))}" aria-current="${p.id==='R07-'+panel?'page':'false'}">${p.id} · ${rEscape(p.title)}</a>`).join('')}</nav>
 <div class="r-toolbar"><a class="r-link" href="#map?region=R07">回到 R07 地理底图</a><a class="r-link" href="./${record.path}" target="_blank" rel="noopener">放大／另存矢量图 ↗</a><a class="r-link" href="./downloads/r07-evidence-v25.csv" download>下载18条证据 CSV</a><a class="r-link" href="./downloads/r07-report-v25.html" target="_blank" rel="noopener">完整报告／打印 ↗</a></div>
 <figure class="r-figure"><img id="research-diagram" src="./${record.path}" alt="${rEscape(record.title)}：文献关系示意，无比例尺"><figcaption>† 表示有校补或定位异说。A／B／C分别回答不同问题，不是可以任意拼接的同年实测平面。</figcaption></figure>
 <section><h2>原文 → 校读 → 空间约束 → 本版画法</h2><p>本栏显示本图的 ${entries.length} 条证据；全专题共 ${researchData.evidence.length} 条。来源复用与校者推论不计为独立目击证据。</p>
 <div class="r-cards">${entries.map(e=>`<article id="evidence-${e.id}" class="r-card ${e.id===selected?'r-selected':''}"><div class="r-card-top"><strong>${e.id}</strong><span>${rEscape(e.kind)}</span><a href="${researchHref(e.group,e.id)}" aria-label="固定到${e.id}">#</a></div><blockquote>${rEscape(e.quote)}</blockquote><p class="r-locator">${rEscape(e.locator)}</p><dl><dt>文字可以支持</dt><dd>${rEscape(e.constraint)}</dd><dt>校读与推理</dt><dd>${rEscape(e.interpretation)}</dd><dt>图中处理</dt><dd>${rEscape(e.drawing)}</dd></dl><div class="r-links">${e.sources.map(id=>{const s=researchData.sources.find(x=>x.id===id);return `<a class="r-link" href="${rEscape(s.url)}" target="_blank" rel="noopener">来源 ${id} ↗</a>`}).join('')}${e.issues.map(issueLink).join('')}</div><div class="r-links">${e.entities.map(entityLink).join('')}</div></article>`).join('')}</div></section>
 <section class="r-sources"><h2>来源层次及依赖</h2>${researchData.sources.map(s=>`<details><summary>${s.id} · ${rEscape(s.title)}</summary><p>${rEscape(s.layer)}</p><p>${rEscape(s.dependency)}</p><a href="${rEscape(s.url)}" target="_blank" rel="noopener">打开电子文本 ↗</a></details>`).join('')}<p>本次核查为电子正文与校注对读，未宣称完成所有古刻逐叶校勘；旧v1.1专题页与v2.4图册页码分开登记。</p></section>`;
 if(selected&&entries.some(x=>x.id===selected))requestAnimationFrame(()=>document.getElementById('evidence-'+selected)?.scrollIntoView({block:'start',behavior:'instant'}));
}
async function initResearch(){
 try{
  const response=await fetch('./data/research-v25.json');if(!response.ok)throw Error('专题数据HTTP '+response.status);
  researchData=await response.json();researchData.status_registry.forEach(s=>statusById.set(s.id,s));
  for(let n=0;n<400&&!svg;n++)await new Promise(resolve=>setTimeout(resolve,50));
  if(!svg)throw Error('基础地图未就绪');
  renderIssues();if(selectedIssue)showIssue(selectedIssue,false);if(selectedEntity)selectEntity(selectedEntity,false,false);
  const tools=$('.map-tools');tools.insertAdjacentHTML('beforeend','<label class="r-detail-label">细注 <select id="detail-mode" aria-label="地图细注显示"><option value="auto">随缩放</option><option value="full">全部</option></select></label>');
  $('#detail-mode').addEventListener('change',updateDetailLevel);updateDetailLevel();
  $('.empty-inspector')?.insertAdjacentHTML('beforeend','<p><a class="r-link" href="#research?panel=A">查看宫前证据专题 v2.5 ↗</a></p>');
  document.documentElement.dataset.researchReady='true';route();
 }catch(error){console.error(error);$('#research-content').textContent='专题加载失败：'+error.message;document.documentElement.dataset.researchReady='error'}
}
initResearch();
