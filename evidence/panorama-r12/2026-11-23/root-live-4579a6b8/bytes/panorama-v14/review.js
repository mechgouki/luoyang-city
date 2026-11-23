(() => {
  "use strict";
  const comparison = document.getElementById("image-comparison");
  const controls = document.getElementById("view-controls");
  if (!comparison || !controls) return;
  const buttons = [...controls.querySelectorAll("button[data-view]")];
  const figures = [...comparison.querySelectorAll("[data-version]")];
  const status = document.getElementById("view-status");
  const rejected = comparison.dataset.imageStatus === "needs_revision";
  const allowed = new Set(["v14", "v13r2", "v12", "compare"]);
  const descriptions = {
    v14: rejected
      ? "当前显示 V14 未通过试绘全幅。实际阻断问题列于图前；当前首页继续采用 V12，可切换 V13 二修或前后并排核对。"
      : "当前显示 V14 空间校正版候选全幅。可切换改图基础 V13 二修、当前首页 V12，或查看前后并排。",
    v13r2: "当前显示 V13 二修全幅，其既有审看记录完整保留。",
    v12: "当前显示已批准的 V12 全幅，正式首页继续采用此图。",
    compare: rejected
      ? "V14 未通过试绘与 V13 二修同时展示；窄屏依此顺序排列。对照展示不改变未通过状态。"
      : "V14 与 V13 二修同时展示；窄屏依此顺序排列。"
  };
  function show(view, updateUrl) {
    if (!allowed.has(view)) view = "v14";
    comparison.dataset.view = view;
    for (const figure of figures) {
      figure.hidden = view === "compare"
        ? !["v14", "v13r2"].includes(figure.dataset.version)
        : figure.dataset.version !== view;
    }
    for (const button of buttons) button.setAttribute("aria-pressed", String(button.dataset.view === view));
    status.textContent = descriptions[view];
    if (updateUrl) {
      const url = new URL(location.href);
      if (view === "v14") url.searchParams.delete("view");
      else url.searchParams.set("view", view);
      history.replaceState(null, "", url);
    }
  }
  controls.hidden = false;
  for (const button of buttons) button.addEventListener("click", () => show(button.dataset.view, true));
  window.addEventListener("popstate", () => show(new URL(location.href).searchParams.get("view"), false));
  show(new URL(location.href).searchParams.get("view"), false);
})();
