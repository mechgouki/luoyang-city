/* Read the same city through documentary relations and separately evidenced geography. */
(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const all = s => [...document.querySelectorAll(s)];
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const kindLabels = {temple:'寺院',palace:'宫殿',city_gate:'城门',gate:'门',office:'官署',ward:'坊里',market:'市场',house:'宅第',residence:'宅第',bridge:'桥',road:'道路',water:'水体',river:'河流',watercourse:'水道',watercourse_region:'水系地域',pool:'池',garden:'园苑',hill:'山地',artificial_hill:'人工山',school:'学校',altar:'礼制设施',enclosure:'范围',area:'区域',city:'城址',tower:'塔',platform:'台',tomb:'冢墓',pass:'关口'};
  Object.assign(kindLabels,{county_site:'县治旧址',enclosure_gate:'围界门',former_market:'旧市',former_office:'旧署',former_residence:'旧宅',former_structure:'旧建筑',former_ward:'旧坊',garden_complex:'园苑群',grove:'林地',hill_or_palace_structure_disputed:'山地或宫苑构筑（有争议）',historical_site:'历史旧址',mountain_region:'山地区域',named_place_unknown_function:'名称存载、用途待考',palace_gate:'宫门',palace_structure:'宫苑建筑',pond:'池',regional_landmark:'地域参照',reserved_site:'待考地点',residence_building:'宅第建筑',ritual_site:'礼制场所',stele:'碑',storehouse:'仓储',training_ground:'校场',weir:'堰',well:'井'});
  const geographicLabels = {source_mapped_extent:'来源图已有位置参照',verified_point:'已核验位置',candidate_area:'候选范围',relative_only:'仅有相对关系',unlocated:'尚未地理定位'};
  const viewNames = {plan:'盛时文献平面',geography:'地形与城市布局',panorama:'由布局生成的城市全景'};
  let data, rows = [], entities = new Map(), targetEntities = new Map(), sourceFeatures = new Map();
  let state = {view:'plan',entity:'',region:'all',kind:'all',q:'',group:'',feature:'',modern:false};
  let svg = null, renderedView = null, box = null, baseBox = null, serial = 0, features = [];
  const mapCache = new Map(), viewBoxes = new Map();

  function safeUrl(value) {
    if (!value) return null;
    try { const u = new URL(value, location.href); return ['http:','https:'].includes(u.protocol) ? u.href : null; }
    catch { return null; }
  }
  function link(value, label, external = false) {
    const href = safeUrl(value);
    return href ? '<a href="' + esc(href) + '"' + (external ? ' target="_blank" rel="noopener"' : '') + '>' + esc(label) + '</a>' : esc(label);
  }
  function strings(value) {
    if (value === null || value === undefined) return [];
    return (Array.isArray(value) ? value : [value]).map(x => typeof x === 'string' ? x : (x.note || x.text || x.title || '')).filter(Boolean);
  }
  function paragraphs(value) { return strings(value).map(x => '<p>' + esc(x) + '</p>').join(''); }
  function validBox(value) { return Array.isArray(value) && value.length === 4 && value.every(Number.isFinite) && value[2] > 0 && value[3] > 0; }
  function availableViews() { return ['plan','geography','panorama'].filter(v => data.maps?.[v]?.url); }
  function regionFor(id) { return (data.regions || []).find(r => r.id === id); }
  function nameFor(id) { return entities.get(id)?.name || id; }
  function sourceFeatureFor(node) { return sourceFeatures.get(node.getAttribute('data-feature-id')); }
  function featureTitle(feature) { return feature.title || feature.label || feature.id; }
  function membersForGroup(key) {
    if(!key)return [];
    return [...new Set(targetEntities.get(key)||key.split(',').filter(id=>entities.has(id)))];
  }

  function readHash() {
    const q = new URLSearchParams(location.hash.slice(1));
    const requested = q.get('view');
    const view=availableViews().includes(requested) ? requested : availableViews()[0];
    const feature=view!=='plan'&&sourceFeatures.has(q.get('feature'))?q.get('feature'):'';
    const group=!feature&&membersForGroup(q.get('group')).length>1?q.get('group'):'';
    state = {
      view,
      entity:feature?'':entities.has(q.get('entity')) ? q.get('entity') : (group?'':(entities.has('ic_yongning') ? 'ic_yongning' : data.entities[0]?.id || '')),
      region:regionFor(q.get('region')) ? q.get('region') : 'all',
      kind:[...new Set(data.entities.map(e => e.kind))].includes(q.get('kind')) ? q.get('kind') : 'all',
      q:q.get('q') || '',
      group,
      feature,
      modern:q.get('modern') === '1',
    };
  }
  function writeHash(replace = false) {
    const q = new URLSearchParams({view:state.view});
    if (state.entity) q.set('entity',state.entity);
    if (state.region !== 'all') q.set('region',state.region);
    if (state.kind !== 'all') q.set('kind',state.kind);
    if (state.q) q.set('q',state.q);
    if (state.group) q.set('group',state.group);
    if (state.feature) q.set('feature',state.feature);
    if (state.modern) q.set('modern','1');
    const hash = '#' + q.toString();
    if (location.hash !== hash) history[replace ? 'replaceState' : 'pushState'](null,'',hash);
  }
  function filteredEntities() {
    const q = state.q.trim().toLocaleLowerCase();
    const region = regionFor(state.region);
    const members=membersForGroup(state.group);
    return data.entities.filter(e => (!members.length || members.includes(e.id)) && (!region || (region.entity_ids || []).includes(e.id)) &&
      (state.kind === 'all' || e.kind === state.kind) &&
      (!q || [e.id,e.name,e.display_name,...(e.aliases || [])].some(v => String(v || '').toLocaleLowerCase().includes(q))));
  }
  function normalizeSelection() {
    rows = filteredEntities();
    if(state.view==='plan')state.feature='';
    if(state.feature&&sourceFeatures.has(state.feature)){state.entity='';return;}
    if (!rows.some(e => e.id === state.entity)) state.entity = state.group?'':rows[0]?.id || '';
  }
  async function change(patch, options = {}) {
    const oldRegion = state.region;
    state = {...state,...patch};
    normalizeSelection(); writeHash(!!options.replace);
    await render();
    if (options.focus) focusSelection();
    else if (oldRegion !== state.region) focusRegion();
  }

  function evidenceHTML(e) {
    const source = (data.sources || []).find(s => s.id === e.source_id);
    return '<article class="evidence-card"><span class="record-id">' + esc(e.id || e.source_id || '') + '</span>' +
      '<h4>' + esc(e.title || '相关记录') + '</h4>' +
      (e.quote ? '<blockquote>' + esc(e.quote) + '</blockquote>' : '') +
      paragraphs(e.reading || e.note) +
      (e.locator ? '<p class="muted">' + esc(e.locator) + '</p>' : '') +
      ((e.url || source?.url) ? link(e.url || source.url, e.link_label || '查看记录与出处 ↗', true) : '') + '</article>';
  }
  function selectedMembers() {
    const e = entities.get(state.entity);
    if (!e || state.view !== 'plan') return [];
    const ids = new Set([...(e.plan_target_ids || []).flatMap(id => targetEntities.get(id) || []),...(state.group?membersForGroup(state.group):[])]);
    return [...ids].filter(id => id !== e.id);
  }
  function renderFeatureDetail(feature) {
    const source=(data.sources||[]).find(s=>s.id===feature.source_id);
    const pages=(feature.source_pages||[]).map(String);
    const modern=feature.id.startsWith('geo-modern-');
    $('#entity-select').disabled=false;$('#entity-select').value='';
    let html='<section data-source-feature-detail="'+esc(feature.id)+'"><span class="record-id">'+esc(feature.id)+'</span><h2>'+esc(featureTitle(feature))+'</h2><span class="pill">'+(modern?'现代地理参照':'来源图要素')+'</span>';
    html+='<p class="muted">按来源图记录的线、范围或标注，与文献地点名录分别保存。</p><h3>图示与位置依据</h3><div class="placement-note">'+paragraphs(feature.placement_note)+'</div>';
    if(feature.source_period)html+='<h3>来源材料时层</h3>'+paragraphs(feature.source_period);
    if(feature.source_historical_period)html+='<h3>来源标注的历史时层</h3>'+paragraphs(feature.source_historical_period);
    if(feature.temporal_interpretation)html+='<h3>本版怎样判断时层</h3>'+paragraphs(feature.temporal_interpretation);
    if(modern)html+='<p class="muted">本要素由“现代地理参照”开关控制；它的时层与北魏城市分布分别阅读。</p>';
    if(source){
      html+='<article class="evidence-card"><span class="record-id">'+esc(source.id)+'</span><h4>'+esc(source.title||source.id)+'</h4>'+paragraphs(source.period||source.source_period)+paragraphs(source.note);
      if(pages.length)html+='<p class="muted">来源 PDF 页码：'+esc(pages.join('、'))+'</p>';
      html+=link(feature.source_url||source.url,'打开这一图件的来源 ↗',true)+'</article>';
    }else if(feature.source_url)html+='<div class="detail-links">'+link(feature.source_url,'打开这一图件的来源 ↗',true)+'</div>';
    if(feature.limitations)html+='<h3>仍需保留的问题</h3>'+paragraphs(feature.limitations);
    if(feature.entity_id&&entities.has(feature.entity_id))html+='<div class="related-members"><button type="button" data-entity-open="'+esc(feature.entity_id)+'">查看文献地点：'+esc(nameFor(feature.entity_id))+'</button></div>';
    html+='</section>';
    $('#entity-detail').innerHTML=html;
    $('#entity-detail').querySelectorAll('[data-entity-open]').forEach(b=>b.addEventListener('click',()=>selectEntity(b.dataset.entityOpen).catch(fail)));
    updateSelection();
  }
  function renderDetail() {
    const sourceFeature=sourceFeatures.get(state.feature);
    if(sourceFeature){renderFeatureDetail(sourceFeature);return;}
    const e = entities.get(state.entity);
    if (!e) {
      const members=membersForGroup(state.group);
      if(members.length>1){
        $('#entity-detail').innerHTML='<section data-group-detail="true"><span class="record-id">共同阅读组</span><h2>选择组内对象</h2><p class="placement-note">这些记录共用文献图中的阅读位置。组内对象的次序、间距或独立地址没有因此得到确认。</p><div class="related-members">'+members.map(id=>'<button type="button" data-group-member="'+esc(id)+'">'+esc(nameFor(id))+'</button>').join('')+'<p class="muted">选择成员，分别查看原文、时层和位置依据。</p></section>';
        $('#entity-select').disabled=false;$('#entity-select').value='';$('#focus-selection').disabled=true;
        $('#entity-detail').querySelectorAll('[data-group-member]').forEach(b=>b.addEventListener('click',()=>selectEntity(b.dataset.groupMember,false,state.group).catch(fail)));
        updateSelection();return;
      }
      $('#entity-detail').innerHTML = '<div class="empty-state"><h2>没有匹配的地点</h2><p class="muted">试试简短的名称，或清除区域、类型筛选。</p></div>';
      $('#entity-select').disabled = true; $('#focus-selection').disabled = true; return;
    }
    $('#entity-select').disabled = false; $('#entity-select').value = e.id;
    const placement = geographicLabels[e.geographic_status] || '位置依据待说明';
    let html = '<span class="record-id">' + esc([e.map_id,e.id].filter(Boolean).join(' · ')) + '</span><h2>' + esc(e.name) + '</h2>';
    html += '<span class="pill">' + esc(e.kind_label || kindLabels[e.kind] || e.kind || '文献对象') + '</span>';
    html += '<span class="pill" data-geographic-status="' + esc(e.geographic_status || 'unlocated') + '">' + esc(placement) + '</span>';
    if (e.temporal_label) html += '<p class="status-text">' + esc(e.temporal_label) + '</p>';
    if (e.component_summary) html += '<h3>地点与构成</h3>' + paragraphs(e.component_summary);
    if(e.detail_figure?.url&&safeUrl(e.detail_figure.url))html+='<figure class="detail-figure"><a href="'+esc(safeUrl(e.detail_figure.url))+'" target="_blank" rel="noopener"><img src="'+esc(safeUrl(e.detail_figure.url))+'" alt="'+esc(e.detail_figure.caption||e.name+'的关系说明')+'"></a>'+(e.detail_figure.caption?'<figcaption>'+esc(e.detail_figure.caption)+'</figcaption>':'')+'</figure>';
    html += '<h3>' + (state.view === 'plan' ? '文献平面中的位置' : '这处位置的依据') + '</h3>';
    html += '<div class="placement-note">' + paragraphs(state.view === 'plan' ? (e.plan_note || e.placement_note) : e.placement_note) + '</div>';
    if (state.view === 'plan' && !(e.plan_note || e.placement_note)) html += '<p class="muted">本图表达文献关系；绘图间距和图符轮廓不表示实测尺度。</p>';
    if (state.view !== 'plan' && e.geographic_status === 'unlocated') html += '<p class="muted">该对象目前保留在文献记录中；本视图没有为它指定地理落点。</p>';
    if (state.view !== 'plan' && e.geographic_status === 'source_mapped_extent') html += '<p class="muted">此位置或范围来自所引来源图；其年代与图示含义须结合来源说明，不自动等同于北魏院界。</p>';
    if (e.position_source_period) html += '<p class="muted">定位材料时层：' + esc(e.position_source_period) + '</p>';
    const members = selectedMembers();
    if (members.length) html += '<h3>共同阅读组</h3><p class="muted">这些记录共用原图的阅读位置；成员没有因此获得独立地址。</p><div class="related-members">' + members.map(id => '<button type="button" data-entity-open="' + esc(id) + '">' + esc(nameFor(id)) + '</button>').join('') + '</div>';
    if (e.limitations) html += '<h3>仍需保留的问题</h3>' + paragraphs(e.limitations);
    const evidence = e.evidence_refs || [];
    html += '<h3>原文与位置记录</h3>' + (evidence.length ? evidence.map(evidenceHTML).join('') : '<p class="muted">此页尚未汇入该对象的详细证据；可继续阅读原文献图中的档案。</p>');
    html += '<div class="detail-links">' + link('./#map?entity=' + encodeURIComponent(e.id),'打开既有文献档案 ↗') + (e.source_url ? link(e.source_url,'阅读基线文本出处 ↗',true) : '') + '</div>';
    $('#entity-detail').innerHTML = html;
    $('#entity-detail').querySelectorAll('[data-entity-open]').forEach(b => b.addEventListener('click',() => selectEntity(b.dataset.entityOpen,true,state.group).catch(fail)));
    updateSelection();
  }
  function idsForFeature(node) {
    const direct = (node.getAttribute('data-entity-id') || node.getAttribute('data-entity-ids') || node.getAttribute('data-ids') || '').split(/[ ,]+/).filter(id => entities.has(id));
    try{const members=JSON.parse(node.getAttribute('data-members')||'[]');if(Array.isArray(members))direct.push(...members.map(x=>typeof x==='string'?x:x.id).filter(id=>entities.has(id)));}catch{ /* A display-only label does not create entity membership. */ }
    const target = node.getAttribute('data-target-id') || node.id;
    return [...new Set([...direct,...(targetEntities.get(target) || [])])];
  }
  function featureFor(node) {
    let current = node instanceof Element ? node : null;
    while (current && current !== svg) {
      if (idsForFeature(current).length || sourceFeatureFor(current)) return current;
      current = current.parentElement;
    }
    return null;
  }
  function bindFeatures() {
    features = [...svg.querySelectorAll('[data-entity-id],[data-entity-ids],[data-members],[data-ids],[data-target-id],[data-feature-id],[id]')].filter(n => idsForFeature(n).length || sourceFeatureFor(n));
    features.forEach(n => {
      n.setAttribute('tabindex','0'); n.setAttribute('role','button');
      const ids=idsForFeature(n);
      n.setAttribute('aria-label', ids.length ? ids.map(nameFor).join('、') : featureTitle(sourceFeatureFor(n)));
    });
  }
  function updateSelection() {
    features.forEach(n => {
      const ids=idsForFeature(n),members=membersForGroup(state.group);
      const selected = state.feature?n.getAttribute('data-feature-id')===state.feature:state.entity?ids.includes(state.entity):members.length>1&&ids.length===members.length&&ids.every(id=>members.includes(id));
      n.classList.toggle('prosperity-selected',selected);
      n.setAttribute('aria-pressed',String(selected));
    });
    $('#focus-selection').disabled = !selectionBox();
  }
  function updateModernReference() {
    const available = state.view !== 'plan' && svg.querySelector('[data-layer="modern_reference"]');
    $('#modern-reference-control').hidden = !available;
    $('#modern-reference').checked = state.modern;
    svg.querySelectorAll('[data-layer="modern_reference"]').forEach(layer => {
      layer.style.display = state.modern ? '' : 'none';
      layer.setAttribute('aria-hidden',String(!state.modern));
    });
  }
  function selectionBox() {
    const e = entities.get(state.entity);
    if ((!e && !sourceFeatures.has(state.feature)) || !svg) return null;
    const explicit = e?.map_bboxes?.[state.view] || (state.view === 'plan' ? e?.plan_bbox : null);
    if (validBox(explicit)) return explicit;
    const selected = features.filter(n => (state.feature ? n.getAttribute('data-feature-id')===state.feature : idsForFeature(n).includes(e.id)) && (state.modern || !n.closest('[data-layer="modern_reference"]')));
    const corners = [];
    for (const n of selected) {
      try {
        const b = n.getBBox(), matrix = svg.getScreenCTM().inverse().multiply(n.getScreenCTM());
        if (b.width <= 0 && b.height <= 0) continue;
        for (const [x,y] of [[b.x,b.y],[b.x+b.width,b.y],[b.x,b.y+b.height],[b.x+b.width,b.y+b.height]]) corners.push(new DOMPoint(x,y).matrixTransform(matrix));
      } catch { /* An unavailable rendered extent is not a geographic position. */ }
    }
    if (!corners.length) return null;
    const xs=corners.map(p=>p.x),ys=corners.map(p=>p.y),minX=Math.min(...xs),minY=Math.min(...ys);
    return [minX,minY,Math.max(1,Math.max(...xs)-minX),Math.max(1,Math.max(...ys)-minY)];
  }
  function setBox(next) {
    if (!svg || !validBox(next)) return;
    box = [...next]; viewBoxes.set(state.view,[...box]); svg.setAttribute('viewBox',box.join(' '));
  }
  function fitExtent(extent) {
    if (!validBox(extent) || !baseBox) return;
    const w=Math.max(extent[2]*1.45,baseBox[2]*.07),h=Math.max(extent[3]*1.45,baseBox[3]*.07);
    setBox([extent[0]+extent[2]/2-w/2,extent[1]+extent[3]/2-h/2,w,h]);
  }
  function focusSelection() { const extent=selectionBox(); if(extent)fitExtent(extent); }
  function focusRegion() {
    const region=regionFor(state.region);
    const extent=region?.map_bboxes?.[state.view] || (state.view==='plan'?region?.bbox:null);
    if (validBox(extent)) setBox(extent);
    else if (state.region==='all') setBox(baseBox);
  }
  function zoom(factor) {
    if(!box||!baseBox)return;
    const width=Math.max(baseBox[2]*.04,Math.min(baseBox[2]*5,box[2]*factor));
    const scale=width/box[2],height=box[3]*scale;
    setBox([box[0]+(box[2]-width)/2,box[1]+(box[3]-height)/2,width,height]);
  }
  async function selectEntity(id,focus=false,group='') {
    if(!entities.has(id))return;
    await change({entity:id,region:'all',kind:'all',q:'',group,feature:''},{focus});
  }
  async function activateFeature(node) {
    const ids=idsForFeature(node);
    if(ids.length>1){
      const target=node.getAttribute('data-target-id')||node.id;
      const key=membersForGroup(target).length>1?target:ids.join(',');
      await change({group:key,entity:'',region:'all',kind:'all',q:'',feature:''});
    }else if(ids.length===1)await selectEntity(ids[0]);
    else if(sourceFeatureFor(node))await change({feature:sourceFeatureFor(node).id,entity:'',group:'',region:'all',kind:'all',q:''});
  }

  async function mapFor(view) {
    if(mapCache.has(view))return mapCache.get(view);
    const descriptor=data.maps[view],href=safeUrl(descriptor.url);
    if(!href)throw Error('图件地址无效');
    const response=await fetch(href);if(!response.ok)throw Error('图件读取失败（HTTP '+response.status+'）');
    const xml=new DOMParser().parseFromString(await response.text(),'image/svg+xml');
    if(xml.querySelector('parsererror')||xml.documentElement.localName!=='svg')throw Error('图件格式无法识别');
    const node=xml.documentElement;
    node.querySelectorAll('script,foreignObject').forEach(n=>n.remove());
    [node,...node.querySelectorAll('*')].forEach(n=>{
      [...n.attributes].filter(a=>/^on/i.test(a.name)).forEach(a=>n.removeAttribute(a.name));
      if(n.localName==='image')for(const attr of ['href','xlink:href']){const value=n.getAttribute(attr);if(value&&!value.startsWith('#')&&!value.startsWith('data:image/'))n.setAttribute(attr,new URL(value,href).href);}
    });
    node.removeAttribute('width');node.removeAttribute('height');
    node.setAttribute('aria-label',descriptor.title||viewNames[view]);
    const vb=descriptor.viewBox || (node.getAttribute('viewBox')||'').split(/[ ,]+/).map(Number);
    if(!validBox(vb))throw Error('图件缺少有效画幅');
    mapCache.set(view,{node,viewBox:vb});return mapCache.get(view);
  }
  async function renderMap() {
    const request=++serial,view=state.view,descriptor=data.maps[view];
    $('#map-viewport').setAttribute('aria-busy','true');
    if(renderedView!==view){
      const loaded=await mapFor(view);if(request!==serial)return false;
      svg=document.importNode(loaded.node,true);baseBox=[...loaded.viewBox];
      $('#map-viewport').replaceChildren(svg);renderedView=view;
      setBox(viewBoxes.get(view)||baseBox);bindFeatures();
    }
    $('#map-viewport').dataset.currentView=view;
    $('#map-viewport').dataset.map=descriptor.url;
    $('#map-viewport').setAttribute('aria-busy','false');
    $('#download-map').href=safeUrl(descriptor.url);updateModernReference();updateSelection();return true;
  }
  async function render() {
    document.documentElement.dataset.prosperityReady='loading';
    const descriptor=data.maps[state.view];
    all('[data-view]').forEach(b=>{b.hidden=!availableViews().includes(b.dataset.view);b.setAttribute('aria-pressed',String(b.dataset.view===state.view));});
    $('#entity-search').value=state.q;$('#region-filter').value=state.region;$('#kind-filter').value=state.kind;
    $('#entity-select').innerHTML=rows.length?(state.group?'<option value="">选择组内对象</option>':state.feature?'<option value="">返回文献地点名录</option>':'')+rows.map(e=>'<option value="'+esc(e.id)+'">'+esc(e.name)+'</option>').join(''):'<option value="">没有匹配的地点</option>';
    $('#result-count').textContent=state.group?'共同阅读组 · '+rows.length+' 项记录':rows.length+' / '+data.entities.length+' 项地点记录';
    $('#basis-label').textContent=descriptor.basis_label||'';
    $('#view-title').textContent=descriptor.title||viewNames[state.view];
    $('#basis-note').textContent=[...strings(descriptor.source_period),...strings(descriptor.note)].join(' · ');
    $('#map-caption').textContent=descriptor.caption||(state.view==='plan'?'图面表达文献关系；图符、间距和范围须结合具体依据阅读。':'位置图形的依据与时层见右侧档案；未定位对象继续保留在文献记录中。');
    $('#map-status').textContent=state.view==='plan'?'文献相对平面 · 可拖动与点选':descriptor.basis_label||viewNames[state.view];
    $('#map-limitations-body').innerHTML=paragraphs(descriptor.limitations||descriptor.note);
    $('#map-limitations').hidden=!strings(descriptor.limitations||descriptor.note).length;
    renderDetail();
    if(await renderMap())document.documentElement.dataset.prosperityReady='true';
  }
  function renderSources() {
    $('#source-list').innerHTML=(data.sources||[]).map(s=>'<article class="source-card"><span class="record-id">'+esc(s.id||'资料')+'</span><h3>'+esc(s.title||s.id)+'</h3>'+paragraphs(s.period||s.source_period)+paragraphs(s.role)+paragraphs(s.note)+paragraphs(s.limitations)+(s.url?link(s.url,'打开来源 ↗',true):'')+'</article>').join('');
    $('#download-links').innerHTML=(data.downloads||[]).map(d=>link(d.url,d.label||d.title||d.type||'下载图件')).join('');
    const counts=data.text_review_summary,decisions=data.map_decisions||[];
    $('#text-review').hidden=!counts&&!decisions.length;
    if(counts){
      const labels=[['evidence_records','条记录纳入核对'],['legacy_quote_sequence_match_records','条原引序列匹配'],['manual_exception_records','条人工处理']];
      $('#text-review-summary').innerHTML='<p class="review-counts">'+labels.filter(([key])=>Number.isFinite(counts[key])).map(([key,label])=>'<span><strong>'+counts[key]+'</strong> '+label+'</span>').join('')+'</p><p class="muted">本版核对电子转录中的原文、节录与校注，分别说明采用判断。全版本的书影逐叶校勘仍待继续，版本异读保留记录。</p>';
    }
    const reviewText=value=>String(value||'').replaceAll('small.inline-note','现代夹注层');
    $('#text-decisions').innerHTML=decisions.map(d=>'<article class="text-decision" data-text-decision="'+esc(d.id)+'"><span class="record-id">'+esc(d.id)+'</span><h3>'+esc(d.title||d.id)+'</h3>'+paragraphs(reviewText(d.finding))+(d.corrected_quote?'<blockquote>'+esc(d.corrected_quote)+'</blockquote>':'')+(d.visual_instruction?'<h4>在图中怎样采用</h4>'+paragraphs(reviewText(d.visual_instruction)):'')+(d.locator?'<p class="muted">'+esc(d.locator)+'</p>':'')+(d.evidence_keys?.length?'<p class="muted">相关记录：'+esc(d.evidence_keys.join('、'))+'</p>':'')+'</article>').join('');
  }
  function showSources() { $('#source-catalog').open=true;$('#sources').scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'}); }
  function fail(error) {
    document.documentElement.dataset.prosperityReady='error';
    $('#map-viewport').setAttribute('aria-busy','false');
    $('#map-viewport').innerHTML='<p class="error-message">暂时无法载入：'+esc(error.message)+'。请刷新后重试。</p>';
    console.error(error);
  }
  async function init() {
    const filterMedia=matchMedia('(max-width: 800px)');
    $('#filter-panel').open=!filterMedia.matches;
    filterMedia.addEventListener('change',event=>{$('#filter-panel').open=!event.matches;});
    const response=await fetch('./prosperity/data.json');if(!response.ok)throw Error('城市数据读取失败（HTTP '+response.status+'）');
    data=await response.json();
    if(!Array.isArray(data.entities)||!data.entities.length||!data.maps?.plan?.url)throw Error('城市数据缺少必要内容');
    entities=new Map(data.entities.map(e=>[e.id,e]));
    sourceFeatures=new Map((data.source_features||[]).map(f=>[f.id,f]));
    for(const e of data.entities)for(const id of e.plan_target_ids||[])targetEntities.set(id,[...(targetEntities.get(id)||[]),e.id]);
    if(data.intro)$('#intro-copy').textContent=data.intro;
    $('#region-filter').innerHTML='<option value="all">全城</option>'+(data.regions||[]).map(r=>'<option value="'+esc(r.id)+'">'+esc(r.name)+'</option>').join('');
    const kinds=[...new Set(data.entities.map(e=>e.kind).filter(Boolean))];
    $('#kind-filter').innerHTML='<option value="all">全部类型</option>'+kinds.map(k=>'<option value="'+esc(k)+'">'+esc(kindLabels[k]||data.entities.find(e=>e.kind===k)?.kind_label||k)+'</option>').join('');
    all('[data-view]').forEach(b=>b.addEventListener('click',()=>change({view:b.dataset.view}).catch(fail)));
    $('#entity-search').addEventListener('input',()=>change({q:$('#entity-search').value,group:'',feature:''},{replace:true}).catch(fail));
    $('#region-filter').addEventListener('change',()=>change({region:$('#region-filter').value,group:'',feature:''}).catch(fail));
    $('#kind-filter').addEventListener('change',()=>change({kind:$('#kind-filter').value,group:'',feature:''}).catch(fail));
    $('#entity-select').addEventListener('change',()=>change({entity:$('#entity-select').value,feature:''},{focus:true}).catch(fail));
    $('#clear-filters').addEventListener('click',()=>change({region:'all',kind:'all',q:'',group:'',feature:''}).catch(fail));
    $('#zoom-in').addEventListener('click',()=>zoom(.8));$('#zoom-out').addEventListener('click',()=>zoom(1.25));
    $('#reset-map').addEventListener('click',()=>setBox(baseBox));$('#focus-selection').addEventListener('click',focusSelection);
    $('#modern-reference').addEventListener('change',()=>change({modern:$('#modern-reference').checked}).catch(fail));
    $('#sources-link').addEventListener('click',e=>{e.preventDefault();showSources();});
    window.addEventListener('hashchange',()=>{if(location.hash==='#sources'){showSources();return;}readHash();normalizeSelection();render().catch(fail);});
    const viewport=$('#map-viewport');let drag=null;
    viewport.addEventListener('pointerdown',event=>{if(event.button!==0||!box)return;drag={id:event.pointerId,x:event.clientX,y:event.clientY,box:[...box],target:event.target,moved:false};});
    viewport.addEventListener('pointermove',event=>{
      if(!drag||event.pointerId!==drag.id||!svg)return;
      const dx=event.clientX-drag.x,dy=event.clientY-drag.y;
      if(Math.hypot(dx,dy)>6){drag.moved=true;viewport.setPointerCapture(event.pointerId);viewport.classList.add('dragging');}
      if(drag.moved){const rect=viewport.getBoundingClientRect();setBox([drag.box[0]-dx*drag.box[2]/rect.width,drag.box[1]-dy*drag.box[3]/rect.height,drag.box[2],drag.box[3]]);}
    });
    viewport.addEventListener('pointerup',event=>{
      if(!drag||event.pointerId!==drag.id)return;
      const completed=drag;drag=null;viewport.classList.remove('dragging');
      if(viewport.hasPointerCapture(event.pointerId))viewport.releasePointerCapture(event.pointerId);
      if(!completed.moved){const target=featureFor(completed.target);if(target)activateFeature(target).catch(fail);}
    });
    viewport.addEventListener('pointercancel',()=>{drag=null;viewport.classList.remove('dragging');});
    viewport.addEventListener('wheel',event=>{event.preventDefault();zoom(event.deltaY>0?1.12:.89);},{passive:false});
    viewport.addEventListener('keydown',event=>{
      if(['Enter',' '].includes(event.key)){const target=featureFor(event.target);if(target){event.preventDefault();activateFeature(target).catch(fail);}}
      else if(event.key==='+'||event.key==='='){event.preventDefault();zoom(.8);}
      else if(event.key==='-'){event.preventDefault();zoom(1.25);}
      else if(event.key==='Home'){event.preventDefault();setBox(baseBox);}
    });
    readHash();normalizeSelection();renderSources();await render();
    if(location.hash==='#sources')showSources();
    try{
      const latestResponse=await fetch('./release.json',{cache:'no-store'});if(!latestResponse.ok)throw Error('release');
      const latest=await latestResponse.json();
      $('#release-status').textContent=latest.source_commit===data.source_commit?'本页与正式发布一致 · '+data.source_commit.slice(0,7):'本页版本 '+(data.version||'盛时洛阳')+'；最新发布请返回首页。';
    }catch{$('#release-status').textContent='本页版本 '+(data.version||'盛时洛阳')+'；在线版本暂未核对。';}
  }
  init().catch(fail);
})();
