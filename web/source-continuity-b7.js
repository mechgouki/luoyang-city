'use strict';
(() => {
  const $ = selector => document.querySelector(selector);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const filters = ['all', 'period-match', 'earlier'];
  const views = ['timeline', 'lineage'];
  let data;
  let state = {record: 'zhengzhou-1942', filter: 'all', view: 'timeline', open: false};
  const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(text)} ↗</a>`;
  const list = values => `<ul>${values.map(value => `<li>${esc(value)}</li>`).join('')}</ul>`;

  function saveState() {
    const params = new URLSearchParams({...state, open: state.open ? '1' : '0'});
    if (location.hash !== '#' + params.toString()) history.replaceState(null, '', '#' + params.toString());
  }

  function selectedRecord() {
    return data.records.find(record => record.id === state.record) || data.records[0];
  }

  function timeline(record) {
    const descriptions = {
      upstream_map_date: record.upstream_map_scale_denominator ? `1:${record.upstream_map_scale_denominator}` : '未给出底图年月',
      photography_date: '航片拍摄日期', survey_date: '目录所记测量日期', plate_date: '不自动等于新测',
      publication_date_as_cataloged: record.publication_year_bracketed ? '保留馆方方括号' : '目录出版字段',
    };
    return `<section id="continuity-timeline"><h3>五种日期分别看</h3><div class="date-grid">${data.date_semantics.map(item => `<div class="date-cell"><span>${esc(item.label)}</span><strong>${esc(record[item.field] || '目录未记')}</strong><span>${esc(descriptions[item.field])}</span></div>`).join('')}</div><p class="small">目录未记只表示本次所读字段没有给出，不表示该步骤没有发生。摄影、测量、制版与出版日期不能互相替代。</p><p>${esc(record.production_description)}</p>${record.upstream_map_creator ? `<p><strong>目录所记底图机构：</strong>${esc(record.upstream_map_creator)}</p>` : ''}</section>`;
  }

  function lineage(record) {
    const stages = [];
    if (record.upstream_map_date) stages.push([`${record.upstream_map_date} · 中国底图`, `${record.upstream_map_creator}；1:${record.upstream_map_scale_denominator}`]);
    if (record.photography_date) stages.push([`${record.photography_date} · 摄影`, '依据目录一般注记，尚未核实际航片或原图边栏']);
    if (record.survey_date) stages.push([`${record.survey_date} · 测量`, '目录记为要图／航空摄影测量；实际范围与方法仍须原件']);
    if (record.plate_date) stages.push([`${record.plate_date} · 制版`, '制版过程，不自动解释为这一年新增实测']);
    stages.push([`${record.publication_date_as_cataloged} · 出版`, record.publication_year_bracketed ? '原目录方括号保留，不改为精确印刷日期' : '这条单件目录的出版日期']);
    return `<section id="continuity-lineage"><h3>目录明载的制作关系</h3><ol class="lineage-list">${stages.map(([title, detail]) => `<li><strong>${esc(title)}</strong>${esc(detail)}</li>`).join('')}</ol><div class="meaning"><strong>与AMS实际用图关系：仍未证</strong>上述链条只表达本条目录所记制作过程，未连接为L500或L531实际采用的源图。</div></section>`;
  }

  function renderSource(record) {
    const source = data.sources.find(item => item.id === record.source_id);
    $('#continuity-source-link').href = source.url;
    $('#continuity-source-toggle').setAttribute('aria-expanded', String(state.open));
    $('#continuity-source-toggle').textContent = state.open ? '收起来源详情' : '展开来源详情';
    $('#continuity-source-detail').hidden = !state.open;
    $('#continuity-source-detail').innerHTML = `<h3>${esc(source.title)}</h3><dl class="label-value"><dt>完整题名</dt><dd>${esc(record.catalog_title)}</dd><dt>系列／图号</dt><dd>${esc(record.series)}</dd><dt>制作／出版</dt><dd>${esc(record.creator)} / ${esc(record.publisher)}</dd><dt>纸本著录</dt><dd>${esc(record.catalog_physical_form)}；1:${record.scale_denominator}</dd><dt>出版地／日期</dt><dd>${esc(record.publication_place_as_cataloged)} / ${esc(record.publication_date_as_cataloged)}</dd><dt>馆号／书目ID</dt><dd>${esc(record.call_number)} / ${esc(record.bibliographic_id)}</dd><dt>证据位置</dt><dd>${esc(source.evidence_location)}</dd><dt>获取日期</dt><dd>${esc(source.retrieved_date)}</dd></dl><h3>目录一般注记</h3><blockquote lang="ja">${esc(record.catalog_general_note)}</blockquote><p class="small">这是官方目录注记，本批没有取得这三幅地图影像，也没有把目录文字标为亲见原图边栏。</p><p>${link(source.url, '官方单件目录')} · ${link(source.api_url, 'NDL API查询入口')}</p><p class="small">本次目录HTML响应SHA-256<br><code>${esc(source.response_sha256)}</code></p><p class="small">哈希识别本次取得的响应字节；动态网页可能变更，不能据此宣称永久内容不变。${esc(source.rights_note)}</p>`;
  }

  function render() {
    const records = data.records.filter(record => state.filter === 'all' || record.status === state.filter);
    const record = records.find(item => item.id === state.record) || records[0];
    state.record = record.id;
    $('#continuity-filter').value = state.filter;
    $('#continuity-view').value = state.view;
    $('#continuity-record').innerHTML = records.map(item => `<option value="${esc(item.id)}">${esc(item.title)}</option>`).join('');
    $('#continuity-record').value = record.id;
    $('#continuity-count').textContent = `目录已核3条；当前${records.length}条；新增历史扫描0幅；已确认实际用图关系0条；获准地面控制点0。`;
    $('#continuity-reading').innerHTML = `<h2>${esc(record.title)}</h2><span class="status">${esc(record.status_label)}</span>${state.view === 'timeline' ? timeline(record) : lineage(record)}<div class="two-column"><section><h3>地域核对</h3><p>${esc(record.region_review)}</p><h3>版次核对</h3><p>${esc(record.edition_review)}</p></section><section><h3>尚未证明的部分</h3>${list(record.unknowns)}</section></div><div class="meaning"><strong>当前结论</strong>${esc(record.conclusion)}</div><h3>下一步门槛</h3><p>${esc(record.next_gate)}</p>`;
    renderSource(record);
    saveState();
  }

  function restoreState() {
    const params = new URLSearchParams(location.hash.slice(1));
    state = {record: data.records.some(record => record.id === params.get('record')) ? params.get('record') : 'zhengzhou-1942',
      filter: filters.includes(params.get('filter')) ? params.get('filter') : 'all',
      view: views.includes(params.get('view')) ? params.get('view') : 'timeline',
      open: params.get('open') === '1'};
    render();
  }

  ['record', 'filter', 'view'].forEach(key => {
    $('#continuity-' + key).addEventListener('change', event => {
      if (!data) return;
      state[key] = event.target.value;
      render();
    });
  });
  $('#continuity-source-toggle').addEventListener('click', () => {
    if (!data) return;
    state.open = !state.open;
    renderSource(selectedRecord());
    saveState();
  });
  window.addEventListener('hashchange', () => { if (data) restoreState(); });
  fetch('./source-continuity/metadata.json').then(response => {
    if (!response.ok) throw Error('HTTP ' + response.status);
    return response.json();
  }).then(result => {
    data = result;
    $('#continuity-gates').innerHTML = data.next_gates.map(gate => `<article class="gate"><h3>${esc(gate.title)}</h3><p>${esc(gate.requires)}</p></article>`).join('');
    $('#continuity-limits').innerHTML = data.limitations.map(item => `<li>${esc(item)}</li>`).join('');
    $('#continuity-build').innerHTML = `发布提交：<code>${esc(data.source_commit)}</code><br>研究基线：<code>${esc(data.baseline_commit)}</code>`;
    restoreState();
    document.documentElement.dataset.sourceContinuityReady = 'true';
  }).catch(error => {
    $('#continuity-error').hidden = false;
    $('#continuity-error').textContent = '来源连续性数据加载失败：' + error.message;
    document.documentElement.dataset.sourceContinuityReady = 'error';
  });
})();
