/* R11 evidence remains distinct from the layout of its reading groups. */
(() => {
  'use strict';
  const $=s=>document.querySelector(s);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const views={
    map:{path:'dual/maps/L10.svg',title:'洛南馆里与市场文献图',note:'四馆、四里保持无序分组。两市和寺院为旁注；图框位置、宽度和排列不表示街址或占地。'},
    institutions:{path:'dual/maps/LN7-institutions.svg',title:'四馆四里安置关系',note:'这是制度对应表。行次、列对齐与箭头不表示实际街景、距离或所有人的共同迁居路径。'},
    markets:{path:'dual/maps/LN7-markets.svg',title:'市场、永桥与方向关系',note:'分别核对归正里属、洛水南、永桥通行及圜丘方向；不画市场边界或古河道。'},
    layers:{path:'dual/maps/LN7-layers.svg',title:'人物迁居、寺院与动物时层',note:'到来、居馆、筑宅、舍宅与建坊分别计时。未定年和晚于河阴的叙事不自动进入盛时景观。'}
  };
  let data,tab='map',selected='LG01',zoom=1;
  function detail(e){
    const links=e.sources.map(id=>{const s=data.sources.find(x=>x.id===id);return s?`<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.id)} 电子文本 ↗</a>`:'';}).join('');
    return `<span class="record-id">${esc(e.id)} · R11</span><h2>${esc(e.title)}</h2><blockquote>${esc(e.quote)}</blockquote>
      <p class="source-info">引文采用：${esc(e.quote_source)} · ${esc(e.quote_locator)}</p>
      <p class="source-info">文本层：${esc(e.textual_layer)}</p>
      <div class="section-label">采用读法</div><p>${esc(e.reading)}</p>
      <div class="section-label">本批表达</div><p>${esc(e.drawing)}</p>
      <div class="limits"><div class="section-label">仍未确定</div><p>${esc(e.limit)}</p><p>古代地理坐标：未定位</p></div>
      ${(e.variants||[]).length?`<details class="record-variants"><summary>异文与校读</summary>${e.variants.map(v=>`<p>${esc(v.source)}：${esc(v.reading)}</p>`).join('')}</details>`:''}
      ${e.temporal_note?`<p class="source-info">时层：${esc(e.temporal_note)}</p>`:''}<div class="source-links">${links}</div>`;
  }
  function syncHash(){const qs=new URLSearchParams({id:selected});if(tab==='map'&&$('#archive').checked)qs.set('archive','1');const h='#'+tab+'?'+qs;if(location.hash!==h)history.replaceState(null,'',h);}
  function choose(id,sync=true){const e=data.evidence.find(x=>x.id===id)||data.evidence[0];selected=e.id;$('#evidence-picker').value=e.id;$('#detail').innerHTML=detail(e);if(sync)syncHash();}
  function scale(value){zoom=Math.min(4,Math.max(1,value));$('#map').style.width=(zoom*100)+'%';if(zoom===1)$('#viewer').scrollTo(0,0);}
  function show(t,sync=true){
    tab=Object.prototype.hasOwnProperty.call(views,t)||t==='evidence'?t:'map';
    document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.tab===tab)));
    $('#reading-grid').hidden=tab==='evidence';$('#all-evidence').hidden=tab!=='evidence';$('#archive-control').hidden=tab!=='map';
    if(tab!=='evidence'){
      const archive=tab==='map'&&$('#archive').checked;$('#map').src='./'+views[tab].path.replace('.svg',archive?'-archive.svg':'.svg');
      $('#map').alt=views[tab].title;$('#caption').textContent=archive?'封存v2.4母图同区原样裁切；与B7阅读表达对照。':views[tab].note;scale(1);
    }
    if(sync)syncHash();
  }
  function restore(){const [t='map',q='']=(location.hash.slice(1)||'map').split('?');const qs=new URLSearchParams(q);$('#archive').checked=qs.get('archive')==='1';show(t,false);choose(qs.get('id')||'LG01',false);syncHash();}
  async function main(){
    const response=await fetch('./dual/luonan-b7.json');if(!response.ok)throw Error('HTTP '+response.status);data=await response.json();
    $('#summary-count').textContent=data.evidence.length+' 条证据 · 洛南 L10';
    $('#evidence-picker').innerHTML=data.evidence.map(e=>`<option value="${esc(e.id)}">${esc(e.id+' '+e.title)}</option>`).join('');
    $('#all-evidence').innerHTML=data.evidence.map(e=>`<article class="evidence-card" id="record-${esc(e.id)}">${detail(e)}<p><a href="#map?id=${esc(e.id)}">在洛南图旁查看 ↗</a></p></article>`).join('');
    restore();document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>show(b.dataset.tab)));
    $('#evidence-picker').addEventListener('change',()=>choose($('#evidence-picker').value));$('#archive').addEventListener('change',()=>show(tab));
    $('#zoom-in').onclick=()=>scale(zoom*1.4);$('#zoom-out').onclick=()=>scale(zoom/1.4);$('#zoom-reset').onclick=()=>scale(1);
    window.addEventListener('hashchange',restore);$('#map').addEventListener('error',()=>{document.documentElement.dataset.luonanB7Ready='error';$('#caption').textContent='图件加载失败，请重新载入页面。';});
    document.documentElement.dataset.luonanB7Ready='true';
    try{const r=await fetch('./build-info.json');if(!r.ok)throw Error('HTTP '+r.status);const info=await r.json();if(info.luonan_b7?.source_commit!==data.source_commit)throw Error('记录版本不一致');$('#release-status').textContent='B7研究记录与本页构建一致 · '+info.luonan_b7.records+' 条证据 · B1—B6继续保留。';}
    catch(e){$('#release-status').textContent='研究图已载入；构建版本暂未核对：'+e.message;}
  }
  main().catch(e=>{$('#detail').innerHTML='<p class="error">研究记录载入失败：'+esc(e.message)+'</p>';document.documentElement.dataset.luonanB7Ready='error';});
})();
