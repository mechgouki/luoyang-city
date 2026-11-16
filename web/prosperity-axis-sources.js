(()=>{"use strict";
const select=document.getElementById("scenario"),output=document.getElementById("scenario-output");
const choices={
"nara2011":"奈文研2011：三号门至太极殿约200米；累计约375米。与另报总距约460米相比相差约-85米。该差额不是测量误差区间。",
"qian2012":"钱国祥研究：三号门至太极殿约300米；累计约475米。与另报总距约460米相比相差约+15米。该差额不是测量误差区间。"
};
function update(caseID,write){
const key=Object.prototype.hasOwnProperty.call(choices,caseID)?caseID:"nara2011";
select.value=key;output.textContent=choices[key];
document.documentElement.dataset.auditReady="true";
if(write){const u=new URL(location.href);u.searchParams.set("scenario",key);history.replaceState(null,"",u.pathname+u.search+u.hash);}
}
select.addEventListener("change",()=>update(select.value,true));
window.addEventListener("popstate",()=>update(new URLSearchParams(location.search).get("scenario"),false));
update(new URLSearchParams(location.search).get("scenario"),false);
})();