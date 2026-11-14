/* B8 audits associations without converting documentary anchors to coordinates. */
(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const all = s => [...document.querySelectorAll(s)];
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const labels = {individual:'单实体交互',group_member:'共享／组内交互',no_interactive_target:'无交互目标'};
  const temporal = {attested_by_528:'盛时已有记载',later_temple:'盛时为宅第／后改寺',undated:'年代未详',historical:'历史旧迹',retrospective:'后世追记'};
  const reviewLabels = {display_resolved:'显示关系已厘清',separate_layers_required:'须保持分层',evidence_pending:'史证仍待核'};
  const views = ['map','ledger','cases','sources'];
  const filters = ['all','individual','group_member','no_interactive_target','has_evidence','catalog_only','review_cases'];
  let ledger, cases, sources, metadata, current = [], zoom = 1;
  let state = {view:'map',entity:'ic_yongning',filter:'all',region:'all',q:'',case:'CB01',overlay:true};

  function link(url, label) {
    try {
      const u = new URL(url, location.href);
      if (!['http:', 'https:'].includes(u.protocol)) return esc(label);
      return '<a href="' + esc(url) + '">' + esc(label) + '</a>';
    } catch { return esc(label); }
  }
  function sourceLink(id) {
    const s = (sources.sources || []).find(x => x.id === id);
    return s ? link(s.url, s.title || s.id) : esc(id);
  }
  function recordFor(id) { return ledger.entities.find(x => x.id === id); }
  function entityName(id) { const e = recordFor(id); return e ? (e.display_name || e.name) : id; }
  function caseFor(id) { return cases.records.find(x => x.id === id); }
  function caseLinks(ids) {
    return (ids || []).map(id => '<button class="member" data-case-open="' + esc(id) + '">' + esc(id + ' ' + (caseFor(id)?.short_title || '')) + '</button>').join('');
  }
  function memberLinks(ids) {
    return (ids || []).map(id => '<button class="member" data-entity-open="' + esc(id) + '">' + esc(entityName(id)) + '</button>').join('');
  }
  function textList(value) {
    if (!value) return '';
    const values = Array.isArray(value) ? value : [value];
    return '<ul>' + values.map(x => '<li>' + esc(typeof x === 'string' ? x : (x.note || x.reading || x.finding || x.title || '')) + '</li>').join('') + '</ul>';
  }
  function syncHash() {
    const q = new URLSearchParams({view:state.view,entity:state.entity,filter:state.filter,region:state.region,q:state.q,case:state.case,overlay:state.overlay?'1':'0'});
    const hash = '#' + q.toString();
    if (location.hash !== hash) history.replaceState(null, '', hash);
  }
  function matches(e) {
    const q = state.q.trim().toLocaleLowerCase();
    if (q && ![e.id,e.map_id,e.name,e.source_name,e.display_name].some(x => String(x || '').toLocaleLowerCase().includes(q))) return false;
    if (state.region !== 'all' && !e.explicit_focus_regions.includes(state.region)) return false;
    if (['individual','group_member','no_interactive_target'].includes(state.filter) && e.marker_state !== state.filter) return false;
    if (state.filter === 'has_evidence' && !e.direct_evidence_refs.length) return false;
    if (state.filter === 'catalog_only' && e.direct_evidence_refs.length) return false;
    if (state.filter === 'review_cases' && !e.case_ids.length) return false;
    return true;
  }
  function bindLocalLinks(parent) {
    parent.querySelectorAll('[data-entity-open]').forEach(b => b.onclick = () => {
      state.entity = b.dataset.entityOpen; state.filter = 'all'; state.region = 'all'; state.q = ''; state.view = 'map'; render();
    });
    parent.querySelectorAll('[data-case-open]').forEach(b => b.onclick = () => {
      state.case = b.dataset.caseOpen; state.view = 'cases'; render();
    });
  }
  function renderDetail() {
    const e = recordFor(state.entity);
    if (!e || !current.includes(e)) {
      $('#entity-detail').innerHTML = '<p class="empty">当前筛选没有匹配实体。可清除筛选后继续查阅。</p>';
      $('#focus-selection').disabled = true;
      highlight();
      return;
    }
    const shared = e.marker_state === 'group_member';
    const memberIds = [...new Set(e.targets.flatMap(t => t.member_ids))];
    const override = e.current_review || {};
    const evidence = e.direct_evidence_refs.map(r => link(r.link, r.key + ' · ' + (r.title || '记录'))).join('<br>');
    const chronology = e.chronology_refs.map(r => link(r.link, r.id + ' · ' + (r.role || '时层记录'))).join('<br>');
    const notes = (e.case_ids || []).map(id => caseFor(id)).filter(Boolean);
    let html = '<span class="record-id">' + esc((e.map_id || '未编号') + ' · ' + e.id) + '</span><h2>' + esc(e.display_name || e.name) + '</h2>';
    html += '<span class="pill">' + esc(labels[e.marker_state]) + '</span><span class="pill">结构关联已核</span>';
    if (override.temporal_label) html += '<p class="notice current-reading">' + esc(override.temporal_label) + (override.note ? '：' + esc(override.note) : '') + '</p>';
    html += '<h3>当前图上关联</h3><p>' + (e.targets.length ? (shared ? '此实体与同组对象共用既有阅读锚点。成员不拆成独立地址。' : '现有一个单实体点击目标；这只说明界面关联，不等于独立遗址已经定位。') : '原交互层没有该实体的点击目标。道路、水体、附录和旁注可能以其他方式表达，不据此判作漏画。') + '</p>';
    if (shared) html += '<div class="group-members">' + memberLinks(memberIds) + '</div>';
    html += '<p class="subtle">原始绘图方式：' + esc((e.drawing_status.baseline_modes || []).join('、') || '未登记') + '。古代地理坐标：未定位。</p>';
    html += '<h3>分区与图幅</h3><p>显式焦点名录：' + esc(e.explicit_focus_regions.join('、') || '没有列入') + '<br>既有锚点落入图幅：' + esc(e.crop_regions.join('、') || '无可计算命中') + '</p><p class="subtle">第二项仅是绘图裁切关系，不证明历史边界或里属。</p>';
    html += '<h3>本批审校</h3>' + (notes.length ? caseLinks(e.case_ids) : '<p class="subtle">本批完成结构清点；没有为此实体新增独立史证结论。</p>');
    if (notes.length) html += '<p>' + esc(notes.map(c => c.action).filter(Boolean).join(' ')) + '</p>';
    if (e.finding_ids?.length) html += ledger.findings.filter(f => e.finding_ids.includes(f.id)).map(f => '<p class="notice">' + esc(f.title + '：' + f.detail) + '</p>').join('');
    html += '<h3>历批显式引用</h3><p class="subtle">' + e.direct_evidence_refs.length + ' 条记录关联；不是独立史料来源数量，也不是逐条结论均已重审。</p><div class="links-list">' + (evidence || '尚无本清单覆盖批次的显式引用；基线出处仍保留。') + '</div>';
    html += '<h3>时层与基线</h3><p class="legacy-field">封存时层字段：' + esc(e.legacy_temporal_state ? (temporal[e.legacy_temporal_state] || e.legacy_temporal_state) : '未填写') + '</p><p class="subtle">旧字段是可追溯记录；须与上方本批说明及事件对象范围并读。</p>';
    if (chronology) html += '<div class="links-list">' + chronology + '</div>';
    html += '<div class="divider"></div><div class="links-list">' + link('./v3.0-dual.html#map?entity=' + encodeURIComponent(e.id), '回到文献母图') + (e.source_url ? link(e.source_url, '基线文本出处') : '') + '</div>';
    $('#entity-detail').innerHTML = html;
    $('#focus-selection').disabled = !e.targets.length;
    bindLocalLinks($('#entity-detail'));
    highlight();
  }
  function highlight() {
    const e = recordFor(state.entity), ids = new Set((e?.targets || []).map(t => t.id));
    all('#map-holder .city-review-target').forEach(g => g.classList.toggle('selected', ids.has(g.dataset.targetId)));
    const overlay = $('#map-holder #city-audit-overlay-b8');
    if (overlay) overlay.style.visibility = state.overlay ? 'visible' : 'hidden';
    $('#map-location-info').textContent = !e || !current.includes(e) ? '当前没有选中实体；阅读环只表示既有交互关联。' : e.targets.length
      ? (e.marker_state === 'group_member' ? '共享阅读组：只突出既有共同锚点，不为成员拆出坐标。' : '突出的是既有单实体交互锚点，不提供经纬度或遗址精度。')
      : '该实体没有交互目标；本页保留未定位／非点状状态，不自动在图上添点。';
  }
  function renderLedger() {
    $('#ledger-body').innerHTML = current.map(e => '<tr data-entity-row="' + esc(e.id) + '"><td><button data-entity-open="' + esc(e.id) + '">' + esc(e.display_name || e.name) + '</button><br><span class="record-id">' + esc((e.map_id || '—') + ' · ' + e.id) + '</span></td><td>' + esc(labels[e.marker_state]) + '</td><td>' + esc(e.explicit_focus_regions.join('、') || '未列入') + '</td><td>' + e.direct_evidence_refs.length + '<span class="subtle"> 条关联</span></td><td>' + (e.case_ids.length ? caseLinks(e.case_ids) : '<span class="subtle">结构已核／史证未重审</span>') + '</td></tr>').join('') || '<tr><td colspan="5" class="empty">没有匹配记录。</td></tr>';
    bindLocalLinks($('#ledger-body'));
  }
  function renderCases() {
    const c = caseFor(state.case) || cases.records[0];
    state.case = c.id;
    $('#case-list').innerHTML = cases.records.map(x => '<button data-case="' + esc(x.id) + '" aria-pressed="' + (x.id === c.id) + '"><span class="record-id">' + esc(x.id) + '</span>' + esc(x.short_title || x.title) + '</button>').join('');
    $('#case-list').querySelectorAll('[data-case]').forEach(b => b.onclick = () => {state.case = b.dataset.case; renderCases(); syncHash();});
    let html = '<span class="record-id">' + esc(c.id + ' · ' + (reviewLabels[c.review_state] || c.review_state)) + '</span><h2>' + esc(c.title || c.short_title) + '</h2><div>' + memberLinks(c.entities) + '</div>';
    html += '<h3>本次判断</h3><p>' + esc(c.finding) + '</p><h3>当前显示与处理</h3><p class="notice">' + esc(c.action) + '</p><p>' + esc(c.current_display) + '</p>';
    html += '<details><summary>查看基线记录与前后差异</summary><p>' + esc(c.baseline_display_note) + '</p></details>';
    if (c.errata) {
      const er = c.errata;
      html += '<section class="quotation-correction"><h3>引文层更正 · ' + esc(er.legacy_record_id || 'G15') + '</h3><p>旧记录为压缩概述，保留为校核对象：</p><blockquote>' + esc(er.legacy_quote || '') + '</blockquote><p>本次补录的正文原句：</p><blockquote>' + esc(er.corrected_source_quote || c.corrected_source_quote || '') + '</blockquote><p class="subtle">' + esc(er.note || '夹注与正文分列；本项更正不增补水路或定位。') + '</p></section>';
    }
    html += '<h3>直接复核的来源</h3><p class="subtle">整理本卷页与现代校注分层保存；本批仍属于同一古籍来源家族，不把重复整理本计作多份独立原书。</p>';
    html += (c.source_checks || []).map(s => {
      const src = cases.sources.find(x => x.id === (s.source_id || s.source));
      const url = s.url || src?.url;
      return '<div class="source-check"><blockquote>' + esc(s.quote || s.short_quote || '') + '</blockquote><p class="subtle">' + esc(s.locator || s.location || '') + ' · ' + esc(s.textual_layer || s.layer || '') + '</p><p>' + (url ? link(url, (s.source_id || s.source || '原始文本') + ' ↗') : '') + '</p><p class="subtle">直接涉及：' + esc((s.direct_entity_ids || []).map(entityName).join('、') || '本条为校注或背景') + '；背景／对比：' + esc((s.context_entity_ids || []).map(entityName).join('、') || '无') + '</p>' + ((s.note || s.editorial_reading) ? '<p class="subtle">' + esc(s.note || s.editorial_reading) + '</p>' : '') + '</div>';
    }).join('');
    html += '<h3>对应历批记录</h3><div class="links-list">' + (c.evidence_refs || []).map(r => {
      const found = ledger.entities.flatMap(e => e.direct_evidence_refs).find(x => x.batch === r.batch && x.id === r.id);
      return link(r.link || found?.link || './v3.0-dual.html', r.batch + ':' + r.id + (r.role === 'context' ? '（背景）' : ''));
    }).join('') + '</div>';
    html += '<h3>必须保留的边界</h3>' + textList(c.required_boundary);
    html += '<h3>不能推出的结论</h3>' + textList((c.forbidden_inferences || []).map(x => '不得：' + x));
    if (c.remaining_question) html += '<h3>仍待解决</h3><p>' + esc(c.remaining_question) + '</p>';
    $('#case-detail').innerHTML = html; bindLocalLinks($('#case-detail'));
  }
  function renderSources() {
    const count = sources.review_counts;
    let html = '<h2 class="source-section-title">三幅目标地图：落实获取路径</h2><div class="source-grid">';
    html += sources.access_records.map(r => '<article class="source-card"><span class="record-id">' + esc(r.target_call_number) + '</span><h2>' + esc(r.title) + '</h2><p class="notice">' + esc(r.status_label) + '</p><p>' + esc(r.finding) + '</p><h3>下一道证据</h3><p>' + esc(r.next_gate) + '</p><p class="subtle">' + esc(r.limit) + '</p><div class="links-list">' + (r.source_ids || []).slice(0,3).map(sourceLink).join('') + '</div></article>').join('');
    html += '</div><h2 class="source-section-title">两套中国底图：从一般注记到具体系列目录</h2><div class="source-grid">';
    html += sources.upstream_records.map(r => '<article class="source-card"><span class="record-id">目录 ' + esc(r.catalog_record_number) + ' · 非历史图幅编号</span><h2>' + esc(r.catalog_title) + '</h2><p>' + esc(r.catalog_year) + ' · 1:' + r.scale_denominator + ' · ' + r.catalog_sheet_count + ' 幅</p><p>' + esc(r.creator_as_cataloged) + '</p><p class="notice">' + esc(r.new_finding) + '</p><p>' + esc(r.notes_as_cataloged || '') + '</p><p>' + esc(r.target_relation) + '</p><p class="subtle">' + esc(r.next_gate) + '</p>' + sourceLink(r.source_id) + '</article>').join('');
    html += '<article class="source-card"><span class="record-id">原件与匹配分开计数</span><h2>' + count.documented_join_index_targets + ' 张接合表线索</h2><p>本批取得目标历史扫描：' + count.target_historical_scans_obtained + '<br>取得接合表影像：' + count.join_index_images_obtained + '<br>确证 AMS 实际用图：' + count.actual_ams_source_matches + '<br>获准地面控制点：' + count.approved_ground_control_points + '</p><p class="subtle">目录编号、历史图号、印次和数字化编号须分别登记。年份与尺度相容，仍不足以认定具体来源。</p></article></div>';
    html += '<h2 class="source-section-title">排除同名、重号与存续假设</h2><div class="source-grid">';
    html += sources.rejected_matches.map(r => '<article class="source-card"><span class="record-id">' + esc(r.candidate_catalog_id || r.id) + '</span><h2>' + esc(r.candidate_name || r.title || r.id) + '</h2><p>' + esc(r.reason) + '</p><p class="subtle">排除这条记录作为目标同版图；不推断其他馆藏不存在。</p>' + sourceLink(r.source_id) + '</article>').join('');
    html += sources.structure_reviews.map(r => '<article class="source-card source-wide"><h2>' + esc(r.title) + '</h2><p>' + esc(r.reported_event_date + '：' + r.reported_event) + '</p><p class="notice">' + esc(r.verdict) + '</p><p class="subtle">依据养护部门的回顾性叙述；不是原始工程测量图。' + esc(r.next_gate) + '</p>' + sourceLink(r.source_id) + '</article>').join('');
    html += '</div><details><summary>查看本批两张完整审核板</summary><img class="source-plate" src="./source-access/access-summary.svg" alt="三幅目标地图的公开获取状态与误匹配排除"><img class="source-plate" src="./source-access/upstream-summary.svg" alt="两套中国底图系列目录、接合表线索与桥墩存续限制"></details>';
    $('#source-content').innerHTML = html;
  }
  function scale(value) {
    zoom = Math.max(1, Math.min(5, value));
    $('#map-holder').style.width = (zoom * 100) + '%';
    if (zoom === 1) $('#map-viewport-b8').scrollTo(0,0);
  }
  function render() {
    $('#entity-search').value = state.q; $('#entity-filter').value = state.filter; $('#region-filter').value = state.region; $('#show-review').checked = state.overlay;
    current = ledger.entities.filter(matches);
    if (!current.some(e => e.id === state.entity)) state.entity = current[0]?.id || '';
    $('#entity-select').innerHTML = current.map(e => '<option value="' + esc(e.id) + '">' + esc((e.map_id || '') + ' ' + (e.display_name || e.name)) + '</option>').join('');
    $('#entity-select').value = state.entity; $('#entity-select').disabled = !current.length;
    $('#result-count').textContent = '匹配 ' + current.length + ' / ' + ledger.counts.entities + ' 项；结构关联已核，历史确证不据此计数。';
    for (const v of views) $('#' + v + '-view').hidden = state.view !== v;
    $('#entity-controls').hidden = !['map','ledger'].includes(state.view);
    all('[data-view]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.view === state.view)));
    renderDetail(); renderLedger(); if (state.view === 'cases') renderCases(); syncHash();
  }
  function restore() {
    const q = new URLSearchParams(location.hash.slice(1));
    state = {
      view: views.includes(q.get('view')) ? q.get('view') : 'map',
      entity:q.get('entity') || 'ic_yongning',
      filter:filters.includes(q.get('filter')) ? q.get('filter') : 'all',
      region:ledger.regions.some(r => r.code === q.get('region')) ? q.get('region') : 'all',
      q:q.get('q') || '',case:caseFor(q.get('case'))?.id || cases.records[0].id,overlay:q.get('overlay') !== '0'
    };
    render();
  }
  async function read(path, asText=false) {
    const r = await fetch('./' + path); if (!r.ok) throw Error(path + ' HTTP ' + r.status);
    return asText ? r.text() : r.json();
  }
  async function main() {
    const result = await Promise.all([read('city-review/ledger.json'),read('city-review/cases.json'),read('source-access/metadata.json'),read('city-review/metadata.json'),read('build-info.json'),read('assets/master-dual-b8-review.svg',true)]);
    [ledger,cases,sources,metadata] = result;
    const info = result[4];
    if (![ledger,cases,sources,metadata].every(x => x.source_commit === info.source_commit)) throw Error('研究记录与构建版本不一致');
    if (info.city_review_b8?.entities !== 339 || ledger.entities.length !== 339) throw Error('实体清单数量不一致');
    $('#map-holder').innerHTML = result[5].replace(/<\?xml[^>]*\?>/,'');
    $('#metric-entities').textContent = ledger.counts.entities; $('#metric-targets').textContent = ledger.counts.targets;
    $('#metric-cases').textContent = cases.records.length; $('#metric-unmapped').textContent = ledger.counts.no_interactive_target_entities;
    $('#region-filter').innerHTML = '<option value="all">全部分区</option>' + ledger.regions.map(r => '<option value="' + esc(r.code) + '">' + esc(r.code + ' ' + r.title) + '</option>').join('');
    renderSources(); restore();
    all('[data-view]').forEach(b => b.onclick = () => {state.view = b.dataset.view; render();});
    $('#entity-search').oninput = () => {state.q = $('#entity-search').value; render();};
    $('#entity-filter').onchange = () => {state.filter = $('#entity-filter').value; render();};
    $('#region-filter').onchange = () => {state.region = $('#region-filter').value; render();};
    $('#clear-filters').onclick = () => {state.q = ''; state.filter = 'all'; state.region = 'all'; render();};
    $('#entity-select').onchange = () => {state.entity = $('#entity-select').value; renderDetail(); syncHash();};
    $('#show-review').onchange = () => {state.overlay = $('#show-review').checked; highlight(); syncHash();};
    $('#zoom-in').onclick = () => scale(zoom * 1.4); $('#zoom-out').onclick = () => scale(zoom / 1.4); $('#zoom-reset').onclick = () => scale(1);
    $('#focus-selection').onclick = () => {
      const e = recordFor(state.entity); if (!e?.targets.length) return;
      scale(3.2);
      requestAnimationFrame(() => $('#map-holder [data-target-id="' + e.targets[0].id + '"]')?.scrollIntoView({block:'center',inline:'center'}));
    };
    all('#map-holder .city-review-target').forEach(g => {
      g.setAttribute('tabindex','0'); g.setAttribute('role','button');
      const choose = () => {state.entity = g.dataset.entityIds.split(' ')[0];state.q='';state.filter='all';state.region='all';render();};
      g.onclick = choose; g.onkeydown = e => {if (['Enter',' '].includes(e.key)) {e.preventDefault();choose();}};
    });
    window.addEventListener('hashchange', restore);
    $('#release-status').textContent = 'B8 记录与本页构建一致 · ' + info.source_commit.slice(0,7) + ' · 339 项结构清点，' + cases.records.length + ' 个重点审校案例。';
    document.documentElement.dataset.cityReviewReady = 'true';
  }
  main().catch(e => {
    $('#entity-detail').innerHTML = '<p class="error">审校资料载入失败：' + esc(e.message) + '</p>';
    $('#release-status').textContent = '研究记录未能完成版本核对。';
    document.documentElement.dataset.cityReviewReady = 'error';
    console.error(e);
  });
})();
