/* Current literary map changes are published, not merely hidden in a side page. */
const beforeDualEntity=renderEntity;let dualData=null;
renderEntity=function(e){const base=beforeDualEntity(e);if(!dualData)return base;const entries=[...dualData.b1.decisions.filter(d=>d.entity===e.id),...dualData.b2.evidence.filter(d=>d.entities.includes(e.id))];if(!entries.length)return base;const region=entries.some(d=>d.id.startsWith('G'))?'L04':dualData.regions.find(r=>(r.changes||[]).some(id=>entries.some(e=>e.id===id)))?.id||'L01';return `<section class="dual-coverage" style="padding:15px;border-left:3px solid #326e5c;background:#edf3e8;margin-bottom:18px"><h3>双图 B1+B2 · 原图已深化</h3><p>构件与类型图符已修改；示意锚点不移动，未增加古址经纬度。</p><p>${entries.map(x=>escapeHTML(x.id)).join(' / ')}</p><a href="./dual-b2.html#literary?region=${region}&entity=${encodeURIComponent(e.id)}">查看改图与原文 ↗</a> <a href="./dual-b2.html#terrain?region=${region}&entity=${encodeURIComponent(e.id)}">独立地形插图 ↗</a></section>`+base};
function labelCurrentRelease(){
 for(const root of document.querySelectorAll('.global-footer,.v28-help')){
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);let n;
  while((n=walker.nextNode()))n.textContent=n.textContent.replace('当前整合版 v2.9','当前工作版 B1+B2').replace('当前主入口已为v2.9','当前主入口已为双图B1+B2');
 }
}
(async()=>{try{const r=await atlasFetch('./dual/data.json');if(!r.ok)throw Error('双图资料HTTP '+r.status);dualData=await r.json();for(let i=0;i<600&&document.documentElement.dataset.portal28Ready!=='true';i++)await new Promise(r=>setTimeout(r,50));if(selectedEntity)selectEntity(selectedEntity,false,false);labelCurrentRelease();document.documentElement.dataset.dualMainReady='true'}catch(e){console.error(e);document.documentElement.dataset.dualMainReady='error'}})();
