'use strict';
(() => {
  const $ = selector => document.querySelector(selector);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const prefix = './historical-datum/';
  const allowedFilters = ['all', 'pending', 'excluded', 'approved'];
  let data, sheet, crop, filter = 'all', restoring = false;

  function saveState() {
    if (!data || restoring) return;
    const params = new URLSearchParams({sheet: sheet.id, crop: crop.id, source: $('#datum-source-details').open ? 'open' : 'closed', filter});
    if (location.hash !== '#' + params.toString()) history.replaceState(null, '', '#' + params.toString());
  }

  function selectCrop(id, updateHash = true) {
    crop = sheet.crops.find(item => item.id === id) || sheet.crops[0];
    $('#datum-crop-picker').value = crop.id;
    $('#datum-margin-image').src = prefix + crop.image;
    $('#datum-margin-image').alt = `${sheet.id} ${crop.title}，未经地理转换的原图裁片`;
    $('#datum-margin-full').href = prefix + crop.image;
    $('#datum-crop-meaning').textContent = crop.interpretation;
    $('#datum-crop-position').textContent = `原始像素矩形 [${crop.raw_scan_crop_xyxy.join(', ')}] · ${crop.image_size_px.join(' × ')} px · 点击图像查看细字`;
    if (updateHash) saveState();
  }

  function renderCandidates() {
    $('#datum-candidate-filter').value = filter;
    const records = data.candidate_review_queue.filter(record => filter === 'all' || record.status === filter);
    $('#datum-candidate-count').textContent = `显示 ${records.length} 类审核记录；具体已确认实体 0，获准地面控制点 ${data.approved_ground_control_points.length}。`;
    $('#datum-candidate-list').innerHTML = records.length ? records.map(record => `<article class="candidate" data-candidate-id="${esc(record.id)}" data-candidate-status="${esc(record.status)}"><span class="status">${esc(record.status_label)} · 地物类型</span><h3>${esc(record.title)}</h3><p>${esc(record.reason)}</p><p class="small"><b>纳入或重新评审门槛：</b>${esc(record.admission_gate)}</p></article>`).join('') : '<div class="empty"><h3>获准地面控制点 0</h3><p>当前没有具体地物同时通过原图可识别、跨年代同点连续和独立现代坐标来源三项门槛。没有为类型队列附加坐标。</p></div>';
  }

  function renderSheet() {
    const paper = sheet.paper_map, digital = sheet.digitized_product, b4 = sheet.b4_internal_calibration;
    document.querySelectorAll('[data-datum-sheet]').forEach(button => button.setAttribute('aria-pressed', button.dataset.datumSheet === sheet.id ? 'true' : 'false'));
    $('#datum-paper-title').textContent = sheet.id + ' · ' + sheet.title;
    $('#datum-crop-picker').innerHTML = sheet.crops.map(item => `<option value="${esc(item.id)}">${esc(item.title)}</option>`).join('');
    $('#datum-paper-facts').innerHTML = `<dt>版次 / 印刷</dt><dd>${esc(paper.edition)} / ${esc(paper.printed_date)}</dd><dt>编图 / 航片</dt><dd>${paper.compiled_year} / ${esc(paper.planimetry_aerial_photography_years)}年</dd><dt>投影与格网</dt><dd>横轴墨卡托 / 10公里UTM第49带</dd><dt>印刷椭球</dt><dd>${esc(paper.ellipsoid_as_printed)}</dd><dt>格网带标识</dt><dd>${esc(paper.grid_zone_designation_as_printed)}；S为纬带</dd>`;
    $('#datum-scan-link').href = sheet.source_url;
    $('#datum-excerpt').textContent = data.english_excerpt.text;
    $('#datum-digital-facts').innerHTML = `<dt>配准步骤</dt><dd>${esc(digital.georeference_process_date)}</dd><dt>后来赋予基准</dt><dd>${esc(digital.assigned_horizontal_datum)}<br><span class="small">只属于数字产品工作定义</span></dd><dt>控制方式</dt><dd>${esc(digital.registration_control_type)}，共${digital.registration_control_count}组</dd><dt>独立地面检查</dt><dd>元数据没有报告</dd><dt>数字影像尺寸</dt><dd>${digital.raster_size_px.join(' × ')} px；本项目扫描为${sheet.source_size_px.join(' × ')} px</dd>`;
    $('#datum-same-edition').textContent = sheet.cross_product_comparison;
    const location = digital.process_location;
    $('#datum-source-body').innerHTML = `<p><a id="datum-metadata-link" href="${esc(digital.metadata_view_url)}#L${location.line_start}-L${location.line_end}" target="_blank" rel="noopener">查看原馆固定版本XML及处理说明 ↗</a> · <a href="${esc(digital.metadata_url)}" target="_blank" rel="noopener">原始XML</a></p><p>数字字段${esc(digital.assigned_horizontal_datum)}属于后来赋予的WGS84工作定义；原纸图datum仍未识别。</p><p class="small">过程文字：第${location.line_start}—${location.line_end}行；配准日期：第${location.date_line}行。</p><p><code>${esc(location.xpath)}</code></p><p class="small">固定commit<br><code>${esc(digital.repository_commit)}</code></p><p class="small">XML SHA-256<br><code>${esc(digital.metadata_sha256)}</code></p><p class="small">原始扫描SHA-256<br><code>${esc(sheet.source_sha256)}</code></p><p class="small">${esc(digital.date_note)} 元数据另记扫描步骤${esc(digital.scan_process_date)}、元数据日期${esc(digital.metadata_date)}。</p><p class="small">${esc(digital.metadata_projection_warning)}</p><p class="small">原系列基准缺失是数字化机构的明确记录；本项目尚未取得AMS原始大地测量档案独立确认原始基准。</p>`;
    $('#datum-metrics').innerHTML = `<article class="metric"><h3>哈佛：4角格网转换</h3><strong>约 ${digital.rms_m.toFixed(1)} 米</strong><p class="small">同一数字化转换内的RMS；4组印刷角点附近格网坐标，未报告独立地面检查。</p></article><article class="metric"><h3>B4：8点图内拟合</h3><strong>约 ${b4.fit_rms_printed_grid_m.toFixed(1)} 网格米</strong><p class="small">本项目UT扫描中参与拟合的8个蓝网交点，只衡量图内拟合。</p></article><article class="metric"><h3>B4：5点同图留出</h3><strong>约 ${b4.heldout_rms_printed_grid_m.toFixed(1)} 网格米</strong><p class="small">约${b4.heldout_rms_scan_px.toFixed(1)}扫描像素；同一张扫描内部，5点从一开始未参与拟合。</p></article>`;
    selectCrop(crop && sheet.crops.some(item => item.id === crop.id) ? crop.id : sheet.crops[0].id, false);
  }

  function restoreState() {
    restoring = true;
    const params = new URLSearchParams(location.hash.slice(1));
    sheet = data.sheets.find(item => item.id === params.get('sheet')) || data.sheets[0];
    crop = sheet.crops.find(item => item.id === params.get('crop')) || sheet.crops[0];
    filter = allowedFilters.includes(params.get('filter')) ? params.get('filter') : 'all';
    $('#datum-source-details').open = params.get('source') === 'open';
    renderSheet(); renderCandidates();
    restoring = false;
    saveState();
  }

  document.querySelectorAll('[data-datum-sheet]').forEach(button => button.addEventListener('click', () => {
    if (!data) return;
    sheet = data.sheets.find(item => item.id === button.dataset.datumSheet);
    renderSheet(); saveState();
  }));
  $('#datum-crop-picker').addEventListener('change', event => { if (data) selectCrop(event.target.value); });
  $('#datum-candidate-filter').addEventListener('change', event => {
    if (!data) return;
    filter = event.target.value; renderCandidates(); saveState();
  });
  $('#datum-source-details').addEventListener('toggle', saveState);
  window.addEventListener('hashchange', () => { if (data) restoreState(); });
  fetch(prefix + 'metadata.json').then(response => {
    if (!response.ok) throw Error('HTTP ' + response.status);
    return response.json();
  }).then(result => {
    data = result;
    $('#datum-gates').innerHTML = data.next_gates.map(gate => `<article class="gate"><h3>${esc(gate.id)} · ${esc(gate.title)}</h3><p>${esc(gate.requires)}</p><p class="small">达到门槛后：${esc(gate.unlocks)}</p></article>`).join('');
    restoreState();
    document.documentElement.dataset.historicalDatumReady = 'true';
  }).catch(error => {
    $('#datum-error').hidden = false;
    $('#datum-error').textContent = '基准调查数据加载失败：' + error.message;
    document.documentElement.dataset.historicalDatumReady = 'error';
  });
})();
