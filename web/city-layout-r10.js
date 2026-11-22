"use strict";
(() => {
  const select = document.getElementById("region-select");
  const search = document.getElementById("search");
  const basis = document.getElementById("basis-filter");
  const validRegions = new Set(Array.from(select.options, x => x.value));
  const validBases = new Set(Array.from(basis.options, x => x.value));
  const groups = ["decision", "coverage", "network", "gap"].map(name => ({
    name, rows: Array.from(document.querySelectorAll("." + name + (name === "gap" ? "-card" : "-row"))),
    counter: document.getElementById(name + "-count"),
    empty: document.querySelector('[data-empty-for="' + name + '"]')
  }));
  const sheets = Array.from(document.querySelectorAll(".region-sheet"));
  const hasRegion = (row, value) => value === "all" || row.dataset.region.split(/\s+/).includes(value) || row.dataset.region === "all";

  function writeState(clearHash = false) {
    const url = new URL(location.href);
    for (const [key, value, empty] of [["region", select.value, "all"], ["q", search.value.trim(), ""], ["basis", basis.value, "all"]]) {
      if (value === empty) url.searchParams.delete(key);
      else url.searchParams.set(key, value);
    }
    if (clearHash) url.hash = "";
    history.replaceState(null, "", url);
  }
  function applyFilters(updateURL = true) {
    const query = search.value.trim().toLocaleLowerCase();
    for (const group of groups) {
      let visible = 0;
      for (const row of group.rows) {
        row.hidden = !(hasRegion(row, select.value) && (basis.value === "all" || row.dataset.basis === basis.value) &&
          (!query || row.dataset.search.toLocaleLowerCase().includes(query)));
        if (!row.hidden) visible += 1;
      }
      group.counter.dataset.visibleCount = String(visible);
      group.counter.textContent = "显示 " + visible + " / " + group.rows.length + " 项";
      group.empty.hidden = visible !== 0;
    }
    for (const sheet of sheets) sheet.hidden = !(select.value === "all" || sheet.dataset.region === select.value);
    document.getElementById("region-empty").hidden = select.value !== "register";
    if (updateURL) {
      const target = getHashTarget();
      writeState(Boolean(target && (target.hidden || target.closest("[hidden]"))));
    }
  }
  function readState() {
    const params = new URLSearchParams(location.search);
    select.value = validRegions.has(params.get("region")) ? params.get("region") : "all";
    basis.value = validBases.has(params.get("basis")) ? params.get("basis") : "all";
    search.value = params.get("q") || "";
    applyFilters(false);
  }
  function getHashTarget() {
    if (!location.hash) return null;
    try { return document.getElementById(decodeURIComponent(location.hash.slice(1))); }
    catch (_) { return null; }
  }
  function revealHash() {
    const target = getHashTarget();
    if (!target) return;
    const record = target.closest(".decision-row,.coverage-row,.network-row,.gap-card,.region-sheet");
    if (record && (record.hidden || record.closest("[hidden]"))) {
      search.value = "";
      basis.value = "all";
      if (!hasRegion(record, select.value)) {
        const candidates = record.dataset.region.split(/\s+/);
        select.value = candidates.find(x => validRegions.has(x)) || "all";
      }
      applyFilters(false);
      writeState();
    }
    let ancestor = target.parentElement;
    while (ancestor) {
      if (ancestor.tagName === "DETAILS") ancestor.open = true;
      ancestor = ancestor.parentElement;
    }
    requestAnimationFrame(() => {
      target.scrollIntoView({block: "start", behavior: "auto"});
      if (target.hasAttribute("tabindex")) target.focus({preventScroll: true});
    });
  }
  for (const input of [select, basis]) input.addEventListener("change", () => applyFilters());
  search.addEventListener("input", () => applyFilters());
  document.getElementById("clear-filters").addEventListener("click", () => {
    select.value = basis.value = "all";
    search.value = "";
    applyFilters();
  });
  window.addEventListener("hashchange", revealHash);
  window.addEventListener("popstate", () => { readState(); revealHash(); });
  document.addEventListener("click", event => {
    const anchor = event.target.closest("a");
    if (anchor && anchor.getAttribute("href") === location.hash) requestAnimationFrame(revealHash);
  });

  const maps = new Map();
  for (const viewport of document.querySelectorAll(".map-viewport")) {
    const svg = viewport.querySelector("svg");
    const initial = svg.getAttribute("viewBox").trim().split(/[\s,]+/).map(Number);
    maps.set(viewport.dataset.mapId, {svg, viewport, initial, box: [...initial]});
    viewport.addEventListener("keydown", event => {
      if (event.target !== viewport) return;
      const action = {ArrowLeft:"pan-left", ArrowRight:"pan-right", ArrowUp:"pan-up", ArrowDown:"pan-down", "+":"zoom-in", "=":"zoom-in", "-":"zoom-out", "0":"reset"}[event.key];
      if (action) { event.preventDefault(); changeMap(viewport.dataset.mapId, action); }
    });
  }
  function changeMap(id, action) {
    const map = maps.get(id);
    if (!map) return;
    let [x,y,w,h] = map.box;
    if (action === "reset") {
      [x,y,w,h] = map.initial;
      map.viewport.scrollLeft = map.viewport.scrollTop = 0;
    }
    else if (action === "zoom-in" || action === "zoom-out") {
      const scale = action === "zoom-in" ? .8 : 1.25;
      const nextW = Math.min(map.initial[2] * 2, Math.max(map.initial[2] / 8, w * scale));
      const nextH = h * nextW / w;
      x += (w - nextW) / 2;
      y += (h - nextH) / 2;
      w = nextW; h = nextH;
    } else if (action === "pan-left") x -= w * .15;
    else if (action === "pan-right") x += w * .15;
    else if (action === "pan-up") y -= h * .15;
    else if (action === "pan-down") y += h * .15;
    map.box = [x,y,w,h];
    map.svg.setAttribute("viewBox", map.box.join(" "));
  }
  for (const button of document.querySelectorAll("[data-map-target][data-action]")) {
    button.addEventListener("click", () => changeMap(button.dataset.mapTarget, button.dataset.action));
  }
  readState();
  revealHash();
})();
