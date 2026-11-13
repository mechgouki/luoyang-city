'use strict';
(() => {
  const $ = s => document.querySelector(s);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let data, sheet, view = 'scan', selected;
  const prefix = './historical-frame/';
  const number = n => Math.round(n).toLocaleString('en-US');
  const role = p => p.role === 'fit' ? '拟合点' : '同图留出点';

  function state() {
    const params = new URLSearchParams({sheet:sheet.id,view,point:selected.id});
    if (location.hash !== '#' + params.toString()) history.replaceState(null,'','#'+params);
  }
  function selectPoint(id, updateHash = true) {
    selected = sheet.calibration.observations.find(p => p.id === id) || sheet.calibration.observations[0];
    $('#point-picker').value = selected.id;
    $('#crop-image').src = prefix + selected.crop_image;
    $('#crop-image').alt = `${sheet.id} ${selected.id} 蓝网交点的未加标记原图裁片`;
    $('#point-detail').innerHTML = `<p><b>${esc(selected.id)} · ${role(selected)}</b></p>
      <p class="note">原图像素：x ${selected.pixel_xy[0]} / y ${selected.pixel_xy[1]}<br>
      印刷 E ${number(selected.printed_grid_east_m)}<br>印刷 N ${number(selected.printed_grid_north_m)} 网格米</p>
      <p>图内残差约 <b>${number(selected.residual_norm_printed_grid_m)} 网格米</b><br>
      对应 <b>${selected.residual_norm_scan_px.toFixed(1)} 扫描像素</b></p>
      <p class="note">${selected.role==='check'?'此点未参加模型拟合。它仍来自同一张扫描图，不是地面检查点。':'此点参与模型拟合。较小拟合残差不等于地面精度较高。'}</p>`;
    document.querySelectorAll('#point-table tr').forEach(row => row.classList.toggle('selected',row.dataset.point===selected.id));
    document.querySelectorAll('#points-overlay circle').forEach(c => {c.setAttribute('r',c.dataset.point===selected.id?'32':'22');c.setAttribute('stroke-width',c.dataset.point===selected.id?'10':'4');});
    if(updateHash) state();
  }
  function render() {
    document.querySelectorAll('[data-sheet]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.sheet===sheet.id?'true':'false'));
    document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.view===view?'true':'false'));
    $('#main-image').src=prefix+(view==='scan'?sheet.overview_image:sheet.rectified_image);
    $('#main-image').alt=sheet.title+(view==='scan'?' 原始扫描图与26点中本幅的13点':' 印刷网格整饰图，无地理基准标签');
    const [width,height]=sheet.source_size_px;
    $('#points-overlay').setAttribute('viewBox',`0 0 ${width} ${height}`);
    $('#points-overlay').hidden=view!=='scan';
    $('#points-overlay').style.display=view==='scan'?'block':'none';
    $('#points-overlay').innerHTML=sheet.points.map(p=>`<g><circle data-point="${p.id}" role="button" tabindex="0" aria-label="${p.id} ${role(p)}" cx="${p.pixel_xy[0]}" cy="${p.pixel_xy[1]}" r="22" fill="${p.role==='fit'?'#237a79':'#b4543f'}"/><text x="${p.pixel_xy[0]+38}" y="${p.pixel_xy[1]-27}">${p.id.split('-')[1]}</text></g>`).join('');
    $('#points-overlay').querySelectorAll('circle').forEach(c=>{c.addEventListener('click',()=>selectPoint(c.dataset.point));c.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectPoint(c.dataset.point);}});});
    $('#point-picker').innerHTML=sheet.points.map(p=>`<option value="${p.id}">${p.id} · ${role(p)}</option>`).join('');
    const fit=sheet.calibration.fit, check=sheet.calibration.internal_holdout_check;
    $('#metrics').innerHTML=`<article><span>用于拟合 / 内部留出</span><strong>${fit.count} / ${check.count} 点</strong><span>互不重叠的两组观测</span></article><article><span>留出检查 RMS</span><strong>${check.rms_vector_scan_px.toFixed(1)} 像素</strong><span>同一张扫描图内部</span></article><article><span>换算为图面印刷网格</span><strong>约 ${number(check.rms_vector_printed_grid_m)} 米</strong><span>不表示地面精度</span></article>`;
    $('#point-table').innerHTML=sheet.calibration.observations.map(p=>`<tr data-point="${p.id}"><td><button data-point="${p.id}">${p.id}</button></td><td>${role(p)}</td><td>${p.pixel_xy.join(' / ')}</td><td>${number(p.printed_grid_east_m)} / ${number(p.printed_grid_north_m)}</td><td>${number(p.residual_norm_printed_grid_m)}</td><td>${p.residual_norm_scan_px.toFixed(1)}</td></tr>`).join('');
    $('#point-table').querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>selectPoint(b.dataset.point)));
    const [left,bottom,right,top]=sheet.rectified_printed_grid_extent_m;
    $('#extent').innerHTML=view==='scan'?`<span>${esc(sheet.title)} · 原图 ${width} × ${height} px</span>`:`<span>原图印刷网格 E ${number(left)} → ${number(right)}</span><span>N ${number(top)} ↓ ${number(bottom)}</span>`;
    $('#view-caption').textContent=view==='scan'?'点击图中圆点可查看未加标记的原图裁片。绿色8点拟合，赭色5点留出检查；标签位置只用于阅读。':'只显示拟合点包围的矩形；每像素50个印刷网格米是显示采样。未指定EPSG、未与现代地形叠合，也未宣布两图无缝拼接。';
    $('#source-link').href=sheet.source_url;
    $('#source-meta').innerHTML=`来源：US Army Map Service / UT Austin PCL Map Collection · L500 · 1:250,000<br>原图 SHA-256：<code>${sheet.source_sha256}</code>`;
    $('#label-image').src=prefix+sheet.label_image;
    selectPoint(selected && sheet.points.some(p=>p.id===selected.id)?selected.id:sheet.points[0].id,false);
  }
  function restore() {
    const params=new URLSearchParams(location.hash.slice(1));
    sheet=data.sheets.find(s=>s.id===params.get('sheet'))||data.sheets[0];
    view=params.get('view')==='rectified'?'rectified':'scan';
    selected=sheet.calibration.observations.find(p=>p.id===params.get('point'))||sheet.calibration.observations[0];
    render();state();
  }
  document.querySelectorAll('[data-sheet]').forEach(b=>b.addEventListener('click',()=>{sheet=data.sheets.find(s=>s.id===b.dataset.sheet);selected=sheet.calibration.observations[0];render();state();}));
  document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{view=b.dataset.view;render();state();}));
  $('#point-picker').addEventListener('change',e=>selectPoint(e.target.value));
  $('#crosshair').addEventListener('change',e=>$('#crop-overlay').style.display=e.target.checked?'block':'none');
  window.addEventListener('hashchange',()=>{if(data)restore();});
  fetch(prefix+'metadata.json').then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json();}).then(d=>{data=d;restore();document.documentElement.dataset.frameReady='true';document.documentElement.dataset.historicalFrameReady='true';}).catch(e=>{$('#error').hidden=false;$('#error').textContent='校准数据加载失败：'+e.message;document.documentElement.dataset.frameReady='error';document.documentElement.dataset.historicalFrameReady='error';});
})();
