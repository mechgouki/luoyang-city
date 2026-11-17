(()=>{"use strict";
const buttons=[...document.querySelectorAll("[data-type]")];
const panels=[...document.querySelectorAll("[data-type-panel]")];
const ids=buttons.map(x=>x.dataset.type);
const fallback="east_ge_gate";
function render(requested,write){
 const value=ids.includes(requested)?requested:fallback;
 buttons.forEach(button=>button.setAttribute("aria-pressed",String(button.dataset.type===value)));
 panels.forEach(panel=>{panel.hidden=panel.dataset.typePanel!==value});
 document.documentElement.dataset.activeType=value;
 if(write){
  const url=new URL(location.href);
  url.searchParams.set("type",value);
  history.replaceState(null,"",url.pathname+url.search+url.hash);
 }
}
document.body.dataset.enhanced="true";
buttons.forEach(button=>button.addEventListener("click",()=>render(button.dataset.type,true)));
window.addEventListener("popstate",()=>render(new URLSearchParams(location.search).get("type"),false));
render(new URLSearchParams(location.search).get("type"),false);
document.documentElement.dataset.architectureReady="true";
})();
