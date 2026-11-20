(() => {
  const groups = Array.from(document.querySelectorAll("[data-group]"));
  const records = Array.from(document.querySelectorAll("[data-record]"));
  const objects = new Map(Array.from(document.querySelectorAll("[data-object]"), node => [node.id, node]));
  const count = document.getElementById("record-count");
  const selected = document.querySelectorAll(".chips a");
  const current = () => document.getElementById(location.hash.slice(1));

  function render() {
    const target = current();
    const group = target?.dataset.group;
    const record = target?.dataset.record;
    const object = objects.get(target?.id);
    const selectedIds = object ? new Set(object.dataset.records.split(" ")) : null;
    let visible = 0;
    for (const node of records) {
      node.hidden = Boolean((group && node.dataset.owner !== group) ||
        (record && node.dataset.record !== record) || (selectedIds && !selectedIds.has(node.dataset.record)));
      if (!node.hidden) visible++;
    }
    for (const section of groups) {
      section.hidden = !section.querySelector("[data-record]:not([hidden])");
    }
    for (const link of selected) {
      const active = link.hash === location.hash || (visible === records.length && link.hash === "#records");
      if (active) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
    }
    for (const point of document.querySelectorAll("#west-source [data-entity]")) {
      point.classList.toggle("picked", point.dataset.entity === object?.dataset.object);
    }
    if (record) target.querySelector("details").open = true;
    count.textContent = visible + " 条" + (object ? " · " + object.dataset.name : "");
    // Native jumps can run before a formerly filtered record becomes visible.
    if (target && (record || group || object)) target.scrollIntoView({block: "start"});
  }

  document.documentElement.classList.add("enhanced");
  document.getElementById("show-roads").addEventListener("change", event => {
    document.querySelector('#west-source [data-layer="source-roads"]').style.display = event.target.checked ? "" : "none";
  });
  for (const button of document.querySelectorAll("[data-zoom]")) {
    button.addEventListener("click", () => {
      const plate = document.getElementById(button.dataset.zoom);
      const expanded = plate.classList.toggle("zoomed");
      button.setAttribute("aria-pressed", String(expanded));
      if (!expanded) plate.scrollLeft = 0;
    });
  }
  window.addEventListener("hashchange", render);
  window.addEventListener("pageshow", render);
  render();
})();
