/* v2.7: typed paths and event windows; never turn unobserved state into a fact. */
let network27=null;
const routeBefore27=route,entityBefore27=renderEntity;
pageIds.push('network');
const n27escape=value=>escapeHTML(value);
function n27url(values={}){return '#network?'+new URLSearchParams(values).toString()}
route=function(){
 const [p,qs='']=(location.hash||'#map').slice(1).split('?');
 if(p==='network'){
  setRoute('network');document.title='水陆与事件 v2.7 · 北魏洛阳';
  if(network27)renderNetwork27(new URLSearchParams(qs));
 }else routeBefore27();
};
renderEntity=function(entity){
 const base=entityBefore27(entity);
 if(!network27)return base;
 const passages=network27.passages.filter(p=>p.map_ids.includes(entity.id));
 if(!passages.length)return base;
 return base+'<section class="detail-section"><h3>水陆关系与事件范围 v2.7</h3><p>相关段落不自动给出此址的全年通行或毁后状态。</p><div class="r-links">'+passages.map(p=>'<a class="r-link" href="'+n27url({tab:'evidence',item:p.id})+'">'+p.id+' · '+n27escape(p.anchor.split('；')[0])+'</a>').join('')+'<a class="r-link" href="'+n27url({tab:'events',entity:entity.id,year:547})+'">查看相关事件</a></div></section>';
};
function position27(event,year){
 if(event.start===null)return 'undated_reference';
 if(year<event.start)return 'event_not_yet_in_recorded_window';
 if(year>event.end)return 'past_event_later_state_unknown';
 return event.start===event.end?'event_in_selected_year':'year_inside_uncertain_event_window';
}
function n27evidence(id){return '<a class="n27-chip" href="'+n27url({tab:'evidence',item:id})+'">'+n27escape(id)+'</a>'}
function renderNetwork27(params){
 const tab=['network','events','evidence','audit'].includes(params.get('tab'))?params.get('tab'):'network';
 const root=$('#network-content'),e=n27escape;
 root.innerHTML='<header class="article-header"><div class="eyebrow">TEXTUAL NETWORKS & EVENT SCOPE · v2.7</div><h1>哪些连接有依据，哪些变化只作用于一部分？</h1><p>先分开水流、道路和跨越，再检验接缝。事件标注的是发生范围，不是把整座城自动设为同一种状态。</p></header>'+
 '<div class="n27-statbar"><span><strong>'+network27.passages.length+'</strong>段落证据</span><span><strong>'+network27.edges.length+'</strong>分类型关系</span><span><strong>'+network27.scenarios.length+'</strong>前提／来源组合</span><span><strong>'+network27.events.length+'</strong>作用范围明确的事件</span></div>'+
 '<nav class="r-tabs" aria-label="水陆与事件页面">'+[['network','水陆网络'],['events','事件时间层'],['evidence','原文与解释'],['audit','全城审阅账本']].map(([k,t])=>'<a href="'+n27url({tab:k})+'" aria-current="'+(k===tab?'page':'false')+'">'+t+'</a>').join('')+'</nav>'+
 '<div class="r-toolbar"><a class="r-link" href="./downloads/network-study-v27.html" target="_blank" rel="noopener">独立研究报告／打印 ↗</a><a class="r-link" href="./data/network-v27.json" download>网络与路径JSON</a><a class="r-link" href="./downloads/network-edges-v27.csv" download>关系CSV</a><a class="r-link" href="./downloads/events-v27.csv" download>事件CSV</a><a class="r-link" href="#map">回到全城基准图</a></div><div id="n27-body"></div>';
 if(tab==='events')return events27(params);
 if(tab==='evidence')return evidence27(params.get('item'));
 if(tab==='audit')return audit27();
 const joins=['J1','J2','J3','FLOOD'].map(k=>params.get(k)==='1');
 const source=['LW','L','W'].includes(params.get('source'))?params.get('source'):'LW';
 const caseId='n'+joins.map(b=>b?'1':'0').join('')+'-'+source;
 const scenario=network27.scenarios.find(s=>s.id===caseId);
 const panel=network27.panels.find(p=>p.id===params.get('panel'))||network27.panels[0];
 const body=$('#n27-body');
 body.innerHTML='<section class="n27-controls"><h2>先把接缝条件写明</h2><label>来源组 <select id="n27-source"><option value="LW">L《伽蓝记》＋W《水经注》</option><option value="L">只留L</option><option value="W">只留W</option></select></label><p>来源组删减用于检验依赖；L的不同整理本不是多份独立证据。</p><div class="n27-joins">'+network27.decisions.map((d,i)=>'<label><input type="checkbox" data-join="'+d.id+'" '+(joins[i]?'checked':'')+'><span><strong>'+d.id+' · '+e(d.title)+'</strong><small>'+e(d.limit)+'</small></span></label>').join('')+'</div></section>'+
 '<section class="n27-results"><h2>这组前提能建立哪些路径？</h2><p class="n27-warning">“未建立”不是“历史上不连通”。证明路径只使用对应类型的边；跨越、对齐不会混入水流。所有段落尚未被同步到某一个具体年份。</p><div class="n27-table-wrap"><table id="n27-queries"><thead><tr><th>问题</th><th>模型结果</th><th>可回查的路径</th></tr></thead><tbody>'+scenario.queries.map(q=>{
 const names=Object.fromEntries(network27.nodes.map(n=>[n.id,n.name]));
 return '<tr data-query="'+q.id+'"><th>'+q.id+' · '+e(q.title)+'</th><td><span class="n27-status '+q.status+'">'+(q.status==='supported_under_conditions'?'本条件下可建立':'材料未建立')+'</span><small>'+e(q.mode==='flow'?'仅水流边':q.mode==='route'?'仅本段叙述行进':'桥梁身份假设')+'</small></td><td>'+q.evidence.map(n27evidence).join(' ')+(q.edge_ids.length?'<details><summary>展开路径与前提</summary><p>'+q.nodes.map(n=>e(names[n]||n)).join(' → ')+'</p><p>边：'+e(q.edge_ids.join(' → '))+'</p><p>额外前提：'+e(q.premises.join('、')||'无本页可开关接缝；仍有一般语义与时层限制')+'</p><p>'+e(q.qualification)+'</p></details>':'<p>'+e(q.qualification)+'</p>')+'</td></tr>';
 }).join('')+'</tbody></table></div></section>'+
 '<section class="n27-diagrams"><h2>分区阅读：四种关系不能画成一条线</h2><nav class="r-tabs">'+network27.panels.map(p=>'<a href="'+n27url({...Object.fromEntries(params),panel:p.id})+'" aria-current="'+(panel.id===p.id?'page':'false')+'">'+e(p.title.split('：')[0])+'</a>').join('')+'</nav><figure><img id="n27-diagram" src="./'+panel.path+'" alt="'+e(panel.title)+' 文本网络，无地理比例尺"><figcaption>图为各段叙述的索引。虚线表示条件或对齐；当前是否启用接缝，请以上方路径表为准。<a href="./'+panel.path+'" target="_blank" rel="noopener">放大SVG ↗</a></figcaption></figure></section>'+
 '<section class="n27-limit"><h2>为什么还没有把水线全部接回母图？</h2>'+network27.limits.map(x=>'<p>'+e(x)+'</p>').join('')+'<p>同门、同名、图面接近均不足以直接认定同一水段。原母图没有被这些示意线替换。</p></section>';
 $('#n27-source').value=source;
 const update=()=>{const p=new URLSearchParams(params);p.set('source',$('#n27-source').value);$$('[data-join]').forEach(x=>p.set(x.dataset.join,x.checked?'1':'0'));location.hash='network?'+p.toString()};
 $('#n27-source').onchange=update;$$('[data-join]').forEach(x=>x.onchange=update);
 document.documentElement.dataset.networkCase=caseId;
}
function evidence27(selected){
 const e=n27escape;
 $('#n27-body').innerHTML='<h2>原句、解释与未定范围</h2><p>原文短引与本项目解释分栏；电子文本已核不等于古刻书影逐叶校勘。PDF页码是电子重排页码。</p><div class="n27-cards">'+network27.passages.map(p=>{
 const source=network27.sources.find(s=>s.id===p.source);
 return '<article id="n27-'+p.id+'" class="n27-card '+(selected===p.id?'selected':'')+'"><h3>'+p.id+' · '+e(p.anchor)+'</h3><blockquote>'+e(p.quote)+'</blockquote><h4>解释及限制</h4><p>'+e(p.reading)+'</p><p><a href="'+e(source.url)+'" target="_blank" rel="noopener">'+e(source.title)+' ↗</a></p><small>'+e(source.note)+'</small><div class="r-links">'+p.map_ids.map(id=>'<a class="r-link" href="#map?entity='+encodeURIComponent(id)+'">'+e(entityById.get(id)?.name||id)+'</a>').join('')+'</div></article>';
 }).join('')+'</div>';
 if(selected)requestAnimationFrame(()=>document.getElementById('n27-'+selected)?.scrollIntoView({block:'start'}));
}
function events27(params){
 const parsed=Number(params.get('year')||547);const year=Number.isInteger(parsed)&&parsed>=1&&parsed<=600?parsed:547;
 const entity=params.get('entity');const selected=network27.events.filter(e=>!entity||e.object===entity);const e=n27escape;
 $('#n27-body').innerHTML='<section class="n27-controls"><h2>看事件，不把事件无限延续成状态</h2><label>比较年份 <input id="n27-year" type="number" min="1" max="600" value="'+year+'"></label><div class="n27-years">'+[516,526,527,534,546,547].map(y=>'<a class="r-link" href="'+n27url({tab:'events',year:y,...(entity?{entity}: {})})+'">'+y+'</a>').join('')+'</div><p class="n27-warning">527桥毁不自动意味着547仍不可通行；534塔火不等于全寺烧尽；520—525“始造”不能推成526还在建。尚未获得逐对象的持续状态证据。</p>'+(entity?'<p>当前只看 '+e(entityById.get(entity)?.name||entity)+'。<a href="'+n27url({tab:'events',year})+'">显示全部事件</a></p>':'')+'</section><div id="n27-event-cards" class="n27-cards">'+selected.map(ev=>{
 const status=position27(ev,year);
 return '<article class="n27-card" data-event="'+ev.id+'" data-status="'+status+'"><h3>'+ev.id+' · '+e(ev.name)+'</h3><p><strong>'+e(ev.original_date)+'</strong> · '+(ev.start===null?'未强定公元年':ev.start===ev.end?ev.start:ev.start+'—'+ev.end)+'</p><span class="n27-status '+status+'">'+e(network27.event_labels[status])+'</span><dl><dt>作用范围</dt><dd>'+e(ev.scope)+'</dd><dt>不能据此推出</dt><dd>'+e(ev.state_note)+'</dd></dl><div class="r-links">'+n27evidence(ev.evidence)+(ev.object?'<a class="r-link" href="#map?entity='+ev.object+'">回相关对象</a>':'<span class="n27-chip">城市级观察／事件，不下传全部建筑</span>')+'</div></article>';
 }).join('')+(selected.length?'':'<p class="n27-empty">本批未给这个对象登记可用的定年事件。这不意味着它未曾变化，更不意味着可以填一个猜测日期。</p>')+'</div><h2>547年对照图现在能够做到什么？</h2><p>可以标出此前已记的塔火、桥毁、迁都和移石经；不能把事件后的未知修复或残存状态自动补全。全城毁后图仍需逐址证据，原序总体景象单独保留。</p>';
 $('#n27-year').onchange=()=>location.hash=n27url({tab:'events',year:$('#n27-year').value,...(entity?{entity}:{})});
}
function audit27(){
 const e=n27escape;const labels={scoped_events_sampled:'已整理部分作用范围事件',passages_reviewed_no_dated_event_added:'本批相关段落已读，未新增定年事件',event_series_not_reviewed:'事件序列尚未专项审阅'};
 $('#n27-body').innerHTML='<h2>339对象：审阅范围也必须留下记录</h2><p>本表保存原年代分类，不将它等同完整事件年表。所有有效起止年仍留空，直到有专门证据支持。</p><a class="r-link" href="./downloads/event-audit-v27.csv" download>下载全部审阅账本</a><div class="n27-table-wrap"><table id="n27-audit"><thead><tr><th>对象</th><th>本轮事件审阅</th><th>原年代分类</th><th>已整理事件</th></tr></thead><tbody>'+network27.event_audit.map(a=>'<tr><th><a href="#map?entity='+a.entity_id+'">'+e(a.name)+'</a></th><td>'+e(labels[a.status])+'</td><td>'+e(a.legacy_temporal_state||'原字段未填')+'</td><td>'+a.event_ids.map(id=>'<a class="n27-chip" href="'+n27url({tab:'events',entity:a.entity_id,year:547})+'">'+id+'</a>').join(' ')+'</td></tr>').join('')+'</tbody></table></div>';
}
(async function(){
 try{
  const response=await fetch('./data/network-v27.json');if(!response.ok)throw Error('v2.7数据 HTTP '+response.status);network27=await response.json();
  for(let n=0;n<600&&document.documentElement.dataset.model26Ready!=='true';n++)await new Promise(resolve=>setTimeout(resolve,50));
  if(document.documentElement.dataset.model26Ready!=='true')throw Error('基础研究模块未就绪');
  document.documentElement.dataset.network27Ready='true';
  if(selectedEntity)selectEntity(selectedEntity,false,false);route();
 }catch(error){console.error(error);document.documentElement.dataset.network27Ready='error';$('#network-content').textContent='水陆专题加载失败：'+error.message;}
})();
