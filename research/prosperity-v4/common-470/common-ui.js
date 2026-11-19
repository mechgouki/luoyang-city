"use strict";
(() => {
  const placeCards = [...document.querySelectorAll("[data-place-card]")];
  const scenes = [...document.querySelectorAll("[data-scene-panel]")];
  const placeIds = new Set(placeCards.map(card => card.dataset.placeCard));
  const sceneIds = new Set(scenes.map(scene => scene.dataset.scenePanel));
  const placeScenes = {C01: "K01", C02: "K02", C03: "", C04: "K01"};
  const state = {place: "C01", scene: "K01", roads: true, walls: true, modern: false};
  const layerControls = Object.fromEntries(["roads", "walls", "modern"].map(key => [key, document.getElementById("layer-" + key)]));
  function writeHash() {
    const query = new URLSearchParams();
    query.set("place", state.place);
    query.set("scene", state.scene);
    for (const key of ["roads", "walls", "modern"]) query.set(key, state[key] ? "1" : "0");
    history.replaceState(null, "", "#" + query.toString());
  }
  function apply(write = true) {
    for (const card of placeCards) card.hidden = card.dataset.placeCard !== state.place;
    document.getElementById("place-overview").hidden = Boolean(state.place);
    for (const button of document.querySelectorAll("[data-place-choice]")) button.setAttribute("aria-pressed", String(button.dataset.placeChoice === state.place));
    for (const mark of document.querySelectorAll("[data-place-id]")) mark.classList.toggle("is-selected", mark.dataset.placeId === state.place);
    for (const scene of scenes) scene.hidden = scene.dataset.scenePanel !== state.scene;
    for (const button of document.querySelectorAll("[data-scene-choice]")) button.setAttribute("aria-pressed", String(button.dataset.sceneChoice === state.scene));
    document.getElementById("scene-none").hidden = Boolean(state.scene);
    for (const key of ["roads", "walls", "modern"]) {
      layerControls[key].checked = state[key];
      for (const layer of document.querySelectorAll(`[data-city-layer="${key}"]`)) {
        layer.style.display = state[key] ? "" : "none";
        layer.setAttribute("aria-hidden", String(!state[key]));
      }
      document.body.dataset[key + "Visible"] = String(state[key]);
    }
    document.body.dataset.currentPlace = state.place;
    document.body.dataset.currentScene = state.scene;
    if (write) writeHash();
  }
  function selectPlace(id, scroll = false) {
    if (!placeIds.has(id)) return;
    state.place = id;
    state.scene = placeScenes[id];
    apply();
    if (scroll && window.innerWidth < 761) document.getElementById("place-" + id).scrollIntoView({block: "start"});
  }
  function selectScene(id, scroll = false) {
    if (!sceneIds.has(id)) return;
    state.scene = id;
    if (id === "K03") state.place = "";
    else if (placeScenes[state.place] !== id) state.place = id === "K01" ? "C01" : "C02";
    apply();
    if (scroll) document.getElementById("city-scenes").scrollIntoView({block: "start"});
  }
  for (const button of document.querySelectorAll("[data-place-choice]")) button.addEventListener("click", event => {event.preventDefault(); selectPlace(button.dataset.placeChoice);});
  for (const link of document.querySelectorAll("[data-place-id]")) link.addEventListener("click", event => {event.preventDefault(); selectPlace(link.dataset.placeId, true);});
  for (const button of document.querySelectorAll("[data-scene-choice]")) button.addEventListener("click", event => {event.preventDefault(); selectScene(button.dataset.sceneChoice);});
  for (const choice of document.querySelectorAll("a[role=button][data-place-choice],a[role=button][data-scene-choice]")) {
    choice.addEventListener("keydown", event => {if (event.key === " ") {event.preventDefault(); choice.click();}});
  }
  for (const link of document.querySelectorAll("[data-open-scene]")) link.addEventListener("click", event => {event.preventDefault(); selectScene(link.dataset.openScene, true);});
  for (const key of ["roads", "walls", "modern"]) layerControls[key].addEventListener("change", () => {state[key] = layerControls[key].checked; apply();});
  const zoom = document.getElementById("map-zoom");
  zoom.addEventListener("click", () => {
    const scroller = document.getElementById("common-map-scroll");
    const enlarged = scroller.classList.toggle("is-zoomed");
    zoom.setAttribute("aria-pressed", String(enlarged));
    zoom.textContent = enlarged ? "恢复全图" : "放大读图";
    if (enlarged) {
      const mark = document.querySelector(`#city-common-map [data-place-id="${state.place || "C01"}"]`);
      if (mark) {
        const view = scroller.getBoundingClientRect(), target = mark.getBoundingClientRect();
        scroller.scrollLeft += target.left - view.left - view.width / 2 + target.width / 2;
      }
    } else scroller.scrollLeft = 0;
  });
  const functionFilter = document.getElementById("function-filter");
  function filterObjects() {
    let count = 0;
    for (const item of document.querySelectorAll("[data-function-object]")) {
      const visible = functionFilter.value === "all" || item.dataset.functionGroup === functionFilter.value;
      item.hidden = !visible;
      count += Number(visible);
    }
    document.getElementById("function-count").textContent = `${count}个对象`;
  }
  functionFilter.addEventListener("change", filterObjects);
  function restoreHash() {
    const hash = location.hash.slice(1);
    if (hash.startsWith("place=")) {
      const values = new URLSearchParams(hash);
      const place = values.get("place"), scene = values.get("scene");
      if (placeIds.has(place)) {state.place = place; state.scene = placeScenes[place];}
      if (sceneIds.has(scene)) {
        state.scene = scene;
        if (scene === "K03") state.place = "";
        else if (placeScenes[state.place] !== scene) state.place = scene === "K01" ? "C01" : "C02";
      }
      for (const key of ["roads", "walls", "modern"]) if (["0", "1"].includes(values.get(key))) state[key] = values.get(key) === "1";
      apply(false);
    } else if (/^place-C0[1-4]$/.test(hash)) selectPlace(hash.slice(6));
    else if (/^scene-K0[1-3]$/.test(hash)) selectScene(hash.slice(6));
    else {
      apply(false);
      let id;
      try {id = decodeURIComponent(hash);} catch (_) {return;}
      if (id) document.getElementById(id)?.scrollIntoView({block: "start"});
    }
  }
  document.documentElement.classList.add("common-enhanced");
  restoreHash();
  filterObjects();
  window.addEventListener("hashchange", restoreHash);
  window.addEventListener("pageshow", () => {apply(false); filterObjects();});
  document.body.dataset.commonReady = "1";
})();
