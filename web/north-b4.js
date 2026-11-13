/* Evidence-linked literary views. No modern or ancient coordinate conversion. */
(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const views = {
    literary: {path:'dual/maps/L06.svg', title:'北门与金墉文献平面', note:'同一张当前文献母图裁切；两处放大插图各有文献坐标范围。图形没有实测地理比例。'},
    gates: {path:'dual/maps/N-gates.svg', title:'两门、两条御道与两场关系', note:'左右保留门位关系，竖向排布用于阅读；寺前不自动解释为南。图上间距和连接线不是道路测量。'},
    membership: {path:'dual/maps/N-membership.svg', title:'金墉通行与里内成员', note:'“城前”保留为非定向关系；名物和里内成员用开放目录表达，不据排列顺序补街址。'}
  };
  let data, tab='literary', selected='NG01', zoom=1;
  function sourceLinks(e) {
    return (e.sources || []).map(id => {
      const s = data.sources.find(x => x.id === id);
      return s ? `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.id)} 电子文本 ↗</a>` : '';
    }).join('');
  }
  function detail(e) {
    return `<span class="record-id">${esc(e.id)}</span><h2>${esc(e.title)}</h2><blockquote>${esc(e.quote)}</blockquote>
      <p class="source-info">引文采用：${esc(e.quote_source || e.sources?.[0])} · ${esc(e.quote_locator || '')}</p>
      <div class="section-label">采用读法</div><p>${esc(e.reading)}</p>
      <div class="section-label">这次如何表达</div><p>${esc(e.drawing || e.reading)}</p>
      <div class="limits"><div class="section-label">仍未确定</div><p>${esc(e.limit)}</p><p>古代地理坐标：未定位</p></div>
      ${(e.variants || []).length ? `<details><summary>异文与校读</summary>${e.variants.map(v=>`<p>${esc(v.source)}：${esc(v.reading)}</p>`).join('')}</details>` : ''}
      ${e.temporal_note ? `<p class="source-info">时层：${esc(e.temporal_note)}</p>` : ''}<div class="source-links">${sourceLinks(e)}</div>`;
  }
  function syncHash() {
    const qs = new URLSearchParams({id:selected});
    if (tab==='literary' && $('#archive').checked) qs.set('archive','1');
    const hash = '#'+tab+'?'+qs;
    if (location.hash !== hash) history.replaceState(null,'',hash);
  }
  function choose(id, sync=true) {
    const e = data.evidence.find(e => e.id===id) || data.evidence[0];
    selected=e.id; $('#evidence-picker').value=e.id; $('#detail').innerHTML=detail(e);
    if(sync) syncHash();
  }
  function scale(value) {
    zoom=Math.min(4,Math.max(1,value)); $('#map').style.width=(zoom*100)+'%';
    if(zoom===1) $('#viewer').scrollTo(0,0);
  }
  function show(t, sync=true) {
    tab = views[t] || t==='evidence' ? t : 'literary';
    document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.tab===tab)));
    $('#reading-grid').hidden=tab==='evidence'; $('#all-evidence').hidden=tab!=='evidence';
    $('#archive-control').hidden=tab!=='literary';
    if(tab!=='evidence') {
      const old=tab==='literary' && $('#archive').checked;
      const path=old?'dual/maps/L06-archive.svg':views[tab].path;
      $('#map').src='./'+path; $('#map').alt=views[tab].title;
      $('#caption').textContent=old?'封存 v2.4 母图的同区裁切；原文件保留，此视图用于比较本批图符变化。':views[tab].note;
      scale(1);
    }
    if(sync) syncHash();
  }
  function restore() {
    const [t='literary',q='']=(location.hash.slice(1)||'literary').split('?');
    const qs=new URLSearchParams(q); $('#archive').checked=qs.get('archive')==='1';
    show(t,false); choose(qs.get('id')||'NG01',false); syncHash();
  }
  async function main() {
    const r=await fetch('./dual/north-b4.json'); if(!r.ok) throw Error('HTTP '+r.status);
    data=await r.json();
    $('#summary-count').textContent=data.evidence.length+' 条证据 · L06 分区';
    $('#evidence-picker').innerHTML=data.evidence.map(e=>`<option value="${esc(e.id)}">${esc(e.id+' '+e.title)}</option>`).join('');
    $('#all-evidence').innerHTML=data.evidence.map(e=>`<article class="evidence-card" id="record-${esc(e.id)}">${detail(e)}<p><a href="#literary?id=${esc(e.id)}">在文献图旁查看 ↗</a></p></article>`).join('');
    restore();
    document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>show(b.dataset.tab)));
    $('#evidence-picker').addEventListener('change',()=>choose($('#evidence-picker').value));
    $('#archive').addEventListener('change',()=>show('literary'));
    $('#zoom-in').onclick=()=>scale(zoom*1.4); $('#zoom-out').onclick=()=>scale(zoom/1.4); $('#zoom-reset').onclick=()=>scale(1);
    window.addEventListener('hashchange',restore);
    $('#map').addEventListener('error',()=>{$('#caption').textContent='图件加载失败，请重新载入页面。';document.documentElement.dataset.northB4Ready='error';});
    document.documentElement.dataset.northB4Ready='true';
    try {
      const r=await fetch('./build-info.json');if(!r.ok)throw Error('HTTP '+r.status);const info=await r.json();
      if(!info.north_b4 || info.north_b4.source_commit!==data.source_commit)throw Error('记录版本不一致');
      $('#release-status').textContent='B4 研究记录与本页构建一致 · '+info.north_b4.records+' 条证据 · 北门图与既有 B1/B2/B3 并存。';
    }catch(e){$('#release-status').textContent='研究图已载入；构建版本暂未核对：'+e.message;}
  }
  main().catch(e=>{$('#detail').innerHTML='<p class="error">研究记录载入失败：'+esc(e.message)+'</p>';document.documentElement.dataset.northB4Ready='error';});
})();
