(() => {
  "use strict";
  const comparison = document.getElementById("image-comparison");
  const controls = document.getElementById("view-controls");
  if (!comparison || !controls) return;
  const buttons = [...controls.querySelectorAll("button[data-view]")];
  const figures = [...comparison.querySelectorAll("[data-version]")];
  const status = document.getElementById("view-status");
  const allowed = new Set(["v13r2", "v13", "v12", "compare"]);
  const descriptions = {
    v13r2: "当前显示 V13 二修候选全幅。可切换前版 V13、当前首页 V12，或查看前后并排。",
    v13: "当前显示前版 V13 全幅，其既有审看记录完整保留。",
    v12: "当前显示已批准的 V12 全幅，正式首页继续采用此图。",
    compare: "本轮二修与前版 V13 同时展示；窄屏依此顺序排列。"
  };
  function show(view, updateUrl) {
    if (!allowed.has(view)) view = "v13r2";
    comparison.dataset.view = view;
    for (const figure of figures) {
      figure.hidden = view === "compare"
        ? !["v13r2", "v13"].includes(figure.dataset.version)
        : figure.dataset.version !== view;
    }
    for (const button of buttons) button.setAttribute("aria-pressed", String(button.dataset.view === view));
    status.textContent = descriptions[view];
    if (updateUrl) {
      const url = new URL(location.href);
      if (view === "v13r2") url.searchParams.delete("view");
      else url.searchParams.set("view", view);
      history.replaceState(null, "", url);
    }
  }
  controls.hidden = false;
  for (const button of buttons) button.addEventListener("click", () => show(button.dataset.view, true));
  window.addEventListener("popstate", () => show(new URL(location.href).searchParams.get("view"), false));
  show(new URL(location.href).searchParams.get("view"), false);
})();
