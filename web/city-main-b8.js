/* The current inspector distinguishes the frozen catalog from later review. */
const beforeCityEntityB8 = renderEntity;
let cityLedgerB8 = null, cityCasesB8 = null;
renderEntity = function(e) {
  let base = beforeCityEntityB8(e);
  if (!cityLedgerB8) return base;
  const row = cityLedgerB8.entities.find(x => x.id === e.id);
  if (!row) return base;
  const labels = {individual:'单实体交互关联',group_member:'共享／组内交互关联',no_interactive_target:'原交互层无目标'};
  if (e.temporal_state) {
    const label = escapeHTML(stateLabel[e.temporal_state] || e.temporal_state);
    base = base.replace('<span class="mini-tag warn">' + label + '</span>', '<span class="mini-tag warn baseline-temporal">基线字段：' + label + '</span>');
  }
  if (row.display_name && row.display_name !== e.name) {
    base = base.replace('<h2 class="inspector-name">' + escapeHTML(e.name) + '</h2>', '<h2 class="inspector-name">' + escapeHTML(row.display_name) + '</h2><div class="ref-line">封存名录：' + escapeHTML(e.name) + '</div>');
  }
  const cases = (row.case_ids || []).map(id => cityCasesB8.records.find(c => c.id === id)).filter(Boolean);
  const links = cases.map(c => '<a href="./dual-city-review.html#view=cases&case=' + encodeURIComponent(c.id) + '">' + escapeHTML(c.id + ' ' + c.short_title) + '</a>').join('<br>');
  const note = row.current_review || {};
  const currentNote = note.temporal_label ? '<p class="city-current-reading"><strong>' + escapeHTML(note.temporal_label) + '</strong> ' + escapeHTML(note.note || '') + '</p>' : '';
  const scope = row.marker_state === 'group_member' ? '同组对象共用阅读锚点，不能拆为独立街址。' : row.marker_state === 'individual' ? '单实体点击关联不等于古址已经独立定位。' : '道路、水体与附录可能无点击点；没有目标不等于漏画。';
  return '<section class="city-review-coverage" style="padding:15px;border-left:3px solid #98713d;background:#f3efdf;margin-bottom:18px"><h3>全城总校核 · B8</h3><p>' + escapeHTML(labels[row.marker_state]) + '；' + escapeHTML(scope) + '</p>' + currentNote + '<p>' + (cases.length ? links : '本批完成结构关联清点，未为此对象新增史证结论。') + '</p><a href="./dual-city-review.html#view=map&entity=' + encodeURIComponent(e.id) + '">查看当前清单、分区与历批证据 ↗</a></section>' + base;
};
(async () => {
  try {
    const result = await Promise.all([atlasFetch('./city-review/ledger.json'),atlasFetch('./city-review/cases.json')]);
    if (result.some(r => !r.ok)) throw Error('B8 审校资料读取失败');
    [cityLedgerB8,cityCasesB8] = await Promise.all(result.map(r => r.json()));
    for (let i = 0; i < 600 && document.documentElement.dataset.luonanMainReady !== 'true'; i++) await new Promise(r => setTimeout(r,50));
    if (document.documentElement.dataset.luonanMainReady !== 'true') throw Error('前序地图未就绪');
    const control = document.querySelector('#b8-review-toggle');
    const overlay = document.querySelector('#map-viewport #city-audit-overlay-b8');
    if (control && overlay) control.addEventListener('change', () => {overlay.style.visibility = control.checked ? 'visible' : 'hidden';});
    if (selectedEntity) selectEntity(selectedEntity,false,false);
    document.documentElement.dataset.cityMainReady = 'true';
  } catch(e) {console.error(e);document.documentElement.dataset.cityMainReady = 'error';}
})();
