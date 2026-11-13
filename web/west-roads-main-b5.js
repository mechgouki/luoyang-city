/* Extend current main-map evidence without changing the 179 hit targets. */
const beforeWestRoadsEntity=renderEntity;let westRoadsData=null;
renderEntity=function(e){
  const base=beforeWestRoadsEntity(e);if(!westRoadsData)return base;
  const entries=westRoadsData.evidence.filter(x=>x.entities.includes(e.id));if(!entries.length)return base;
  return `<section class="west-roads-coverage" style="padding:15px;border-left:3px solid #976e3a;background:#f6f1e5;margin-bottom:18px"><h3>城西三门道 · B5</h3><p>本批寺序、宅改寺时层与构件条件已逐项复核。</p><p>${entries.map(x=>escapeHTML(x.id)).join(' / ')}</p><a href="./dual-west-roads.html#literary?id=${encodeURIComponent(entries[0].id)}">查看本区图件与依据 ↗</a></section>`+base;
};
(async()=>{try{
  const r=await atlasFetch('./dual/west-roads-b5.json');if(!r.ok)throw Error('城西门道资料 HTTP '+r.status);westRoadsData=await r.json();
  for(let i=0;i<600&&document.documentElement.dataset.northMainReady!=='true';i++)await new Promise(r=>setTimeout(r,50));
  if(selectedEntity)selectEntity(selectedEntity,false,false);
  document.documentElement.dataset.westRoadsMainReady='true';
}catch(e){console.error(e);document.documentElement.dataset.westRoadsMainReady='error';}})();
