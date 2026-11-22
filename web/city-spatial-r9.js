"use strict";
(() => {
  const rows = [...document.querySelectorAll(".decision-row")];
  const search = document.getElementById("search");
  const nodeFilter = document.getElementById("node-filter");
  const basisFilter = document.getElementById("basis-filter");
  const count = document.getElementById("result-count");
  const empty = document.getElementById("no-results");
  const map = document.getElementById("spatial-map");
  const mapView = document.getElementById("map-view");
  const views = JSON.parse(document.getElementById("map-views").textContent);
  let zoom = 1;
  let panX = 0, panY = 0;
  const allowed = (control, value) => [...control.options].some(option => option.value === value);
  const normalize = value => value.normalize("NFKC").toLocaleLowerCase("zh-CN").trim();
  function writeUrl(replace = false) {
    const url = new URL(location.href);
    for (const [key, value, neutral] of [["q", search.value.trim(), ""], ["node", nodeFilter.value, "all"], ["basis", basisFilter.value, "all"], ["view", mapView.value, "all"]]) {
      if (value === neutral) url.searchParams.delete(key); else url.searchParams.set(key, value);
    }
    const target = document.getElementById(location.hash.slice(1));
    if (target?.classList.contains("decision-row") && target.hidden) url.hash = "";
    if (url.href !== location.href) history[replace ? "replaceState" : "pushState"]({}, "", url.href);
  }
  function filter(updateUrl = true) {
    const q = normalize(search.value);
    let visible = 0;
    for (const row of rows) {
      const show = (!q || normalize(row.dataset.search).includes(q)) &&
        (nodeFilter.value === "all" || row.dataset.node === nodeFilter.value) &&
        (basisFilter.value === "all" || row.dataset.basis.split(" ").includes(basisFilter.value));
      row.hidden = !show;
      visible += Number(show);
    }
    count.textContent = `显示 ${visible} / ${rows.length} 项空间判断`;
    count.dataset.visibleCount = String(visible);
    empty.hidden = visible !== 0;
    if (updateUrl) writeUrl();
  }
  function setMapView(updateUrl = true) {
    zoom = 1;
    panX = 0; panY = 0;
    map.setAttribute("viewBox", views[mapView.value]);
    map.dataset.view = mapView.value;
    map.dataset.originalViewbox = views[mapView.value];
    const viewport = document.getElementById("map-viewport");
    viewport.scrollTo({left:0, top:0, behavior:"instant"});
    if (updateUrl) writeUrl();
  }
  function scaleMap(factor) {
    zoom = Math.min(4, Math.max(1, zoom * factor));
    renderMap();
  }
  function renderMap() {
    const [x, y, w, h] = views[mapView.value].split(" ").map(Number);
    const zw = w/zoom, zh = h/zoom;
    panX = Math.min((w-zw)/2, Math.max(-(w-zw)/2, panX));
    panY = Math.min((h-zh)/2, Math.max(-(h-zh)/2, panY));
    map.setAttribute("viewBox", `${x+(w-zw)/2+panX} ${y+(h-zh)/2+panY} ${zw} ${zh}`);
  }
  function panMap(dx, dy) {
    const [, , w, h] = views[mapView.value].split(" ").map(Number);
    panX += dx * w / zoom * .18; panY += dy * h / zoom * .18;
    renderMap();
  }
  function showHashTarget(scroll = false) {
    const id = location.hash.slice(1);
    if (!/^decision-SP\d\d$/.test(id)) return;
    const target = document.getElementById(id);
    if (!target) return;
    if (target.hidden) {
      search.value = ""; nodeFilter.value = "all"; basisFilter.value = "all";
      filter(false); writeUrl(true);
    }
    if (scroll) {
      target.scrollIntoView({block:"start", behavior:"instant"});
      target.focus({preventScroll:true});
    }
  }
  function restore() {
    const params = new URL(location.href).searchParams;
    search.value = params.get("q") || "";
    nodeFilter.value = allowed(nodeFilter, params.get("node")) ? params.get("node") : "all";
    basisFilter.value = allowed(basisFilter, params.get("basis")) ? params.get("basis") : "all";
    mapView.value = allowed(mapView, params.get("view")) ? params.get("view") : "all";
    filter(false); setMapView(false); showHashTarget(true);
  }
  search.addEventListener("input", () => filter());
  nodeFilter.addEventListener("change", () => filter());
  basisFilter.addEventListener("change", () => filter());
  document.getElementById("reset-filters").addEventListener("click", () => {
    search.value = ""; nodeFilter.value = "all"; basisFilter.value = "all"; filter(); search.focus();
  });
  mapView.addEventListener("change", () => setMapView());
  document.getElementById("zoom-in").addEventListener("click", () => scaleMap(1.25));
  document.getElementById("zoom-out").addEventListener("click", () => scaleMap(1/1.25));
  document.getElementById("reset-map").addEventListener("click", () => setMapView());
  for (const [id, dx, dy] of [["pan-left",-1,0],["pan-right",1,0],["pan-up",0,-1],["pan-down",0,1]]) {
    document.getElementById(id).addEventListener("click", () => panMap(dx, dy));
  }
  document.getElementById("map-viewport").addEventListener("keydown", event => {
    if (event.target !== event.currentTarget || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || zoom <= 1) return;
    const delta = {ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[event.key];
    if (delta) { event.preventDefault(); panMap(...delta); }
  });
  for (const link of document.querySelectorAll("a[data-decision]")) {
    link.addEventListener("click", event => {
      if (event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) return;
      event.preventDefault();
      const hash = "#decision-" + link.dataset.decision;
      if (location.hash !== hash) history.pushState({}, "", location.pathname + location.search + hash);
      showHashTarget(true);
    });
    link.addEventListener("keydown", event => {
      if (event.key === "Enter") { event.preventDefault(); link.dispatchEvent(new MouseEvent("click", {bubbles:true})); }
    });
  }
  addEventListener("hashchange", () => showHashTarget(true));
  addEventListener("popstate", restore);
  restore();
})();
