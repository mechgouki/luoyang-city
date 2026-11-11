/* v2.6: display computed constraint results, never infer geometry in the UI. */
let milestone26=null, registry26=null;
const routeBefore26=route, entityBefore26=renderEntity;
const m26State={entailed:'模型内必然',contradicted:'模型内排除',undetermined:'未能限定',inconsistent:'前提不相容'};
const m26Targets={explicit_id:'既有ID引用',name_unique:'单名匹配·身份待审',name_ambiguous:'同名多候选',name_variant_candidate:'去限定语候选',compound_expression:'复合表述未拆定',unresolved:'目标待核'};
pageIds.push('model');
function m26url(caseId='s011',tab='plans',extra={}){return '#model?'+new URLSearchParams({case:caseId,tab,...extra}).toString()}
route=function(){
 const [p,qs='']=(location.hash||'#map').slice(1).split('?');
 if(p==='model'){
  setRoute('model');document.title='可检验空间复原 v2.6 · 北魏洛阳';
  if(milestone26&&registry26)render26(new URLSearchParams(qs));
 }else routeBefore26();
};
renderEntity=function(e){
 let s=entityBefore26(e);
 if(milestone26&&milestone26.atoms.some(a=>a.less===e.id||a.more===e.id||a.node===e.id))
  s+='<section class="detail-section"><h3>检验这些关系能推出什么</h3><p>v2.6提供条件开关、可行反例和来源删减检验。</p><a class="r-link" href="'+m26url()+'">打开R07空间检验 ↗</a></section>';
 return s;
};
function atomLink26(id,caseId){return '<a class="m26-chip" href="'+m26url(caseId,'atoms',{atom:id})+'">'+escapeHTML(id)+'</a>'}
function resultRows26(c){return c.queries.map(q=>'<tr><th>'+escapeHTML(q.title)+'</th><td><span class="m26-state '+q.status+'">'+m26State[q.status]+'</span></td><td>'+q.support_subset.map(id=>atomLink26(id,c.id)).join(' ')+(q.support_subset.length?'':'没有充分支持集')+'</td></tr>').join('')}
function render26(params){
 const caseId=params.get('case')||'s011';const c=milestone26.cases.find(c=>c.id===caseId)||milestone26.cases.find(c=>c.id==='s011');
 const tab=['plans','atoms','relations','sensitivity'].includes(params.get('tab'))?params.get('tab'):'plans';
 const e=escapeHTML;const root=$('#model-content');
 root.innerHTML='<header class="article-header"><div class="eyebrow">R07 · TESTABLE RECONSTRUCTION · v2.6</div><h1>文献究竟限定了哪些位置？</h1><p>把前提写清，再看可行平面如何变化。原始母图不动；此处不提供米制坐标，也不把可满足当作历史事实。</p></header>'+
 '<div class="m26-statbar"><span><strong>482</strong>关系无损索引</span><span><strong>'+milestone26.atoms.length+'</strong>判断与前提</span><span><strong>'+milestone26.cases.length+'</strong>检验情形</span><span><strong>0</strong>旧地图坐标输入</span></div>'+
 '<nav class="r-tabs" aria-label="空间检验功能">'+[['plans','候选平面'],['sensitivity','前提敏感性'],['atoms','逐条判断'],['relations','全量关系索引']].map(([id,t])=>'<a aria-current="'+(tab===id?'page':'false')+'" href="'+m26url(c.id,id)+'">'+t+'</a>').join('')+'</nav>'+
 '<div class="m26-downloads"><a class="r-link" href="#map?region=R07">回v2.4母图R07</a><a class="r-link" href="./downloads/r07-study-v26.html" target="_blank" rel="noopener">完整研究说明／打印 ↗</a><a class="r-link" href="./downloads/relations-v26.csv" download>482条关系CSV</a><a class="r-link" href="./downloads/atoms-v26.csv" download>判断与前提CSV</a><a class="r-link" href="./downloads/sensitivity-v26.csv" download>敏感性CSV</a><a class="r-link" href="./data/milestone-v26.json" download>结果与证书JSON</a></div><div id="m26-body"></div>';
 if(tab==='relations'){renderRelations26();return}
 const body=$('#m26-body');
 body.innerHTML='<section class="m26-controls"><label for="m26-case">检验情形</label><select id="m26-case">'+milestone26.cases.map(x=>'<option value="'+x.id+'" '+(x.id===c.id?'selected':'')+'>'+e(x.id+' · '+x.title)+'</option>').join('')+'</select><p>'+e(c.question)+'</p><div class="m26-quick"><a href="'+m26url('s011')+'">太尉两种路侧</a><a href="'+m26url('s110')+'">撤去景乐补东</a><a href="'+m26url('ritual111')+'">庙社条件性冲突</a></div></section>';
 $('#m26-case').onchange=ev=>location.hash=m26url(ev.target.value,tab);
 if(tab==='atoms'){renderAtoms26(c,params.get('atom'));return}
 if(tab==='sensitivity'){renderSensitivity26(c);return}
 if(/^s[01]{3}$/.test(c.id)){
  body.insertAdjacentHTML('beforeend','<div class="m26-switches">'+[['west_side','西侧序列继承'],['east_side','东侧序列继承'],['jingle_east','采用景乐〈东〉补字']].map(([g,t])=>'<label><input type="checkbox" data-assumption="'+g+'" '+(c.enabled.includes(g)?'checked':'')+'>'+t+'</label>').join('')+'</div>');
  $$('.m26-switches input').forEach(input=>input.onchange=()=>{const bits=$$('.m26-switches input').map(el=>el.checked?'1':'0').join('');location.hash=m26url('s'+bits)});
 }
 body.insertAdjacentHTML('beforeend','<div class="m26-premise"><strong>当前启用的额外前提：</strong>'+c.enabled.map(g=>e(milestone26.groups[g])).join('；')+'。<details><summary>所有情形共同的限制</summary>'+milestone26.source_review.fixed_global_assumptions.map(t=>'<p>'+e(t)+'</p>').join('')+'<p>'+e(milestone26.model_scope)+'</p></details></div>');
 if(!c.sat){
  body.insertAdjacentHTML('beforeend','<div id="m26-conflict" class="m26-conflict"><h2>这组前提不能同时满足</h2><p>不是“某本史书必定错误”。下面显示两个分别对应庙、社的子集极小冲突；不声称它们是全部冲突或最少条数。</p>'+c.conflict_cores.map((ids,i)=>'<p><strong>冲突集 '+(i+1)+'</strong> '+ids.map(id=>atomLink26(id,c.id)).join(' ')+'</p>').join('')+'<p>分别撤去“同体”“同时”或“同城界”均可消除此类冲突；这不证明任何一种替代史实。</p></div>');
 }else{
  const plans=milestone26.candidates.filter(p=>p.case_id===c.id);
  if(plans.length){
   const plan=plans.find(p=>p.selected_side===params.get('pick'))||plans[0];
   body.insertAdjacentHTML('beforeend','<section class="m26-plan"><div class="m26-plan-buttons">'+plans.map(p=>'<a aria-current="'+(p.id===plan.id?'page':'false')+'" href="'+m26url(c.id,'plans',{pick:p.selected_side})+'">'+e(milestone26.names[p.focus_id])+'道'+(p.selected_side==='west'?'西':'东')+' · 可行例</a>').join('')+'<a href="./'+plan.path+'" target="_blank" rel="noopener">放大SVG ↗</a></div><p class="m26-map-warning">这些示例使用同一参照与显示范围。点位由约束求解；间距、门北置和标签排版没有史实含义。未展示所有可行连续位置。</p><figure><img id="m26-plan-image" src="./'+plan.path+'" alt="'+e(plan.id)+' 定性平面可行例"><figcaption>'+e(plan.id)+' · 空心点表示路侧未限定。无道路宽度和建筑不相交约束，不是可施工的建筑平面。</figcaption></figure></section>');
  }else body.insertAdjacentHTML('beforeend','<p class="m26-premise">此项用于检验身份、来源或时相，不强行增加具有虚假地址的“第二张地图”。结果见下表。</p>');
 }
 body.insertAdjacentHTML('beforeend','<h2>在这些前提下，哪些结论成立？</h2><div class="m26-table-wrap"><table class="m26-table"><thead><tr><th>问题</th><th>结果</th><th>一个充分支持集（包含依赖）</th></tr></thead><tbody>'+resultRows26(c)+'</tbody></table></div><p>“必然”仅对当前模型成立；来源复用不计为多票。所有数值尺度仍未限定。</p>');
}
function renderAtoms26(c,chosen){
 const e=escapeHTML;const body=$('#m26-body');
 body.insertAdjacentHTML('beforeend','<p>69条记录覆盖18张证据卡，包含直接方向投影、非执行注记和额外前提；不是69份独立史料。灰色卡未在当前情形启用。</p><div class="m26-atoms">'+milestone26.atoms.map(a=>'<article id="atom-'+a.id+'" class="m26-atom '+(c.active_ids.includes(a.id)?'':'inactive ')+(chosen===a.id?'selected':'')+'"><header><strong>'+e(a.id)+'</strong><span>'+e(a.layer)+'</span><span>'+e(a.kind)+'</span></header><blockquote>'+e(a.quote)+'</blockquote><p>'+e(a.source_locator)+'</p><p>来源组 '+e(a.families.join('/')||'项目推理')+'；前提组 '+e(a.group)+'；依赖 '+a.requires.map(id=>atomLink26(id,c.id)).join(' ')+'</p><p><a class="r-link" href="#research?panel='+a.evidence_panel+'&evidence='+a.evidence_id+'">回到 '+a.evidence_id+' 原文／校注 ↗</a></p><details><summary>机器表达</summary><pre>'+e(JSON.stringify(a,null,2))+'</pre></details></article>').join('')+'</div>');
 if(chosen)requestAnimationFrame(()=>document.getElementById('atom-'+chosen)?.scrollIntoView({block:'start'}));
}
function renderSensitivity26(c){
 const body=$('#m26-body');const e=escapeHTML;
 body.insertAdjacentHTML('beforeend','<p>比较8组路侧／校补前提、3次删源、3个冲突前提的单独放松与官名试合并。H可能依赖L，以下不是独立证据或概率统计。</p><div class="m26-table-wrap"><table id="m26-sensitivity" class="m26-table"><thead><tr><th>检验情形</th>'+milestone26.cases[0].queries.map(q=>'<th>'+e(q.title)+'</th>').join('')+'</tr></thead><tbody>'+milestone26.cases.map(c=>'<tr><th><a href="'+m26url(c.id)+'">'+e(c.title)+'</a></th>'+c.queries.map(q=>'<td><span class="m26-state '+q.status+'">'+m26State[q.status]+'</span></td>').join('')+'</tr>').join('')+'</tbody></table></div><h2>尺度仍然没有被确定</h2><p>严格方位关系在任意正比例缩放后保持不变。本页不会给未有长度依据的对象画出有限“置信区间”，也不把两个可行例说成各有50%的概率。</p>');
}
function renderRelations26(){
 const body=$('#m26-body');const e=escapeHTML;const stats=registry26.metrics.target_status;
 body.innerHTML='<h2>482条关系：原文保留，统一索引</h2><p>复核纠正：321条target字段中85条本来是实体ID。245条引用可在现有实体表验证；单名匹配只供候选关联，身份仍待审。city_jinyang这一旧ID缺少实体，未自动补造。</p><div class="m26-controls"><label for="m26-target-filter">目标处理状态</label><select id="m26-target-filter"><option value="all">全部 482</option>'+Object.entries(stats).map(([s,n])=>'<option value="'+s+'">'+e(m26Targets[s]||s)+' '+n+'</option>').join('')+'</select><input id="m26-relation-search" type="search" placeholder="搜索名称、ID、原关系或引文" aria-label="搜索规范化关系"></div><p id="m26-relation-count"></p><div class="m26-table-wrap"><table class="m26-table"><thead><tr><th>记录／主体</th><th>原关系</th><th>目标原值</th><th>候选与状态</th><th>原始记录</th></tr></thead><tbody id="m26-relation-rows"></tbody></table></div>';
 function list(){const status=$('#m26-target-filter').value,q=$('#m26-relation-search').value.trim().toLowerCase();
  const found=registry26.records.filter(r=>(status==='all'||r.target.status===status)&&(!q||JSON.stringify(r).toLowerCase().includes(q)||(milestone26.names[r.subject_id]||'').includes(q)));
  $('#m26-relation-count').textContent='显示 '+found.length+' / 482 条。全部保留，未解析不是删除。';
  $('#m26-relation-rows').innerHTML=found.map(r=>'<tr><th><small>'+e(r.id)+'</small><br><a href="#map?entity='+encodeURIComponent(r.subject_id)+'">'+e(milestone26.names[r.subject_id]||r.subject_id)+'</a></th><td>'+e(r.relation_raw)+'</td><td>'+e(String(r.target.raw))+'</td><td>'+e(m26Targets[r.target.status]||r.target.status)+'<br>'+r.target.candidates.map(id=>e(milestone26.names[id]||id)).join(' / ')+'</td><td><details><summary>原文／原字段</summary><p>'+e(r.source.quote||'此记录未载引文')+'</p><p>'+e(r.source.locator||'定位待补')+'</p><pre>'+e(JSON.stringify(r.original,null,2))+'</pre></details></td></tr>').join('');
 }
 $('#m26-target-filter').onchange=list;$('#m26-relation-search').oninput=list;list();
}
(async function(){
 try{
  const [a,b]=await Promise.all([fetch('./data/milestone-v26.json'),fetch('./data/relations-v26.json')]);
  if(!a.ok||!b.ok)throw Error('v2.6数据加载失败');[milestone26,registry26]=await Promise.all([a.json(),b.json()]);
  document.documentElement.dataset.model26Ready='true';
  for(let i=0;i<400&&document.documentElement.dataset.researchReady!=='true';i++)await new Promise(r=>setTimeout(r,50));
  if(selectedEntity)selectEntity(selectedEntity,false,false);route();
 }catch(error){console.error(error);document.documentElement.dataset.model26Ready='error';$('#model-content').textContent=error.message}
})();
