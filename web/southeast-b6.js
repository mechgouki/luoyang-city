/* Preserve the distinction between drawing anchors and literary relationships. */
(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const views={
    inner:{path:'dual/maps/L08.svg',region:'R08',title:'城东南门内文献图',note:'寺、署、池与园分别读；愿会、宜寿、光明及胡统继续保留关系组或旁注。锚点没有实测比例。'},
    outer:{path:'dual/maps/L09.svg',region:'R09',title:'城东南门外文献图',note:'同里与冢旁不自动提供相对方位；现图锚点继续保留，采用校读和未定关系在证据栏单列。'},
    relations:{path:'dual/maps/SE6-relations.svg',title:'门内外关系与回指',note:'每个面板独立阅读。方向、包含、邻近和回指的证据层次不同；图框不代表街坊边界。'},
    layers:{path:'dual/maps/SE6-layers.svg',title:'宅寺塔与文本年代',note:'寺院本体、后出塔、铭文日期与人物仕历分别计时；没有新增古代地理坐标。'}
  };
  let data,tab='inner',selected='EI01',zoom=1;
  const regionTab=e=>e.source_region==='R09'?'outer':'inner';
  const spatial=()=>tab==='inner'||tab==='outer';
  function detail(e){
    const links=(e.sources||[]).map(id=>{const s=data.sources.find(x=>x.id===id);return s?`<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.id)} 电子文本 ↗</a>`:'';}).join('');
    return `<span class="record-id">${esc(e.id)} · ${esc(e.source_region)}</span><h2>${esc(e.title)}</h2><blockquote>${esc(e.quote)}</blockquote>
      <p class="source-info">引文采用：${esc(e.quote_source)} · ${esc(e.quote_locator)}</p>
      <div class="section-label">采用读法</div><p>${esc(e.reading)}</p>
      <div class="section-label">本批表达</div><p>${esc(e.drawing)}</p>
      <div class="limits"><div class="section-label">仍未确定</div><p>${esc(e.limit)}</p><p>古代地理坐标：未定位</p></div>
      ${(e.variants||[]).length?`<details class="record-variants"><summary>异文与校读</summary>${e.variants.map(v=>`<p>${esc(v.source)}：${esc(v.reading)}</p>`).join('')}</details>`:''}
      ${e.temporal_note?`<p class="source-info">时层：${esc(e.temporal_note)}</p>`:''}<div class="source-links">${links}</div>`;
  }
  function syncHash(){
    const qs=new URLSearchParams({id:selected});if(spatial()&&$('#archive').checked)qs.set('archive','1');
    const hash='#'+tab+'?'+qs;if(location.hash!==hash)history.replaceState(null,'',hash);
  }
  function choose(id,sync=true,followMap=true){
    const e=data.evidence.find(x=>x.id===id)||data.evidence[0];selected=e.id;
    $('#evidence-picker').value=e.id;$('#detail').innerHTML=detail(e);
    if(followMap&&spatial()&&regionTab(e)!==tab)show(regionTab(e),false,false);
    if(sync)syncHash();
  }
  function scale(value){zoom=Math.min(4,Math.max(1,value));$('#map').style.width=(zoom*100)+'%';if(zoom===1)$('#viewer').scrollTo(0,0);}
  function show(t,sync=true,adaptSelection=true){
    tab=views[t]||t==='evidence'?t:'inner';
    document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.tab===tab)));
    $('#reading-grid').hidden=tab==='evidence';$('#all-evidence').hidden=tab!=='evidence';$('#archive-control').hidden=!spatial();
    if(tab!=='evidence'){
      const old=spatial()&&$('#archive').checked;const source=views[tab].path.replace('.svg',old?'-archive.svg':'.svg');
      $('#map').src='./'+source;$('#map').alt=views[tab].title;
      $('#caption').textContent=old?'封存v2.4母图同区裁切；用于比较本批类型表达。':views[tab].note;scale(1);
      if(adaptSelection&&spatial()){
        const current=data.evidence.find(e=>e.id===selected);
        if(!current||current.source_region!==views[tab].region)choose(data.evidence.find(e=>e.source_region===views[tab].region).id,false,false);
      }
    }
    if(sync)syncHash();
  }
  function restore(){
    const [t='inner',q='']=(location.hash.slice(1)||'inner').split('?');const qs=new URLSearchParams(q);$('#archive').checked=qs.get('archive')==='1';
    const defaultId=data.evidence.find(e=>e.source_region===(t==='outer'?'R09':'R08')).id;
    show(t,false,false);choose(qs.get('id')||defaultId,false);syncHash();
  }
  async function main(){
    const response=await fetch('./dual/southeast-b6.json');if(!response.ok)throw Error('HTTP '+response.status);data=await response.json();
    $('#summary-count').textContent=data.evidence.length+' 条证据 · L08 / L09';
    $('#evidence-picker').innerHTML=data.evidence.map(e=>`<option value="${esc(e.id)}">${esc(e.id+' '+e.title)}</option>`).join('');
    $('#all-evidence').innerHTML=data.evidence.map(e=>`<article class="evidence-card" id="record-${esc(e.id)}">${detail(e)}<p><a href="#${regionTab(e)}?id=${esc(e.id)}">在所属分区图旁查看 ↗</a></p></article>`).join('');
    restore();document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>show(b.dataset.tab)));
    $('#evidence-picker').addEventListener('change',()=>choose($('#evidence-picker').value));$('#archive').addEventListener('change',()=>show(tab));
    $('#zoom-in').onclick=()=>scale(zoom*1.4);$('#zoom-out').onclick=()=>scale(zoom/1.4);$('#zoom-reset').onclick=()=>scale(1);
    window.addEventListener('hashchange',restore);$('#map').addEventListener('error',()=>{document.documentElement.dataset.southeastB6Ready='error';$('#caption').textContent='图件加载失败，请重新载入页面。';});
    document.documentElement.dataset.southeastB6Ready='true';
    try{
      const r=await fetch('./build-info.json');if(!r.ok)throw Error('HTTP '+r.status);const info=await r.json();
      if(info.southeast_b6?.source_commit!==data.source_commit)throw Error('记录版本不一致');
      $('#release-status').textContent='B6研究记录与本页构建一致 · '+info.southeast_b6.records+' 条证据 · B1—B5继续保留。';
    }catch(e){$('#release-status').textContent='研究图已载入；构建版本暂未核对：'+e.message;}
  }
  main().catch(e=>{$('#detail').innerHTML='<p class="error">研究记录载入失败：'+esc(e.message)+'</p>';document.documentElement.dataset.southeastB6Ready='error';});
})();
