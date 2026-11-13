/* Extend evidence access; the existing map still has exactly 179 targets. */
const beforeLuonanEntityB7=renderEntity;let luonanDataB7=null;
renderEntity=function(e){
  const base=beforeLuonanEntityB7(e);if(!luonanDataB7)return base;
  const records=luonanDataB7.evidence.filter(x=>x.entities.includes(e.id));if(!records.length)return base;
  return `<section class="luonan-coverage" style="padding:15px;border-left:3px solid #326754;background:#edf2e7;margin-bottom:18px"><h3>洛南馆里与市场 · B7</h3><p>里属、制度、通行与年代分别核对；旁注不增加地点。</p><p>${records.map(x=>escapeHTML(x.id)).join(' / ')}</p><a href="./dual-luonan.html#map?id=${encodeURIComponent(records[0].id)}">查看洛南图件与依据 ↗</a></section>`+base;
};
(async()=>{try{
  const r=await atlasFetch('./dual/luonan-b7.json');if(!r.ok)throw Error('洛南资料 HTTP '+r.status);luonanDataB7=await r.json();
  for(let i=0;i<600&&document.documentElement.dataset.southeastMainReady!=='true';i++)await new Promise(r=>setTimeout(r,50));
  if(document.documentElement.dataset.southeastMainReady!=='true')throw Error('前序地图未就绪');
  if(selectedEntity)selectEntity(selectedEntity,false,false);document.documentElement.dataset.luonanMainReady='true';
}catch(e){console.error(e);document.documentElement.dataset.luonanMainReady='error';}})();
