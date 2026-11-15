/* A local source-reading view. Its camera never generates geographic coordinates. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const viewport = $('map-viewport');
  const escape = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const safeURL = (value, base = location.href) => {
    try { const url = new URL(value, base); return ['http:', 'https:'].includes(url.protocol) ? url.href : ''; }
    catch (_) { return ''; }
  };
  let data, state, svg, request = 0, drag = null, suppressClick = false;
  const cameras = {}, cache = new Map();
  const views = ['local', 'city', 'diagnostics'];

  function readState() {
    const params = new URLSearchParams(location.hash.slice(1));
    const component = params.get('component');
    return {
      view: views.includes(params.get('view')) ? params.get('view') : 'local',
      component: data.components.some((item) => item.id === component) ? component : data.default_component,
      source: params.get('source') !== '0',
    };
  }
  function stateHash() {
    return '#' + new URLSearchParams({view: state.view, component: state.component, source: state.source ? '1' : '0'}).toString();
  }
  function writeState(replace = false) {
    const hash = stateHash();
    if (location.hash !== hash) history[replace ? 'replaceState' : 'pushState'](null, '', hash);
  }
  function camera() { return cameras[state.view] || data.maps[state.view].viewBox.slice(); }
  function setCamera(box) {
    if (!svg || !box.every(Number.isFinite)) return;
    cameras[state.view] = box;
    svg.setAttribute('viewBox', box.map((v) => Number(v.toFixed(3))).join(' '));
  }
  function zoom(factor, anchor) {
    if (!svg) return;
    const box = camera(), full = data.maps[state.view].viewBox;
    const width = Math.max(full[2] / 8, Math.min(full[2] * 1.5, box[2] * factor));
    const ratio = width / box[2], pivot = anchor || [box[0] + box[2] / 2, box[1] + box[3] / 2];
    setCamera([pivot[0] + (box[0] - pivot[0]) * ratio, pivot[1] + (box[1] - pivot[1]) * ratio, width, box[3] * ratio]);
  }
  function drawingPoint(event) {
    const matrix = svg?.getScreenCTM();
    if (!matrix) return null;
    return new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
  }
  function focusComponent() {
    if (!svg) return;
    const nodes = Array.from(svg.querySelectorAll('[data-component-id]')).filter((node) => node.dataset.componentId === state.component);
    if (!nodes.length) return;
    const boxes = nodes.map((node) => {
      const box = node.getBBox(), transform = svg.getCTM().inverse().multiply(node.getCTM());
      return [[box.x, box.y], [box.x + box.width, box.y], [box.x, box.y + box.height], [box.x + box.width, box.y + box.height]].map(([x,y]) => new DOMPoint(x,y).matrixTransform(transform));
    }).flat();
    const left = Math.min(...boxes.map((p) => p.x)), top = Math.min(...boxes.map((p) => p.y));
    const right = Math.max(...boxes.map((p) => p.x)), bottom = Math.max(...boxes.map((p) => p.y));
    const full = data.maps[state.view].viewBox;
    let width = Math.max(240, right - left + 100), height = Math.max(165, bottom - top + 100);
    if (width / height < full[2] / full[3]) width = height * full[2] / full[3];
    else height = width * full[3] / full[2];
    setCamera([(left + right - width) / 2, (top + bottom - height) / 2, width, height]);
  }
  function renderDetail() {
    const item = data.components.find((component) => component.id === state.component);
    if (!item) return;
    $('component-select').value = item.id;
    const links = item.source_links.map((source) => {
      const url = safeURL(source.url);
      return url ? `<a href="${escape(url)}" target="_blank" rel="noopener">${escape(source.label)} ↗</a>` : '';
    }).join('');
    $('component-detail').innerHTML = `<h2>${escape(item.label)}</h2><p class="evidence-label">${escape(item.evidence_label)}</p><p class="measure-label">图内量读 / 构成说明</p><p class="measure-value">${escape(item.dimensions_label)}</p><dl class="component-facts"><dt>原件怎样支持这一构成</dt><dd>${escape(item.note)}</dd><dt>读数使用范围</dt><dd>${escape(item.trace_note)}</dd></dl><div class="component-links">${links}<a href="#source-comparison">对照来源原图 ↓</a><a href="./prosperity-gate/readings.csv" download>下载像素与局部米制读数</a></div><details class="reading-details"><summary>查看读数层说明</summary><p>${escape(item.reading_label)}</p><p>图内原点与轴向只服务本图量读；这些坐标不作为古址经纬度发布。</p></details>`;
    document.querySelectorAll('[data-compare-component]').forEach((node) => {
      const selected = node.getAttribute('data-compare-component') === item.id;
      node.classList.toggle('compare-selected', selected);
      node.setAttribute('aria-pressed', String(selected));
    });
    if (!svg) return;
    let found = false;
    svg.querySelectorAll('[data-component-id]').forEach((node) => {
      const active = node.dataset.componentId === state.component;
      node.classList.toggle('component-selected', active);
      node.classList.toggle('is-selected', active);
      node.setAttribute('aria-pressed', String(active));
      found ||= active;
    });
    $('focus-component').disabled = !found;
  }
  function renderSourceLayer() {
    const layer = svg?.querySelector('#source-layer');
    $('source-toggle').checked = state.source;
    $('source-toggle').disabled = !layer;
    if (layer) layer.style.display = state.source ? '' : 'none';
  }
  async function getDrawing(view) {
    const url = safeURL(data.maps[view].url);
    if (!url) throw new Error('图件地址不可用');
    if (!cache.has(url)) cache.set(url, fetch(url).then(async (response) => {
      if (!response.ok) throw new Error('图件暂时未能载入');
      const document = new DOMParser().parseFromString(await response.text(), 'image/svg+xml');
      if (document.querySelector('parsererror') || document.documentElement.localName !== 'svg') throw new Error('图件格式不可用');
      document.querySelectorAll('script,foreignObject').forEach((node) => node.remove());
      document.querySelectorAll('*').forEach((node) => {
        Array.from(node.attributes).forEach((attribute) => {
          if (/^on/i.test(attribute.name)) node.removeAttribute(attribute.name);
          if (attribute.localName === 'href') {
            const value = attribute.value;
            if (node.localName === 'image' && /^data:image\/(png|jpeg);base64,/i.test(value)) return;
            if (value.startsWith('#')) return;
            const resolved = safeURL(value, url);
            if (resolved) node.setAttributeNS(attribute.namespaceURI, attribute.name, resolved);
            else node.removeAttributeNode(attribute);
          }
        });
      });
      return document.documentElement;
    }).catch((error) => { cache.delete(url); throw error; }));
    return (await cache.get(url)).cloneNode(true);
  }
  async function applyState(next, historyMode = 'push') {
    const changed = !state || state.view !== next.view || !svg;
    state = next;
    if (historyMode !== 'none') writeState(historyMode === 'replace');
    document.querySelectorAll('#mode-switch button').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.view === state.view)));
    $('view-note').textContent = data.maps[state.view].note;
    $('map-title').textContent = data.maps[state.view].title;
    $('open-map').href = safeURL(data.maps[state.view].url);
    renderDetail();
    if (!changed) { renderSourceLayer(); return; }
    const token = ++request, currentView = state.view;
    viewport.setAttribute('aria-busy', 'true');
    document.documentElement.dataset.gateReady = 'false';
    try {
      const drawing = await getDrawing(currentView);
      if (token !== request) return;
      svg = document.importNode(drawing, true);
      svg.removeAttribute('width'); svg.removeAttribute('height');
      svg.setAttribute('role', 'group');
      svg.setAttribute('aria-label', data.maps[currentView].title);
      const valid = new Map(data.components.map((item) => [item.id, item]));
      svg.querySelectorAll('[data-component-id]').forEach((node) => {
        const item = valid.get(node.dataset.componentId);
        if (!item) { node.removeAttribute('data-component-id'); return; }
        node.setAttribute('role', 'button'); node.setAttribute('tabindex', '0');
        node.setAttribute('aria-label', `${item.label}，查看出处`);
      });
      viewport.replaceChildren(svg);
      viewport.dataset.view = currentView;
      setCamera(camera()); renderDetail(); renderSourceLayer();
      viewport.setAttribute('aria-busy', 'false');
      document.documentElement.dataset.gateReady = 'true';
    } catch (error) {
      if (token !== request) return;
      viewport.setAttribute('aria-busy', 'false');
      viewport.querySelector('.error-message')?.remove();
      const message = document.createElement('p'); message.className = 'error-message';
      message.textContent = `${error.message}。可以使用“放大当前图件”或下方下载入口继续阅读。`;
      viewport.append(message);
    }
  }
  function choose(component) {
    if (data.components.some((item) => item.id === component)) applyState({...state, component});
  }
  function bind() {
    document.querySelectorAll('#mode-switch button').forEach((button) => {
      button.disabled = false;
      button.addEventListener('click', () => applyState({...state, view: button.dataset.view}));
    });
    ['zoom-in', 'zoom-out', 'reset-map', 'copy-link', 'component-select'].forEach((id) => { $(id).disabled = false; });
    $('zoom-in').addEventListener('click', () => zoom(.78));
    $('zoom-out').addEventListener('click', () => zoom(1.28));
    $('reset-map').addEventListener('click', () => setCamera(data.maps[state.view].viewBox.slice()));
    $('focus-component').addEventListener('click', focusComponent);
    $('component-select').addEventListener('change', (event) => choose(event.target.value));
    $('source-toggle').addEventListener('change', (event) => applyState({...state, source: event.target.checked}));
    const comparisonOpacity = $('comparison-opacity');
    const updateComparison = () => {
      const opacity = Math.max(0, Math.min(90, Number(comparisonOpacity.value) || 0));
      $('comparison-underlay').setAttribute('opacity', String(opacity / 100));
      $('comparison-opacity-value').textContent = opacity === 0 ? '0%（仅描线）' : opacity + '% 原图叠加';
    };
    comparisonOpacity.disabled = false;
    $('comparison-mix').disabled = false;
    $('comparison-clear').disabled = false;
    comparisonOpacity.addEventListener('input', updateComparison);
    $('comparison-mix').addEventListener('click', () => { comparisonOpacity.value = '55'; updateComparison(); });
    $('comparison-clear').addEventListener('click', () => { comparisonOpacity.value = '0'; updateComparison(); });
    updateComparison();
    $('source-comparison').addEventListener('click', (event) => {
      const node = event.target.closest?.('[data-compare-component]');
      if (node) choose(node.getAttribute('data-compare-component'));
    });
    $('source-comparison').addEventListener('keydown', (event) => {
      const node = event.target.closest?.('[data-compare-component]');
      if (node && ['Enter', ' '].includes(event.key)) {
        event.preventDefault(); choose(node.getAttribute('data-compare-component'));
      }
    });
    $('copy-link').addEventListener('click', async () => {
      writeState(true);
      try {
        if (!navigator.clipboard?.writeText) throw new Error('clipboard unavailable');
        await navigator.clipboard.writeText(location.href);
        $('share-url').hidden = true; $('share-status').textContent = '已复制当前视图、所选构成与原件底图状态的链接。';
      } catch (_) {
        $('share-url').value = location.href; $('share-url').hidden = false; $('share-url').focus(); $('share-url').select();
        $('share-status').textContent = '当前视图链接已选中，可直接复制。';
      }
    });
    viewport.addEventListener('click', (event) => {
      if (suppressClick) { suppressClick = false; return; }
      const node = event.target.closest?.('[data-component-id]');
      if (node) choose(node.dataset.componentId);
    });
    viewport.addEventListener('keydown', (event) => {
      const node = event.target.closest?.('[data-component-id]');
      if (node && ['Enter',' '].includes(event.key)) { event.preventDefault(); choose(node.dataset.componentId); }
      else if (['+', '='].includes(event.key)) { event.preventDefault(); zoom(.78); }
      else if (event.key === '-') { event.preventDefault(); zoom(1.28); }
      else if (event.key === 'Home') { event.preventDefault(); setCamera(data.maps[state.view].viewBox.slice()); }
    });
    viewport.addEventListener('wheel', (event) => {
      if (!svg) return;
      event.preventDefault(); const point = drawingPoint(event);
      zoom(event.deltaY > 0 ? 1.12 : .89, point ? [point.x, point.y] : null);
    }, {passive:false});
    viewport.addEventListener('pointerdown', (event) => {
      if (!svg || event.button !== 0 || !event.isPrimary) return;
      const matrix = svg.getScreenCTM(); if (!matrix) return;
      drag = {id:event.pointerId, x:event.clientX, y:event.clientY, matrix:matrix.inverse(), camera:camera().slice(), moved:false};
      suppressClick = false;
    });
    viewport.addEventListener('pointermove', (event) => {
      if (!drag || event.pointerId !== drag.id) return;
      if (Math.hypot(event.clientX - drag.x, event.clientY - drag.y) < 6 && !drag.moved) return;
      drag.moved = true; viewport.classList.add('dragging');
      if (!viewport.hasPointerCapture(event.pointerId)) viewport.setPointerCapture(event.pointerId);
      const start = new DOMPoint(drag.x, drag.y).matrixTransform(drag.matrix);
      const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(drag.matrix);
      setCamera([drag.camera[0] + start.x - point.x, drag.camera[1] + start.y - point.y, drag.camera[2], drag.camera[3]]);
    });
    const endDrag = (event) => {
      if (!drag || event.pointerId !== drag.id) return;
      suppressClick = drag.moved; drag = null; viewport.classList.remove('dragging');
      if (viewport.hasPointerCapture(event.pointerId)) viewport.releasePointerCapture(event.pointerId);
    };
    viewport.addEventListener('pointerup', endDrag); viewport.addEventListener('pointercancel', endDrag);
    window.addEventListener('hashchange', () => {
      if (location.hash.includes('=')) applyState(readState(), 'replace');
    });
    window.addEventListener('popstate', () => {
      if (location.hash.includes('=')) applyState(readState(), 'none');
    });
  }
  async function verifyRelease() {
    try {
      const response = await fetch('./build-info.json');
      if (!response.ok) throw new Error('metadata unavailable');
      const info = await response.json();
      const verified = info.source_commit === data.source_commit && info.prosperity_gate?.version === data.version;
      $('version-status').dataset.verified = String(verified);
      $('version-status').textContent = verified ? `阊阖门 P3.1 · 原图对比与P4中轴数据已发布 · ${data.source_commit.slice(0, 8)}` : '阊阖门 P3.1 · 发布信息待重新核对';
    } catch (_) { $('version-status').textContent = '阊阖门 P3 · 当前无法核对发布信息；原件与下载仍可查阅'; }
  }
  async function start() {
    try {
      const response = await fetch('./prosperity-gate/data.json');
      if (!response.ok) throw new Error('资料暂时未能载入');
      data = await response.json();
      if (data.version !== 'prosperity-gate-v3' || !data.components?.length || views.some((view) => !data.maps?.[view])) throw new Error('资料版本不匹配');
      bind();
      await applyState(readState(), location.hash && !location.hash.includes('=') ? 'none' : 'replace');
      await verifyRelease();
    } catch (error) {
      const message = document.createElement('p'); message.className = 'error-message';
      message.textContent = `${error.message}。静态图件、原件和资料下载仍可使用。`;
      viewport.append(message);
      $('version-status').textContent = '当前以静态图件阅读';
    }
  }
  start();
})();
