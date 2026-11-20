"use strict";
(() => {
  const byId = id => document.getElementById(id);
  const panels = Array.from(document.querySelectorAll("[data-view]"));
  const objects = Array.from(document.querySelectorAll("[data-object]"));
  const views = new Set(panels.map(node => node.dataset.view));
  const controls = ["q","region","level","period"].map(byId);
  const modern = byId("modern");
  const optional = byId("candidate");

  function layers() {
    for (const root of document.querySelectorAll("[data-geoplate]")) {
      for (const [layer,on] of [["modern", modern.checked],["candidate",optional.checked]]) {
        for (const el of root.querySelectorAll('[data-layer="'+layer+'"]')) {
          if (on) el.removeAttribute("display");
          else el.setAttribute("display","none");
        }
      }
    }
  }

  function shareLayers() {
    const panel = panels.find(p => !p.hidden);
    if (!panel || !["city","core"].includes(panel.dataset.view)) return;
    const args = new URLSearchParams();
    if (modern.checked) args.set("modern","1");
    if (!optional.checked) args.set("candidate","0");
    history.replaceState(null,"","#view-"+panel.dataset.view+(args.size?"?"+args:""));
  }

  function saveSvg() {
    const plate = panels.find(p => !p.hidden)?.querySelector("svg");
    if (!plate) return;
    const copy = plate.cloneNode(true);
    const url = new URL("https://mechgouki.github.io/luoyang-city/prosperity-city-atlas.html");
    for (const link of copy.querySelectorAll("a[href]")) {
      const href = link.getAttribute("href");
      if (href.startsWith("#")) link.setAttribute("href",url.href+href);
    }
    const blob = new Blob([new XMLSerializer().serializeToString(copy)],{type:"image/svg+xml"});
    const href = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.download = "luoyang-"+panels.find(p=>!p.hidden).dataset.view+"-layers.svg";
    link.href = href; link.click();
    setTimeout(() => URL.revokeObjectURL(href),1000);
  }

  function show(name) {
    if (!views.has(name)) return;
    for (const el of panels) el.hidden = el.dataset.view !== name;
    for (const a of document.querySelectorAll("[data-tab]")) {
      a.setAttribute("aria-current",String(a.dataset.tab === name));
    }
    byId("layer-tools").hidden = !["city","core"].includes(name);
  }

  function filter(save = false) {
    const [q,region,level,period] = controls.map(n => n.value.trim().toLowerCase());
    let n = 0;
    for (const el of objects) {
      el.hidden = !!((q && !el.dataset.search.toLowerCase().includes(q)) ||
        (region && !el.dataset.regions.toLowerCase().split(" ").includes(region)) ||
        (level && el.dataset.level !== level) || (period && el.dataset.period !== period));
      if (!el.hidden) n++;
    }
    byId("matched").textContent = n ? "显示 "+n+" / "+objects.length+" 个对象" : "没有符合条件的对象。可清除筛选后重试。";
    if (save) {
      const args = new URLSearchParams();
      for (const control of controls) if (control.value) args.set(control.id,control.value);
      history.replaceState(null,"","#filter"+(args.size?"?"+args:""));
    }
  }

  function reset() {
    controls.forEach(n => { n.value = ""; });
    filter();
  }

  function reveal() {
    let key;
    try { key = decodeURIComponent(location.hash.slice(1).split("?")[0]); } catch { return; }
    if (!key) { show("city"); reset(); return; }
    if (key.startsWith("view-") && views.has(key.slice(5))) {
      if (["city","core"].includes(key.slice(5))) {
        const args = new URLSearchParams(location.hash.split("?")[1] || "");
        modern.checked = args.get("modern")==="1";
        optional.checked = args.get("candidate")!=="0";
        layers();
      }
      show(key.slice(5));
      return;
    }
    const target = byId(key);
    if (key === "filter") {
      const args = new URLSearchParams(location.hash.split("?")[1] || "");
      for (const control of controls) control.value = args.get(control.id) || "";
      filter();
      byId("objects").scrollIntoView();
      return;
    }
    if (!target) return;
    const panel = target.closest("[data-view]");
    if (panel) show(panel.dataset.view);
    if (target.matches("[data-object]") && target.hidden) reset();
    for (let el = target; el; el = el.parentElement) if (el.tagName === "DETAILS") el.open = true;
    target.scrollIntoView({block:"start"});
  }

  for (const a of document.querySelectorAll("[data-filter-region]")) {
    a.addEventListener("click", event => {
      if (event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      location.hash="filter?region="+encodeURIComponent(a.dataset.filterRegion);
      reveal();
    });
  }
  for (const control of controls) control.addEventListener(control.id === "q" ? "input" : "change", () => filter(true));
  byId("reset").addEventListener("click", () => { reset(); filter(true); });
  for (const control of [modern,optional]) control.addEventListener("change",() => { layers(); shareLayers(); });
  for (const button of document.querySelectorAll("[data-zoom]")) {
    button.addEventListener("click", () => {
      const zoomed=byId(button.dataset.zoom).classList.toggle("zoomed");
      button.setAttribute("aria-pressed",String(zoomed));
    });
  }
  byId("export-view").addEventListener("click",saveSvg);
  document.documentElement.classList.add("enhanced");
  layers(); show("city"); filter(); reveal();
  addEventListener("hashchange",reveal);
  document.addEventListener("click", event => {
    const a = event.target.closest("a");
    if (a && a.getAttribute("href") === location.hash && location.hash) reveal();
  });
})();
