/* Append B6 evidence while retaining every existing main-map hit target. */
const beforeSoutheastEntityB6=renderEntity;let southeastDataB6=null;
renderEntity=function(e){
  const base=beforeSoutheastEntityB6(e);if(!southeastDataB6)return base;
  const records=southeastDataB6.evidence.filter(x=>x.entities.includes(e.id));if(!records.length)return base;
  const first=records[0],view=first.source_region==='R09'?'outer':'inner';
  return `<section class="southeast-coverage" style="padding:15px;border-left:3px solid #326754;background:#edf2e7;margin-bottom:18px"><h3>城东南门内外 · B6</h3><p>路侧、里属、邻近与年代逐条核对。</p><p>${records.map(x=>escapeHTML(x.id)).join(' / ')}</p><a href="./dual-southeast.html#${view}?id=${encodeURIComponent(first.id)}">查看本区图件与依据 ↗</a></section>`+base;
};
(async()=>{try{
  const r=await atlasFetch('./dual/southeast-b6.json');if(!r.ok)throw Error('城东南资料 HTTP '+r.status);southeastDataB6=await r.json();
  for(let i=0;i<600&&document.documentElement.dataset.westRoadsMainReady!=='true';i++)await new Promise(r=>setTimeout(r,50));
  if(document.documentElement.dataset.westRoadsMainReady!=='true')throw Error('前序地图未就绪');
  if(selectedEntity)selectEntity(selectedEntity,false,false);document.documentElement.dataset.southeastMainReady='true';
}catch(e){console.error(e);document.documentElement.dataset.southeastMainReady='error';}})();
