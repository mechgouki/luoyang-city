"use strict";
(() => {
  const panels = Array.from(document.querySelectorAll("[data-map-panel]"));
  const choices = Array.from(document.querySelectorAll("[data-map-choice]"));
  const cards = Array.from(document.querySelectorAll("[data-context-card]"));
  const anchorChoice = document.getElementById("anchor-choice");
  const heading = document.getElementById("context-heading");
  const waterSearch = document.getElementById("water-search");
  const rows = Array.from(document.querySelectorAll("[data-water-id]"));
  const state = {map: "frame-06a", anchor: "", water: ""};
  function updateHash() {
    const query = new URLSearchParams();
    query.set("map", state.map);
    if (state.anchor) query.set("anchor", state.anchor);
    if (state.water) query.set("water", state.water);
    history.replaceState(null, "", "#" + query.toString());
  }
  function showMap(id, write = true) {
    if (!panels.some(panel => panel.dataset.mapPanel === id)) return;
    state.map = id;
    for (const panel of panels) panel.hidden = panel.dataset.mapPanel !== id;
    for (const choice of choices) choice.setAttribute("aria-pressed", String(choice.dataset.mapChoice === id));
    document.body.dataset.currentMap = id;
    if (write) updateHash();
  }
  function showContext(id, write = true, scroll = false) {
    if (id && !cards.some(card => card.dataset.contextCard === id)) return;
    state.anchor = id;
    anchorChoice.value = id;
    for (const card of cards) card.hidden = Boolean(id) && card.dataset.contextCard !== id;
    for (const button of document.querySelectorAll("[data-context-choice]")) {
      button.setAttribute("aria-pressed", String(button.dataset.contextChoice === id));
    }
    for (const mark of document.querySelectorAll("[data-context-id]")) {
      mark.classList.toggle("is-selected", mark.dataset.contextId === id);
    }
    heading.textContent = id ? anchorChoice.selectedOptions[0].textContent + " · 关系联读" : "门道周围，联读水系与城市关系";
    document.body.dataset.currentAnchor = id;
    if (write) updateHash();
    if (scroll) document.getElementById("contexts").scrollIntoView({block: "start"});
  }
  for (const choice of choices) choice.addEventListener("click", () => showMap(choice.dataset.mapChoice));
  for (const button of document.querySelectorAll("[data-context-choice]")) {
    button.addEventListener("click", () => showContext(button.dataset.contextChoice));
  }
  anchorChoice.addEventListener("change", () => showContext(anchorChoice.value));
  for (const link of document.querySelectorAll("[data-open-jianchun]")) {
    link.addEventListener("click", event => {
      event.preventDefault();
      showMap("frame-06a", false);
      showContext("geo-jianchun-gate", true, true);
    });
  }
  for (const mark of document.querySelectorAll("[data-context-id]")) {
    mark.addEventListener("click", event => {
      event.preventDefault();
      showContext(mark.dataset.contextId, true, true);
    });
  }
  const modern = document.getElementById("modern-river-469");
  const modernToggle = document.getElementById("modern-river-toggle");
  const updateModern = () => {
    modern.style.display = modernToggle.checked ? "" : "none";
    modern.setAttribute("aria-hidden", String(!modernToggle.checked));
  };
  modernToggle.addEventListener("change", updateModern);
  for (const button of document.querySelectorAll("[data-zoom]")) {
    button.addEventListener("click", () => {
      const scroll = document.querySelector(`[data-map-scroll="${button.dataset.zoom}"]`);
      const zoomed = scroll.classList.toggle("is-zoomed");
      button.setAttribute("aria-pressed", String(zoomed));
      button.textContent = zoomed ? "恢复全图" : "放大读图";
    });
  }
  function filterWater(value) {
    const query = value.trim().toLocaleLowerCase();
    let count = 0;
    for (const row of rows) {
      const visible = !query || (row.dataset.waterId + " " + row.dataset.waterName).toLocaleLowerCase().includes(query);
      row.hidden = !visible;
      count += Number(visible);
    }
    document.getElementById("water-count").textContent = `${count}项`;
    document.getElementById("water-empty").hidden = count > 0;
  }
  waterSearch.addEventListener("input", () => filterWater(waterSearch.value));
  function revealTarget(id) {
    const target = document.getElementById(id);
    if (!target) return;
    if (target.matches("details")) target.open = true;
    if (target.matches("[data-context-card]")) showContext(target.dataset.contextCard, false);
    if (target.matches("[data-water-id]")) {
      waterSearch.value = "";
      filterWater("");
      state.water = target.dataset.waterId;
    }
    target.scrollIntoView({block: "start"});
  }
  document.addEventListener("click", event => {
    const link = event.target.closest('a[href^="#evidence-"],a[href^="#water-"]');
    if (!link) return;
    event.preventDefault();
    const id = link.getAttribute("href").slice(1);
    revealTarget(id);
    history.replaceState(null, "", "#" + id);
  });
  function restoreHash() {
    const hash = location.hash.slice(1);
    if (hash.startsWith("map=")) {
      const values = new URLSearchParams(hash);
      showMap(values.get("map") || "frame-06a", false);
      showContext(values.get("anchor") || "", false);
      const water = values.get("water");
      if (water && /^W\d{2}$/.test(water)) revealTarget("water-" + water);
    } else if (hash) {
      revealTarget(decodeURIComponent(hash));
    }
  }
  document.documentElement.classList.add("backbone-enhanced");
  showMap("frame-06a", false);
  updateModern();
  restoreHash();
  window.addEventListener("hashchange", restoreHash);
  window.addEventListener("pageshow", updateModern);
  document.body.dataset.backboneReady = "1";
})();
