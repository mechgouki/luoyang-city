/* Segment selection is a display state. It never changes the downloaded evidence. */
(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const $$ = selector => Array.from(document.querySelectorAll(selector));
  const relationNames = {flow:'明确流向', connection:'相连，方向未定', adjacency:'仅相邻', proposal:'开渠提议', hypothesis:'复原解释'};
  const periodNames = {text_context:'文献语境', older_event:'早期记事／旧迹', broad_survey:'宽年代调查', interpretation:'后出解释', proposal:'提议，实施待证'};
  const explanations = {
    text:'文献层显示原典所述的水路关系；著书语境和早期记事分别记录，不能据此认定每段在516—528年的每一年均通水。',
    survey:'旧迹与调查层显示早期事件和宽年代遗迹。渠迹存在、测得渠深，与盛时实际过水是不同的问题。',
    all:'完整证据层并列原典、旧迹、调查、提议与复原解释。虚线或仅相邻的关系，不补成已证的连续水路。'
  };
  let data, bySource, activePlate, activeSegment, layer = 'text', zoom = 1;
  const rememberedLayers = new Map();
  let center = {x:510, y:380}, drag = null, suppressClickUntil = 0;

  function element(tag, text, className) {
    const result = document.createElement(tag);
    if (text !== undefined && text !== null) result.textContent = text;
    if (className) result.className = className;
    return result;
  }
  function visible(segment) {
    return layer === 'all' || (layer === 'text' && segment.period_class === 'text_context') ||
      (layer === 'survey' && ['older_event','broad_survey'].includes(segment.period_class));
  }
  function panel() { return $$('[data-plate-panel]').find(item => item.dataset.platePanel === activePlate.id); }
  function svg() { return panel().querySelector('svg'); }
  function setUrl() {
    const state = new URLSearchParams({map:activePlate.id, layer});
    if (activeSegment) state.set('segment', activeSegment.id);
    const hash = '#' + state.toString();
    if (location.hash !== hash) history.replaceState(null, '', hash);
  }
  function renderDetail() {
    const target = $('#segment-detail');
    target.replaceChildren();
    const link = $('#full-evidence-link');
    if (!activeSegment) {
      target.append(element('p', '这一图在当前证据层没有可显示的水段。可切换“全部证据”，查看旧迹、调查或未证提议。', 'empty-detail'));
      link.href = '#evidence';
      link.textContent = '查看完整依据表 ↓';
      return;
    }
    const segment = activeSegment;
    target.append(element('h3', segment.label));
    const meta = element('div', null, 'detail-meta');
    meta.append(element('span', relationNames[segment.relationship_type], 'detail-tag'));
    meta.append(element('span', periodNames[segment.period_class], 'detail-tag period'));
    target.append(meta, element('p', '这段水路能确定什么', 'detail-caption'));
    target.append(element('p', segment.reading, 'detail-reading'));
    if (segment.quote) {
      target.append(element('p', '回到原文', 'detail-caption'));
      target.append(element('blockquote', segment.quote, 'detail-quote'));
    }
    target.append(element('p', segment.locator, 'detail-locator'));
    const list = element('ul', null, 'detail-sources');
    (segment.source_ids || []).forEach(id => {
      const source = bySource.get(id);
      if (!source) return;
      const item = element('li'), anchor = element('a', source.title);
      anchor.href = source.url;
      anchor.target = '_blank';
      anchor.rel = 'noopener';
      item.append(anchor);
      list.append(item);
    });
    target.append(list, element('p', '仍不能推出什么', 'detail-caption'));
    target.append(element('p', segment.limit, 'detail-limit'));
    link.href = '#evidence-' + segment.id;
    link.textContent = '在完整依据表中查看此段 ↓';
  }
  function updateSelection() {
    $$('[data-plate-panel] .water-segment').forEach(group => {
      const selected = group.dataset.segmentId === (activeSegment && activeSegment.id);
      group.classList.toggle('is-selected', selected);
      group.setAttribute('aria-pressed', String(selected));
    });
    $('#segment-choice').value = activeSegment ? activeSegment.id : '';
    renderDetail();
    setUrl();
  }
  function selectSegment(id) {
    const segment = activePlate.segments.find(item => item.id === id);
    if (!segment || !visible(segment)) return;
    activeSegment = segment;
    updateSelection();
  }
  function updateLayer(preferredId) {
    rememberedLayers.set(activePlate.id, layer);
    const shown = activePlate.segments.filter(visible);
    const nodes = new Set(shown.flatMap(segment => [segment.from, segment.to]));
    panel().querySelectorAll('.water-segment').forEach(group => {
      const segment = activePlate.segments.find(item => item.id === group.dataset.segmentId);
      group.toggleAttribute('hidden', !visible(segment));
      group.setAttribute('tabindex', visible(segment) ? '0' : '-1');
    });
    panel().querySelectorAll('.water-node').forEach(group => {
      group.classList.toggle('is-muted', !nodes.has(group.dataset.nodeId) && !['reference','label','city'].includes(group.dataset.kind));
    });
    const select = $('#segment-choice');
    select.replaceChildren();
    shown.forEach(segment => {
      const index = activePlate.segments.indexOf(segment) + 1;
      const option = element('option', String(index).padStart(2,'0') + ' · ' + segment.label);
      option.value = segment.id;
      select.append(option);
    });
    if (!shown.length) {
      const option = element('option', '本层暂无图段');
      option.value = '';
      select.append(option);
    }
    select.disabled = shown.length === 0;
    activeSegment = shown.find(item => item.id === preferredId) || shown.find(item => activeSegment && item.id === activeSegment.id) || shown[0] || null;
    $('#water-layer').value = layer;
    $('#visible-count').textContent = `显示 ${shown.length} / ${activePlate.segments.length} 段`;
    $('#layer-explanation').textContent = explanations[layer];
    updateSelection();
  }
  function updateView() {
    const width = 1020 / zoom, height = 760 / zoom;
    center.x = Math.max(width/2, Math.min(1020-width/2, center.x));
    center.y = Math.max(height/2, Math.min(760-height/2, center.y));
    svg().setAttribute('viewBox', `${center.x-width/2} ${center.y-height/2} ${width} ${height}`);
    panel().querySelector('.map-viewport').classList.toggle('is-zoomed', zoom > 1);
    $('#zoom-level').textContent = Math.round(zoom*100) + '%';
    $('#zoom-out').disabled = zoom <= 1;
    $('#zoom-in').disabled = zoom >= 3;
  }
  function resetView() { zoom = 1; center = {x:510, y:380}; updateView(); }
  function changeZoom(step) { zoom = Math.max(1, Math.min(3, Math.round((zoom+step)*100)/100)); updateView(); }
  function choosePlate(id, segmentId, restoreLayer) {
    activePlate = data.plates.find(item => item.id === id) || data.plates[0];
    if (restoreLayer && ['text','survey','all'].includes(restoreLayer)) layer = restoreLayer;
    else layer = rememberedLayers.get(activePlate.id) || activePlate.default_layer || 'text';
    $$('[data-plate-panel]').forEach(item => { item.hidden = item.dataset.platePanel !== activePlate.id; });
    $$('[data-plate-choice]').forEach(button => { button.setAttribute('aria-pressed', String(button.dataset.plateChoice === activePlate.id)); });
    activeSegment = null;
    const requested = activePlate.segments.find(item => item.id === segmentId);
    if (requested && !visible(requested)) layer = 'all';
    resetView();
    updateLayer(segmentId);
  }
  function restore() {
    const params = new URLSearchParams(location.hash.slice(1));
    if (params.has('map')) {
      choosePlate(params.get('map'), params.get('segment'), params.get('layer'));
    } else if (!activePlate) {
      const ordinaryAnchor = location.hash;
      choosePlate(data.plates[0].id);
      if (ordinaryAnchor) history.replaceState(null, '', ordinaryAnchor);
    }
  }
  function pointerDown(event) {
    if (zoom <= 1 || event.button > 0) return;
    const map = svg();
    const clicked = event.target.closest('.water-segment');
    drag = {pointer:event.pointerId, x:event.clientX, y:event.clientY, center:{...center}, moved:false,
      segmentId:clicked ? clicked.dataset.segmentId : null};
    map.setPointerCapture(event.pointerId);
    panel().querySelector('.map-viewport').classList.add('is-dragging');
  }
  function pointerMove(event) {
    if (!drag || event.pointerId !== drag.pointer) return;
    const rect = svg().getBoundingClientRect();
    const dx = event.clientX - drag.x, dy = event.clientY - drag.y;
    if (Math.hypot(dx,dy) > 4) drag.moved = true;
    center = {x:drag.center.x - dx * (1020/zoom) / rect.width, y:drag.center.y - dy * (760/zoom) / rect.height};
    updateView();
  }
  function pointerEnd(event) {
    if (!drag || event.pointerId !== drag.pointer) return;
    if (drag.moved) suppressClickUntil = performance.now() + 250;
    else if (drag.segmentId) selectSegment(drag.segmentId);
    drag = null;
    panel().querySelector('.map-viewport').classList.remove('is-dragging');
    if (svg().hasPointerCapture(event.pointerId)) svg().releasePointerCapture(event.pointerId);
  }
  function init() {
    data = JSON.parse($('#water-study-data').textContent);
    bySource = new Map(data.sources.map(source => [source.id, source]));
    ['map-tabs','map-tools','layer-explanation','map-help','evidence-panel'].forEach(id => { document.getElementById(id).hidden = false; });
    $$('[data-plate-choice]').forEach(button => button.addEventListener('click', () => choosePlate(button.dataset.plateChoice)));
    $('#water-layer').addEventListener('change', event => { layer = event.target.value; updateLayer(); });
    $('#segment-choice').addEventListener('change', event => selectSegment(event.target.value));
    $('#zoom-in').addEventListener('click', () => changeZoom(.25));
    $('#zoom-out').addEventListener('click', () => changeZoom(-.25));
    $('#zoom-reset').addEventListener('click', resetView);
    $$('[data-water-map]').forEach(map => {
      map.setAttribute('role', 'group');
      map.setAttribute('tabindex', '0');
      map.addEventListener('click', event => {
        if (performance.now() < suppressClickUntil) return;
        const group = event.target.closest('.water-segment');
        if (group) selectSegment(group.dataset.segmentId);
      });
      map.addEventListener('keydown', event => {
        const group = event.target.closest('.water-segment');
        if (group && ['Enter',' '].includes(event.key)) {
          event.preventDefault(); selectSegment(group.dataset.segmentId); return;
        }
        if (event.key === '+' || event.key === '=') { event.preventDefault(); changeZoom(.25); }
        if (event.key === '-') { event.preventDefault(); changeZoom(-.25); }
        if (event.key === 'Home') { event.preventDefault(); resetView(); }
        if (zoom > 1 && ['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key)) {
          event.preventDefault();
          center.x += event.key === 'ArrowLeft' ? -45/zoom : event.key === 'ArrowRight' ? 45/zoom : 0;
          center.y += event.key === 'ArrowUp' ? -45/zoom : event.key === 'ArrowDown' ? 45/zoom : 0;
          updateView();
        }
      });
      map.addEventListener('pointerdown', pointerDown);
      map.addEventListener('pointermove', pointerMove);
      map.addEventListener('pointerup', pointerEnd);
      map.addEventListener('pointercancel', pointerEnd);
    });
    window.addEventListener('hashchange', restore);
    restore();
    document.documentElement.dataset.water467Ready = 'true';
  }
  try { init(); } catch (error) {
    document.documentElement.dataset.water467Ready = 'error';
    console.error('Water study controls:', error);
    $$('[data-plate-panel]').forEach(item => { item.hidden = false; });
    $$('.water-segment').forEach(item => item.removeAttribute('hidden'));
    ['map-tabs','map-tools','layer-explanation','map-help','evidence-panel'].forEach(id => { document.getElementById(id).hidden = true; });
  }
})();
