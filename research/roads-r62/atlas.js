(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const rows = [...document.querySelectorAll('details[data-record]')];
  const query = $('#query'), level = $('#group-filter'), zoom = $('#zoom');
  const layers = ['source', 'inferred', 'unknown'];
  const boxes = Object.fromEntries(layers.map(k => [k, $('#show-' + k)]));
  $('#filter').hidden = false;
  $('#map-tools').hidden = false;
  function hashId() {
    try { return decodeURIComponent(location.hash.slice(1)); } catch { return ''; }
  }
  function hashRecord() {
    const id = hashId().replace(/^map-record-/, '');
    const target = document.getElementById(id);
    return target?.matches('[data-record]') ? target : null;
  }
  function selectRecord(row) {
    document.querySelectorAll('.map-selected').forEach(e => e.classList.remove('map-selected'));
    row.open = true;
    document.querySelectorAll('#all-road-map a').forEach(a => {
      if (a.getAttribute('href') === '#' + row.id) a.classList.add('map-selected');
    });
  }
  function apply(write = true) {
    const q = query.value.trim().toLowerCase();
    let count = 0;
    const exactId = /^[roxtpfgb]\d{2}$/.test(q);
    for (const row of rows) {
      const match = exactId ? row.id.toLowerCase() === q : row.textContent.toLowerCase().includes(q);
      row.hidden = !(match && (!level.value || row.dataset.group === level.value));
      if (!row.hidden) count++;
    }
    for (const group of document.querySelectorAll('.register-group')) group.hidden = !group.querySelector('[data-record]:not([hidden])');
    $('#count').textContent = count ? `${count} / ${rows.length} 条证据记录` : `0 / ${rows.length} 条证据记录 · 没有符合条件的结果`;
    $('#empty').hidden = count > 0;
    for (const key of layers) {
      for (const node of document.querySelectorAll('#all-road-map [data-layer="' + key + '"]')) {
        if (boxes[key].checked) node.removeAttribute('display'); else node.setAttribute('display', 'none');
      }
    }
    $('#all-road-map').style.width = Math.max($('#map-scroll').clientWidth, 1000) * Number(zoom.value) / 100 + 'px';
    $('#zoom-value').textContent = zoom.value + '%';
    if (write) {
      const u = new URL(location.href);
      const selected = hashRecord();
      if (selected?.hidden) {
        u.hash = '';
        document.querySelectorAll('.map-selected').forEach(e => e.classList.remove('map-selected'));
        $('#map-status').hidden = true;
      }
      for (const [key,value] of [['q',query.value],['level',level.value],['layers',layers.filter(k => boxes[k].checked).join(',')],['zoom',zoom.value]]) {
        const defaultValue = key === 'layers' ? layers.join(',') : key === 'zoom' ? '100' : '';
        if (value === defaultValue) u.searchParams.delete(key); else u.searchParams.set(key, value);
      }
      history.replaceState(null, '', u);
    }
  }
  function showOnMap(id, write = true, focus = true) {
    const row = document.getElementById(id);
    const target = document.getElementById('map-record-' + id);
    if (!row?.matches('[data-record]') || !target) return;
    if (row.hidden) { query.value = ''; level.value = ''; }
    // Enable only the layers needed to see this existing map item.
    target.querySelectorAll('[data-layer]').forEach(node => {
      const box = boxes[node.dataset.layer];
      if (box) box.checked = true;
    });
    apply(write);
    selectRecord(row);
    if (write) {
      const u = new URL(location.href);
      u.hash = target.id;
      if (u.href !== location.href) history.pushState(null, '', u);
    }
    const scroll = $('#map-scroll');
    const box = scroll.getBoundingClientRect(), item = target.getBoundingClientRect();
    // Rendered bounds include a source panel's presentation transform; they are screen positions only.
    scroll.scrollLeft += item.left - box.left - Math.max(20, (scroll.clientWidth - item.width) / 2);
    scroll.scrollTop += item.top - box.top - Math.max(20, (scroll.clientHeight - item.height) / 2);
    scroll.scrollIntoView({block: 'center', behavior: 'instant'});
    if (focus) target.focus({preventScroll: true});
    const status = $('#map-status');
    status.textContent = id + ' ' + row.querySelector('.road-title').textContent + '：已返回原图面位置。关系符号与索引排列不表示古代坐标。';
    status.hidden = false;
  }
  function openHash(scroll = true) {
    const id = hashId();
    if (id.startsWith('map-record-')) {
      showOnMap(id.slice('map-record-'.length), false, scroll);
      return;
    }
    const target = document.getElementById(id);
    document.querySelectorAll('.map-selected').forEach(e => e.classList.remove('map-selected'));
    $('#map-status').hidden = true;
    if (!target) return;
    if (target.matches('[data-record]')) {
      if (target.hidden) { query.value = ''; level.value = ''; apply(); }
      selectRecord(target);
    }
    if (scroll) target.scrollIntoView({block: 'start', behavior: 'instant'});
  }
  function restore() {
    const p = new URLSearchParams(location.search);
    query.value = p.get('q') || '';
    level.value = p.get('level') || '';
    const active = p.has('layers') ? p.get('layers').split(',') : layers;
    for (const k of layers) boxes[k].checked = active.includes(k);
    const n = Number(p.get('zoom') || 100);
    zoom.value = String(Math.max(100, Math.min(220, Number.isFinite(n) ? n : 100)));
    apply(false); openHash(false);
  }
  query.addEventListener('input', () => apply());
  level.addEventListener('change', () => apply());
  zoom.addEventListener('input', () => apply());
  Object.values(boxes).forEach(b => b.addEventListener('change', () => apply()));
  $('#clear').addEventListener('click', () => {query.value='';level.value='';apply();});
  window.addEventListener('hashchange', () => openHash());
  window.addEventListener('popstate', restore);
  window.addEventListener('resize', () => apply(false));
  document.querySelectorAll('[data-map-panel]').forEach(button => button.addEventListener('click', () => {
    const scroll = $('#map-scroll');
    const [x, y] = button.dataset.mapPanel.split(',').map(Number);
    const scale = $('#all-road-map').clientWidth / 1440;
    scroll.scrollLeft = x * scale;
    scroll.scrollTop = y * scale;
  }));
  document.addEventListener('click', e => {
    const back = e.target.closest('[data-show-record]');
    if (back) {
      e.preventDefault();
      showOnMap(back.dataset.showRecord);
      return;
    }
    const a = e.target.closest('a[href^="#"]');
    if (a && a.getAttribute('href') === location.hash) openHash();
  });
  document.querySelectorAll('[data-category-link]').forEach(a => a.addEventListener('click', () => {query.value='';level.value=a.dataset.categoryLink;apply();}));
  restore();
})();
