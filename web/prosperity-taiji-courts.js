(()=>{"use strict";
const phaseIds=["wei_jin","northern_wei","northern_zhou"];
const extentIds=["A","B"];
const extentSelect=document.getElementById("extent-select"),extentOutput=document.getElementById("extent-result");
function renderPhase(id,write){
 const value=phaseIds.includes(id)?id:"northern_wei";
 document.querySelectorAll("[data-phase]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.phase===value)));
 document.querySelectorAll("[data-phase-card]").forEach(c=>c.hidden=c.dataset.phaseCard!==value);
 if(write){const u=new URL(location.href);u.searchParams.set("phase",value);history.replaceState(null,"",u.pathname+u.search+u.hash);}
}
function renderExtent(id,write){
 const value=extentIds.includes(id)?id:"A";
 extentSelect.value=value;
 extentOutput.textContent=value==="A"
 ?"方案A：东西约340m、南北约310m。南北边界、所选时相和共同锚点均未核对。"
 :"方案B：东西约320m、南北约380m。较方案A东西少20m、南北多70m；真实边界的对应关系尚未验证。";
 if(write){const u=new URL(location.href);u.searchParams.set("extent",value);history.replaceState(null,"",u.pathname+u.search+u.hash);}
}
const params=new URLSearchParams(location.search);
renderPhase(params.get("phase"),false);renderExtent(params.get("extent"),false);
document.querySelectorAll("[data-phase]").forEach(b=>b.addEventListener("click",()=>renderPhase(b.dataset.phase,true)));
extentSelect.addEventListener("change",()=>renderExtent(extentSelect.value,true));
window.addEventListener("popstate",()=>{const p=new URLSearchParams(location.search);renderPhase(p.get("phase"),false);renderExtent(p.get("extent"),false);});
document.documentElement.dataset.taijiReady="true";
})();