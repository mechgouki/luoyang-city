(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const rows = [...document.querySelectorAll('details[data-record]')];
  const query = $('#query'), level = $('#group-filter'), zoom = $('#zoom');
  const layers = ['source', 'inferred', 'unknown'];
  const boxes = Object.fromEntries(layers.map(k => [k, $('#show-' + k)]));
  $('#filter').hidden = false;
  $('#map-tools').hidden = false;
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
      let selected;
      try { selected = document.getElementById(decodeURIComponent(u.hash.slice(1))); } catch { selected = null; }
      if (selected?.matches('[data-record]') && selected.hidden) {
        u.hash = '';
        document.querySelectorAll('.map-selected').forEach(e => e.classList.remove('map-selected'));
      }
      for (const [key,value] of [['q',query.value],['level',level.value],['layers',layers.filter(k => boxes[k].checked).join(',')],['zoom',zoom.value]]) {
        const defaultValue = key === 'layers' ? layers.join(',') : key === 'zoom' ? '100' : '';
        if (value === defaultValue) u.searchParams.delete(key); else u.searchParams.set(key, value);
      }
      history.replaceState(null, '', u);
    }
  }
  function openHash(scroll = true) {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    const target = document.getElementById(id);
    document.querySelectorAll('.map-selected').forEach(e => e.classList.remove('map-selected'));
    if (!target) return;
    if (target.matches('[data-record]')) {
      if (target.hidden) { query.value = ''; level.value = ''; apply(); }
      target.open = true;
      document.querySelectorAll('#all-road-map a').forEach(a => { if(a.getAttribute('href') === '#' + id) a.classList.add('map-selected'); });
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
    const a = e.target.closest('a[href^="#"]');
    if (a && a.getAttribute('href') === location.hash) openHash();
  });
  document.querySelectorAll('[data-category-link]').forEach(a => a.addEventListener('click', () => {query.value='';level.value=a.dataset.categoryLink;apply();}));
  restore();
})();
