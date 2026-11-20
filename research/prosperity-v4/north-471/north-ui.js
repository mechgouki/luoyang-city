"use strict";
(() => {
  const places = new Set([...document.querySelectorAll("[data-north-card]")].map(n => n.dataset.northCard));
  const groups = new Set(["all", ...[...document.querySelectorAll("[data-evidence-group]")].map(n => n.dataset.evidenceGroup)]);
  const records = Object.fromEntries([...document.querySelectorAll("[data-evidence-id]")].map(n => [n.dataset.evidenceId, n]));
  const state = {view: "north", place: "N01", group: "all", record: "", roads: true, walls: true, modern: false};
  const layers = ["roads", "walls", "modern"];
  const zoom = document.getElementById("north-map-zoom");
  function save() {
    const query = new URLSearchParams();
    for (const key of ["view", "place", "group", "record"]) query.set(key, state[key]);
    for (const key of layers) query.set(key, state[key] ? "1" : "0");
    history.replaceState(null, "", "#" + query.toString());
  }
  function apply(write = true) {
    for (const card of document.querySelectorAll("[data-north-card]")) card.hidden = card.dataset.northCard !== state.place;
    for (const choice of document.querySelectorAll("[data-north-choice]")) choice.setAttribute("aria-pressed", String(choice.dataset.northChoice === state.place));
    for (const mark of document.querySelectorAll("[data-north-id]")) mark.classList.toggle("is-selected", mark.dataset.northId === state.place);
    for (const panel of document.querySelectorAll("[data-map-panel]")) panel.hidden = panel.dataset.mapPanel !== state.view;
    for (const choice of document.querySelectorAll("[data-map-choice]")) choice.setAttribute("aria-pressed", String(choice.dataset.mapChoice === state.view));
    for (const group of document.querySelectorAll("[data-evidence-group]")) group.hidden = state.group !== "all" && group.dataset.evidenceGroup !== state.group;
    for (const choice of document.querySelectorAll("[data-group-choice]")) choice.setAttribute("aria-pressed", String(choice.dataset.groupChoice === state.group));
    for (const [id, record] of Object.entries(records)) record.classList.toggle("is-selected", id === state.record);
    const count = Object.values(records).filter(n => !n.closest("[data-evidence-group]").hidden).length;
    document.getElementById("evidence-count").textContent = `${count}条证据`;
    for (const layer of layers) {
      document.getElementById("north-layer-" + layer).checked = state[layer];
      for (const node of document.querySelectorAll(`[data-city-layer="${layer}"]`)) {
        node.style.display = state[layer] ? "" : "none";
        node.setAttribute("aria-hidden", String(!state[layer]));
      }
      document.body.dataset[layer + "Visible"] = String(state[layer]);
    }
    const scroller = document.querySelector(`[data-map-scroll="${state.view}"]`);
    const enlarged = scroller.classList.contains("is-zoomed");
    zoom.setAttribute("aria-pressed", String(enlarged));
    zoom.textContent = enlarged ? "恢复全图" : "放大读图";
    document.body.dataset.currentNorth = state.place;
    document.body.dataset.currentMap = state.view;
    document.body.dataset.currentGroup = state.group;
    document.body.dataset.currentRecord = state.record;
    if (write) save();
  }
  function choosePlace(id, scroll) {
    if (!places.has(id)) return;
    state.place = id;
    apply();
    if (scroll && innerWidth < 761) document.getElementById("north-" + id).scrollIntoView({block: "start"});
  }
  function chooseRecord(id, scroll) {
    const record = records[id];
    if (!record) return;
    state.record = id;
    state.group = record.closest("[data-evidence-group]").dataset.evidenceGroup;
    apply();
    record.querySelector("[data-reading-detail]").open = true;
    if (scroll) record.scrollIntoView({block: "start"});
  }
  for (const choice of document.querySelectorAll("[data-north-choice]")) choice.addEventListener("click", e => {e.preventDefault(); choosePlace(choice.dataset.northChoice, false);});
  for (const mark of document.querySelectorAll("[data-north-id]")) mark.addEventListener("click", e => {e.preventDefault(); choosePlace(mark.dataset.northId, true);});
  for (const choice of document.querySelectorAll("[data-map-choice]")) choice.addEventListener("click", e => {e.preventDefault(); state.view = choice.dataset.mapChoice; apply();});
  for (const choice of document.querySelectorAll("[data-group-choice]")) choice.addEventListener("click", e => {e.preventDefault(); state.group = choice.dataset.groupChoice; state.record = ""; apply();});
  for (const link of document.querySelectorAll("[data-open-evidence]")) link.addEventListener("click", e => {e.preventDefault(); chooseRecord(link.dataset.openEvidence, true);});
  for (const choice of document.querySelectorAll("a[role=button]")) choice.addEventListener("keydown", e => {if (e.key === " ") {e.preventDefault(); choice.click();}});
  for (const layer of layers) document.getElementById("north-layer-" + layer).addEventListener("change", e => {state[layer] = e.target.checked; apply();});
  zoom.addEventListener("click", () => {
    const scroller = document.querySelector(`[data-map-scroll="${state.view}"]`);
    const enlarged = scroller.classList.toggle("is-zoomed");
    if (enlarged) {
      const point = scroller.querySelector(`[data-north-id="${state.place}"] circle[data-source-feature-id]`);
      if (point) {
        const view = scroller.getBoundingClientRect(), target = point.getBoundingClientRect();
        scroller.scrollLeft += target.left - view.left - view.width / 2 + target.width / 2;
      }
    } else scroller.scrollLeft = 0;
    apply(false);
  });
  function restore() {
    const hash = location.hash.slice(1);
    if (hash.startsWith("view=")) {
      const query = new URLSearchParams(hash);
      if (["north", "overview"].includes(query.get("view"))) state.view = query.get("view");
      if (places.has(query.get("place"))) state.place = query.get("place");
      if (groups.has(query.get("group"))) state.group = query.get("group");
      state.record = Object.hasOwn(records, query.get("record")) ? query.get("record") : "";
      for (const layer of layers) if (["0", "1"].includes(query.get(layer))) state[layer] = query.get(layer) === "1";
      if (state.record) state.group = records[state.record].closest("[data-evidence-group]").dataset.evidenceGroup;
      apply(false);
      if (state.record) {
        records[state.record].querySelector("[data-reading-detail]").open = true;
        records[state.record].scrollIntoView({block: "start"});
      }
    } else if (hash.startsWith("north-") && places.has(hash.slice(6))) {
      state.place = hash.slice(6); apply(false);
      document.getElementById(hash).scrollIntoView({block: "start"});
    } else if (hash.startsWith("evidence-") && Object.hasOwn(records, hash.slice(9))) {
      const id = hash.slice(9); state.record = id; state.group = records[id].closest("[data-evidence-group]").dataset.evidenceGroup;
      apply(false); records[id].querySelector("[data-reading-detail]").open = true; records[id].scrollIntoView({block: "start"});
    } else if (hash === "map-overview" || hash === "map-north") {
      state.view = hash.slice(4); apply(false);
    } else apply(false);
  }
  restore();
  document.body.dataset.northReady = "1";
  window.addEventListener("hashchange", restore);
})();
