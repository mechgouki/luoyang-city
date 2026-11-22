/* All evidence is in the HTML. This file adds navigation, selection and filtering. */
(() => {
  'use strict';

  const byId = id => document.getElementById(id);
  const all = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const rows = all('.segment[data-segment]');
  const query = byId('segment-query');
  const node = byId('node-filter');
  const evidence = byId('evidence-filter');
  const maps = new Map(all('.map-figure[data-map]').map(figure => [figure.dataset.map, {
    figure,
    viewport: figure.querySelector('.map-scroll'),
    svg: figure.querySelector('.map-scroll > svg'),
    slider: figure.querySelector('[data-map-zoom]'),
    output: figure.querySelector('[data-zoom-value]'),
    status: figure.querySelector('.map-status'),
  }]));
  const searchText = new Map(rows.map(row => [row, row.textContent.toLocaleLowerCase()]));
  let restoring = false;

  function writeURL(url, replace = false) {
    try {
      if (url.href !== location.href) history[replace ? 'replaceState' : 'pushState']({}, '', url);
    } catch (_) {
      // file:// readers still keep usable native fragment navigation.
      if (url.hash !== location.hash) location.hash = url.hash;
    }
  }

  function setParam(url, key, value) {
    if (value) url.searchParams.set(key, value);
    else url.searchParams.delete(key);
  }

  function syncFilters(url) {
    setParam(url, 'q', query.value.trim());
    setParam(url, 'node', node.value);
    setParam(url, 'evidence', evidence.value);
  }

  function filterRows() {
    const word = query.value.trim().toLocaleLowerCase();
    const exactID = /^[roxtpfgb]\d{2}$/i.test(word);
    let count = 0;
    rows.forEach(row => {
      const matchText = !word || (exactID ? row.dataset.segment.toLocaleLowerCase() === word : searchText.get(row).includes(word));
      const matchNode = !node.value || row.dataset.nodes.split(/\s+/).includes(node.value);
      const matchEvidence = !evidence.value || row.dataset.evidence === evidence.value;
      row.hidden = !(matchText && matchNode && matchEvidence);
      if (!row.hidden) count += 1;
    });
    byId('segment-count').textContent = `${count} / ${rows.length} 条来源记录`;
    byId('segment-empty').hidden = count !== 0;
  }

  function clearSelection() {
    all('.is-selected').forEach(item => item.classList.remove('is-selected'));
    all('[data-map] [aria-current], .panorama-point[aria-current]').forEach(item => item.removeAttribute('aria-current'));
    maps.forEach(map => { map.status.hidden = true; });
  }

  function reveal(target) {
    if (target.matches('.segment') && target.hidden) {
      query.value = '';
      node.value = '';
      evidence.value = '';
      filterRows();
      const url = new URL(location.href);
      syncFilters(url);
      writeURL(url, true);
    }
    let item = target;
    while (item && item !== document.body) {
      if (item.tagName === 'DETAILS') item.open = true;
      item = item.parentElement;
    }
  }

  function focusAndScroll(target) {
    target.scrollIntoView({ block: 'start', behavior: 'auto' });
    if (!target.hasAttribute('tabindex') && !target.matches('a, button, input, select, summary')) target.setAttribute('tabindex', '-1');
    if (typeof target.focus === 'function') target.focus({ preventScroll: true });
  }

  function guideSelection(id) {
    const card = byId(`guide-${id}`);
    const point = byId(`point-${id}`);
    if (card) card.classList.add('is-selected');
    if (point) {
      point.classList.add('is-selected');
      point.setAttribute('aria-current', 'true');
    }
  }

  function sizeMap(map) {
    if (!map.svg) return;
    const base = Math.max(map.viewport.clientWidth, Number(map.figure.dataset.minWidth) || 820);
    map.svg.style.width = `${base * Number(map.slider.value) / 100}px`;
    map.output.value = `${map.slider.value}%`;
    map.output.textContent = `${map.slider.value}%`;
  }

  function chooseMap(key, segment, zoom, shouldFocus = true) {
    const map = maps.get(key);
    if (!map) return false;
    if (zoom && Number.isFinite(Number(zoom))) {
      map.slider.value = String(Math.max(100, Math.min(220, Math.round(Number(zoom) / 20) * 20)));
    }
    sizeMap(map);
    const targets = segment ? all('[data-segment-ref]', map.svg).filter(item => item.dataset.segmentRef.split(/[\s,]+/).includes(segment)) : [];
    targets.forEach(item => {
      item.classList.add('is-selected');
      item.setAttribute('aria-current', 'true');
    });
    const selected = targets[0];
    if (selected) {
      const viewport = map.viewport.getBoundingClientRect();
      const box = selected.getBoundingClientRect();
      map.viewport.scrollTo({
        left: map.viewport.scrollLeft + box.left - viewport.left - (map.viewport.clientWidth - box.width) / 2,
        top: map.viewport.scrollTop + box.top - viewport.top - (map.viewport.clientHeight - box.height) / 2,
        behavior: 'auto',
      });
      const row = byId(`segment-${segment}`);
      const name = row ? row.querySelector('.segment-title').firstChild.textContent.trim() : segment;
      map.status.textContent = `已定位 ${segment} · ${name}。高亮沿用本图已有路迹、符号或关系说明。`;
      map.status.hidden = false;
      if (shouldFocus) {
        map.viewport.scrollIntoView({ block: 'start', behavior: 'auto' });
        if (!selected.hasAttribute('tabindex')) selected.setAttribute('tabindex', '-1');
        if (typeof selected.focus === 'function') selected.focus({ preventScroll: true });
      }
    } else {
      if (segment) {
        map.status.textContent = `${segment} 尚无可选择的本图路迹，已返回所属关系图；请结合图旁说明阅读。`;
        map.status.hidden = false;
      }
      if (shouldFocus) focusAndScroll(map.viewport);
    }
    return true;
  }

  function restoreFromURL(shouldFocus = true) {
    restoring = true;
    const url = new URL(location.href);
    query.value = url.searchParams.get('q') || '';
    node.value = url.searchParams.get('node') || '';
    evidence.value = url.searchParams.get('evidence') || '';
    filterRows();
    clearSelection();
    let id;
    try { id = decodeURIComponent(url.hash.slice(1)); } catch (_) { id = url.hash.slice(1); }
    const target = byId(id);
    if (!target) {
      restoring = false;
      return;
    }
    if (id.startsWith('map-')) {
      const key = id.slice(4);
      const sameMap = url.searchParams.get('map') === key;
      chooseMap(key, sameMap ? url.searchParams.get('segment') : '', sameMap ? url.searchParams.get('zoom') : '', shouldFocus);
    } else {
      reveal(target);
      if (target.matches('.segment, .finding, .guide-card, .water-card')) target.classList.add('is-selected');
      if (target.matches('.guide-card')) guideSelection(target.dataset.guide);
      if (id === 'panorama' && url.searchParams.get('guide')) {
        byId('show-panorama-guides').checked = true;
        document.querySelector('.panorama-points').hidden = false;
        guideSelection(url.searchParams.get('guide'));
      }
      if (shouldFocus) focusAndScroll(target);
    }
    restoring = false;
  }

  document.addEventListener('click', event => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const anchor = event.target.closest('a');
    if (!anchor || anchor.hasAttribute('download') || anchor.target === '_blank') return;
    const raw = anchor.getAttribute('href') || anchor.getAttribute('xlink:href');
    if (!raw || !raw.startsWith('#')) return;
    let id;
    try { id = decodeURIComponent(raw.slice(1)); } catch (_) { return; }
    if (!byId(id)) return;
    event.preventDefault();
    const url = new URL(location.href);
    url.hash = raw;
    ['map', 'segment', 'zoom', 'guide'].forEach(key => url.searchParams.delete(key));
    if (anchor.dataset.returnMap) {
      const key = anchor.dataset.returnMap;
      setParam(url, 'map', key);
      setParam(url, 'segment', anchor.dataset.returnSegment);
      const map = maps.get(key);
      if (map && map.slider.value !== '100') setParam(url, 'zoom', map.slider.value);
    }
    if (anchor.dataset.returnGuide) setParam(url, 'guide', anchor.dataset.returnGuide);
    writeURL(url);
    restoreFromURL();
  });

  function changeFilters() {
    filterRows();
    const url = new URL(location.href);
    syncFilters(url);
    const selected = byId(url.hash.slice(1));
    if (selected && selected.matches('.segment') && selected.hidden) {
      url.hash = '#register';
      ['map', 'segment', 'zoom'].forEach(key => url.searchParams.delete(key));
      clearSelection();
    }
    writeURL(url, true);
  }

  query.addEventListener('input', changeFilters);
  node.addEventListener('change', changeFilters);
  evidence.addEventListener('change', changeFilters);
  byId('segment-clear').addEventListener('click', () => {
    query.value = '';
    node.value = '';
    evidence.value = '';
    changeFilters();
    query.focus();
  });
  byId('show-panorama-guides').addEventListener('change', event => {
    document.querySelector('.panorama-points').hidden = !event.target.checked;
  });
  maps.forEach((map, key) => {
    map.figure.querySelector('.map-controls').hidden = false;
    map.viewport.addEventListener('keydown', event => {
      if (event.target !== map.viewport || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
      const delta = { ArrowLeft: [-40, 0], ArrowRight: [40, 0], ArrowUp: [0, -40], ArrowDown: [0, 40] }[event.key];
      if (!delta) return;
      // Native animated key scrolling can continue after "reset" and move the
      // map again. Finish each viewport key step before the next interaction.
      // Events from SVG links retain their normal keyboard behavior.
      event.preventDefault();
      map.viewport.scrollBy({ left: delta[0], top: delta[1], behavior: 'instant' });
    });
    map.slider.addEventListener('input', () => {
      sizeMap(map);
      const url = new URL(location.href);
      if (url.searchParams.get('map') !== key) url.searchParams.delete('segment');
      url.searchParams.delete('guide');
      setParam(url, 'map', key);
      setParam(url, 'zoom', map.slider.value === '100' ? '' : map.slider.value);
      url.hash = `#map-${key}`;
      writeURL(url, true);
    });
    map.figure.querySelector('[data-map-reset]').addEventListener('click', () => {
      clearSelection();
      map.slider.value = '100';
      sizeMap(map);
      map.viewport.scrollTo({ left: 0, top: 0, behavior: 'instant' });
      const url = new URL(location.href);
      ['segment', 'zoom', 'guide'].forEach(name => url.searchParams.delete(name));
      url.searchParams.set('map', key);
      url.hash = `#map-${key}`;
      writeURL(url, true);
      map.viewport.focus({ preventScroll: true });
    });
    sizeMap(map);
  });
  byId('segment-filters').hidden = false;
  document.querySelector('.guide-toggle').hidden = false;
  if (typeof ResizeObserver !== 'undefined') {
    const observer = new ResizeObserver(entries => {
      entries.forEach(entry => {
        const figure = entry.target.closest('[data-map]');
        const map = maps.get(figure.dataset.map);
        sizeMap(map);
      });
    });
    maps.forEach(map => observer.observe(map.viewport));
  } else {
    window.addEventListener('resize', () => maps.forEach(sizeMap));
  }
  window.addEventListener('popstate', () => { if (!restoring) restoreFromURL(); });
  window.addEventListener('hashchange', () => { if (!restoring) restoreFromURL(); });
  restoreFromURL(false);
  if (location.hash) requestAnimationFrame(() => restoreFromURL());
})();
