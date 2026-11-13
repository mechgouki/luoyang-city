/* Extend current main-map evidence without changing the 179 hit targets. */
const beforeNorthEntity=renderEntity;let northData=null;
renderEntity=function(e){
  const base=beforeNorthEntity(e);if(!northData)return base;
  const entries=northData.evidence.filter(x=>x.entities.includes(e.id));if(!entries.length)return base;
  return `<section class="north-coverage" style="padding:15px;border-left:3px solid #976e3a;background:#f6f1e5;margin-bottom:18px"><h3>北门与金墉 · B4</h3><p>本批原文、校读、关系与未定位置已逐项复核。</p><p>${entries.map(x=>escapeHTML(x.id)).join(' / ')}</p><a href="./dual-north.html#literary?id=${encodeURIComponent(entries[0].id)}">查看本区图件与依据 ↗</a></section>`+base;
};
(async()=>{try{
  const r=await atlasFetch('./dual/north-b4.json');if(!r.ok)throw Error('北门资料 HTTP '+r.status);northData=await r.json();
  for(let i=0;i<600&&document.documentElement.dataset.dualMainReady!=='true';i++)await new Promise(r=>setTimeout(r,50));
  if(selectedEntity)selectEntity(selectedEntity,false,false);
  document.documentElement.dataset.northMainReady='true';
}catch(e){console.error(e);document.documentElement.dataset.northMainReady='error';}})();
