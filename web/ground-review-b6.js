'use strict';
(() => {
  const $ = selector => document.querySelector(selector);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const prefix = './ground-review/';
  const filters = ['all', 'pending', 'excluded', 'approved'];
  let data, restoring = false;
  let state = {record: 'baima', crop: 'detail', filter: 'all', source: 'MCT-BAIMA', open: false, lineage: 'l531-k'};
  const list = items => `<ul>${items.map(item => `<li>${esc(item)}</li>`).join('')}</ul>`;
  const refs = ids => `<div class="links">${ids.map(id => `<button type="button" data-ground-source="${esc(id)}">${esc(id)} 来源</button>`).join('')}</div>`;
  const link = (url, text) => `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(text)} ↗</a>`;

  function saveState() {
    if (!data || restoring) return;
    const params = new URLSearchParams({...state, open: state.open ? '1' : '0'});
    if (location.hash !== '#' + params.toString()) history.replaceState(null, '', '#' + params.toString());
  }

  function currentRecord() {
    return data.candidates.find(record => record.id === state.record) || data.candidates[0];
  }

  function renderCrop(record) {
    const crop = record.crops.find(item => item.id === state.crop) || record.crops[0];
    state.crop = crop.id;
    $('#ground-crop').value = crop.id;
    $('#ground-image').src = prefix + crop.image;
    $('#ground-image').alt = `${record.title}：${crop.title}，未经地理转换的原图裁片`;
    $('#ground-image-link').href = prefix + crop.image;
    $('#ground-crop-reading').textContent = crop.observation;
    $('#ground-crop-position').textContent = `原扫描像素框 [${crop.raw_scan_crop_xyxy.join(', ')}] · ${crop.image_size_px.join(' × ')} px`;
  }

  function renderRecords() {
    $('#ground-filter').value = state.filter;
    const records = data.candidates.filter(record => state.filter === 'all' || record.status === state.filter);
    $('#ground-count').textContent = `本批具名审核 ${data.named_candidates} 项；当前显示 ${records.length} 项；获准地面控制点 ${data.approved_control_points}。`;
    $('#ground-record').disabled = !records.length;
    $('#ground-empty').hidden = !!records.length;
    $('#ground-record-detail').hidden = !records.length;
    if (!records.length) {
      $('#ground-record').innerHTML = '<option value="">当前没有获准地面点</option>';
      return;
    }
    let record = records.find(item => item.id === state.record) || records[0];
    state.record = record.id;
    $('#ground-record').innerHTML = records.map(item => `<option value="${esc(item.id)}">${esc(item.title)}</option>`).join('');
    $('#ground-record').value = record.id;
    $('#ground-title').textContent = record.title;
    $('#ground-status').textContent = record.status_label;
    $('#ground-crop').innerHTML = record.crops.map(item => `<option value="${esc(item.id)}">${esc(item.title)}</option>`).join('');
    const sheet = data.sheets.find(item => item.id === record.sheet_id);
    $('#ground-scan-link').href = sheet.source_url;
    $('#ground-map-facts').innerHTML = `<dl class="label-value"><dt>图上文字</dt><dd>${record.map_label_read.map(esc).join(' / ')}</dd><dt>符号核读</dt><dd>${esc(record.map_symbol_observation)}</dd><dt>原图年代</dt><dd>${sheet.compiled_year}编图 / ${esc(sheet.printed_date)}印刷</dd><dt>像素框用途</dt><dd>供原图复查的区域，未选测量点</dd></dl><p class="small">原扫描SHA-256<br><code>${esc(sheet.source_sha256)}</code></p>`;
    $('#ground-review-reading').innerHTML = `<h3>现代对应的支持范围</h3><p>${esc(record.modern_correspondence)}</p><h3>跨年代连续性</h3><p>${esc(record.chronology)}</p>${record.continuity_events ? list(record.continuity_events.map(event => `${event.year}：${event.event}`)) : ''}<div class="meaning"><strong>${esc(record.status_label)}</strong>${esc(record.verdict)}</div><h3>尚缺的证据</h3>${list(record.blockers)}<h3>重新审核门槛</h3><p>${esc(record.admission_gate)}</p><p class="small">${esc(record.scope_exclusion)}</p>${refs(record.source_ids)}`;
    renderCrop(record);
  }

  function sourceImage(asset) {
    return `<article class="source-crop"><h3>${esc(asset.title)}</h3><a href="${esc(prefix + asset.image)}" target="_blank" rel="noopener"><img src="${esc(prefix + asset.image)}" alt="${esc(asset.source_id + ' ' + asset.title + ' 原比例边栏裁片')}" loading="lazy"></a><p class="small">完整IIIF原图像素框 [${asset.raw_scan_crop_xyxy.join(', ')}]；${asset.size_px.join(' × ')} px；保存原馆响应字节。</p><p class="small">${esc(asset.credit)} · ${link(asset.rights_uri, '原馆权利声明')}</p><p class="small">裁片SHA-256<br><code>${esc(asset.sha256)}</code></p><p class="small">${link(asset.source_url, '官方IIIF原比例裁片')} · ${link(asset.source_canvas, '对应馆藏canvas')}</p></article>`;
  }

  function renderSource() {
    const source = data.sources.find(item => item.id === state.source) || data.sources[0];
    state.source = source.id;
    $('#ground-source').value = source.id;
    $('#ground-source-toggle').setAttribute('aria-expanded', String(state.open));
    $('#ground-source-toggle').textContent = state.open ? '收起来源详情' : '展开来源详情';
    $('#ground-source-detail').hidden = !state.open;
    const fields = [['机构', source.institution], ['日期', source.published_date || source.retrieved_date || '见原图版记／引用位置'], ['引用位置', source.location], ['核读状态', source.status]];
    let body = `<h3>${esc(source.id)} · ${esc(source.title)}</h3><dl class="label-value">${fields.map(([key, val]) => `<dt>${esc(key)}</dt><dd>${esc(val)}</dd>`).join('')}</dl><p>${esc(source.evidence)}</p>${source.limit ? `<div class="meaning"><strong>适用范围</strong>${esc(source.limit)}</div>` : ''}<p>${link(source.url, '查看来源')}</p>`;
    if (source.catalog_url) body += `<p>${link(source.catalog_url, '馆藏目录')}</p>`;
    if (source.authority_url) body += `<p>${link(source.authority_url, '机构公开档案说明')}</p>`;
    if (source.service_url) body += `<p>${link(source.service_url, '公共目录属性服务')}</p>`;
    if (source.sha256 || source.query_snapshot_sha256) body += `<p class="small">本次读取的${source.sha256 ? 'manifest' : '查询响应'} SHA-256<br><code>${esc(source.sha256 || source.query_snapshot_sha256)}</code></p>`;
    if (source.id === 'UT-7' || source.id === 'UT-8') {
      const sheet = data.sheets.find(item => item.id === (source.id === 'UT-7' ? 'NI49-7' : 'NI49-8'));
      const crop = sheet.compilation_crop;
      body += `<h3>本幅编图来源栏</h3><a href="${esc(prefix + crop.image)}" target="_blank" rel="noopener"><img src="${esc(prefix + crop.image)}" alt="${esc(sheet.id)}编图来源栏"></a><p class="small">原扫描像素框 [${crop.raw_scan_crop_xyxy.join(', ')}]；原图SHA-256<br><code>${esc(sheet.source_sha256)}</code></p>`;
    }
    const assets = data.source_assets.filter(asset => asset.source_id === source.id);
    if (assets.length) body += '<div class="lineage-grid">' + assets.map(sourceImage).join('') + '</div>';
    $('#ground-source-detail').innerHTML = body;
  }

  function renderLineage() {
    const lineage = data.lineage_records.find(item => item.id === state.lineage) || data.lineage_records[0];
    state.lineage = lineage.id;
    $('#lineage-record').value = lineage.id;
    let body = `<h3>${esc(lineage.title)}</h3><span class="status">${esc(lineage.status_label)}</span><p>${esc(lineage.evidence)}</p>`;
    if (lineage.observed_compiled_year) {
      body += `<dl class="label-value"><dt>L500所引年份</dt><dd>${lineage.l500_cited_year}</dd><dt>本实物版记</dt><dd>${esc(lineage.edition_as_printed)}</dd><dt>本实物编图年</dt><dd>${lineage.observed_compiled_year}</dd><dt>上游五万分一</dt><dd>${esc(lineage.parent_source)}</dd><dt>投影／格网</dt><dd>${esc(lineage.projection_as_printed)}<br>${esc(lineage.grid_as_printed)}</dd></dl>`;
    }
    if (lineage.catalog_records) body += list(lineage.catalog_records.map(record => {const a = record.attributes; return `${a.ghzno}：${a.name} / ${a.code} / ${a.scale} / 印刷${a.print_year}，出版${a.publication_year}。仅目录，未核原件。`;}));
    if (lineage.archive_references) body += list(lineage.archive_references.map(record => `${record.call_number}：${record.title} / ${record.catalog_date}`));
    body += `<div class="meaning"><strong>目前没有证明的部分</strong>${esc(lineage.reason_unresolved)}</div><h3>继续核查门槛</h3><p>${esc(lineage.next_gate)}</p>${refs(lineage.source_ids)}`;
    $('#lineage-reading').innerHTML = body;
    $('#lineage-images').innerHTML = lineage.asset_ids.map(id => sourceImage(data.source_assets.find(asset => asset.id === id))).join('');
    $('#lineage-images').hidden = !lineage.asset_ids.length;
  }

  function restoreState() {
    restoring = true;
    const params = new URLSearchParams(location.hash.slice(1));
    const record = data.candidates.find(item => item.id === params.get('record')) || data.candidates[0];
    state = {record: record.id, crop: params.get('crop') || 'detail',
      filter: filters.includes(params.get('filter')) ? params.get('filter') : 'all',
      source: data.sources.some(item => item.id === params.get('source')) ? params.get('source') : record.default_source_id,
      open: params.get('open') === '1',
      lineage: data.lineage_records.some(item => item.id === params.get('lineage')) ? params.get('lineage') : 'l531-k'};
    renderRecords(); renderSource(); renderLineage();
    restoring = false;
    saveState();
  }

  $('#ground-filter').addEventListener('change', event => {
    if (!data) return;
    state.filter = event.target.value;
    renderRecords();
    state.source = currentRecord().default_source_id;
    renderSource(); saveState();
  });
  $('#ground-record').addEventListener('change', event => {
    if (!data) return;
    state.record = event.target.value; state.crop = 'detail';
    state.source = currentRecord().default_source_id;
    renderRecords(); renderSource(); saveState();
  });
  $('#ground-crop').addEventListener('change', event => {
    if (!data) return;
    state.crop = event.target.value; renderCrop(currentRecord()); saveState();
  });
  $('#ground-source').addEventListener('change', event => {
    if (!data) return;
    state.source = event.target.value; renderSource(); saveState();
  });
  $('#ground-source-toggle').addEventListener('click', () => {
    if (!data) return;
    state.open = !state.open; renderSource(); saveState();
  });
  $('#lineage-record').addEventListener('change', event => {
    if (!data) return;
    state.lineage = event.target.value; renderLineage(); saveState();
  });
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-ground-source]');
    if (!data || !button) return;
    state.source = button.dataset.groundSource; state.open = true;
    renderSource(); saveState();
    $('#ground-source-toggle').scrollIntoView({block: 'nearest'});
  });
  window.addEventListener('hashchange', () => { if (data) restoreState(); });
  fetch(prefix + 'metadata.json').then(response => {
    if (!response.ok) throw Error('HTTP ' + response.status);
    return response.json();
  }).then(result => {
    data = result;
    $('#ground-source').innerHTML = data.sources.map(source => `<option value="${esc(source.id)}">${esc(source.id + ' · ' + source.title)}</option>`).join('');
    $('#lineage-record').innerHTML = data.lineage_records.map(record => `<option value="${esc(record.id)}">${esc(record.title)}</option>`).join('');
    $('#ground-gates').innerHTML = data.next_gates.map(gate => `<article class="gate"><h3>${esc(gate.title)}</h3><p>${esc(gate.requires)}</p></article>`).join('');
    restoreState();
    document.documentElement.dataset.groundReviewReady = 'true';
  }).catch(error => {
    $('#ground-error').hidden = false;
    $('#ground-error').textContent = '具名地物审核数据加载失败：' + error.message;
    document.documentElement.dataset.groundReviewReady = 'error';
  });
})();
