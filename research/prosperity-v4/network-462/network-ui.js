"use strict";
const plate = document.querySelector("#network-plate svg");
const controls = document.getElementById("layer-controls");
if (plate && controls) {
  for (const input of controls.querySelectorAll("input[data-layer]")) {
    const layer = plate.querySelector("#" + input.dataset.layer);
    if (!layer) continue;
    const update = () => {
      layer.style.display = input.checked ? "" : "none";
    };
    update();
    input.addEventListener("change", update);
    window.addEventListener("pageshow", update);
  }
  controls.hidden = false;
}
const choice = document.getElementById("road-choice");
if (plate && choice) {
  const roads = Array.from(plate.querySelectorAll("#roads [data-road]"));
  const status = document.getElementById("selected-roads");
  function highlight(ids) {
    const selected = ids ? ids.split(" ") : [];
    for (const road of roads) {
      const active = selected.includes(road.dataset.road);
      road.classList.toggle("highlighted", active);
      road.classList.toggle("dimmed", selected.length > 0 && !active);
    }
    if (ids && !Array.from(choice.options).some(option => option.value === ids)) {
      const option = new Option(ids, ids);
      option.dataset.temporary = "true";
      choice.add(option);
    }
    choice.value = ids;
    for (const old of choice.querySelectorAll("option[data-temporary]")) {
      if (old.value !== ids) old.remove();
    }
    status.textContent = ids ? "当前选中 " + ids : "";
  }
  plate.addEventListener("click", event => {
    const item = event.target.closest("[data-road], [data-roads]");
    if (item) highlight(item.dataset.road || item.dataset.roads);
  });
  choice.addEventListener("change", () => highlight(choice.value));
}
