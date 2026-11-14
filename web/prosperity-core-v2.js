/* Core building sizes stay distinct from their source positions and working orientations. */
(() => {
  'use strict';
  const $=selector=>document.querySelector(selector);
  const all=selector=>[...document.querySelectorAll(selector)];
  const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const validBox=value=>Array.isArray(value)&&value.length===4&&value.every(Number.isFinite)&&value[2]>0&&value[3]>0;
  const paragraphs=value=>(Array.isArray(value)?value:[value]).filter(Boolean).map(text=>'<p>'+esc(text)+'</p>').join('');
  let data,items=new Map(),focuses=new Map(),state={mode:'plan',item:'',focus:'all'};
  let svg=null,renderedMode='',box=null,baseBox=null,targets=[],renderSerial=0;
  const maps=new Map(),cameras=new Map();

  function safeUrl(value,base=location.href){
    if(!value)return null;
    try{const url=new URL(value,base);return ['https:','http:'].includes(url.protocol)?url.href:null;}catch{return null;}
  }
  function link(value,label,external=false){
    const url=safeUrl(value);
    return url?'<a href="'+esc(url)+'"'+(external?' target="_blank" rel="noopener"':'')+'>'+esc(label)+'</a>':esc(label);
  }
  function modes(){return ['plan','oblique'].filter(mode=>data.maps?.[mode]?.url);}
  function normalize(candidate){
    return {mode:modes().includes(candidate.mode)?candidate.mode:modes()[0],item:items.has(candidate.item)?candidate.item:data.items[0].id,focus:focuses.has(candidate.focus)?candidate.focus:(focuses.has('all')?'all':data.focuses[0].id)};
  }
  function readHash(){
    const params=new URLSearchParams(location.hash.slice(1));
    state=normalize({mode:params.get('mode'),item:params.get('item'),focus:params.get('focus')});
  }
  function writeHash(replace=false){
    const hash='#'+new URLSearchParams(state).toString();
    if(location.hash!==hash)history[replace?'replaceState':'pushState'](null,'',hash);
  }
  function cameraKey(){return state.mode+':'+state.focus;}
  function focusBox(){const extent=focuses.get(state.focus)?.boxes?.[state.mode];return validBox(extent)?extent:baseBox;}
  function setBox(next){
    if(!svg||!validBox(next))return;
    box=[...next];svg.setAttribute('viewBox',box.join(' '));cameras.set(cameraKey(),[...box]);
  }
  function selectedBox(){const extent=items.get(state.item)?.boxes?.[state.mode];return validBox(extent)?extent:null;}
  function fitSelected(){
    let extent=selectedBox();if(!extent)return;
    // Include the selected drawing's labels when framing it, without changing its geometry.
    const node=targets.find(target=>target.getAttribute('data-core-id')===state.item);
    if(node){
      try{
        const bounds=node.getBBox(),matrix=svg.getScreenCTM().inverse().multiply(node.getScreenCTM());
        const points=[[bounds.x,bounds.y],[bounds.x+bounds.width,bounds.y],[bounds.x,bounds.y+bounds.height],[bounds.x+bounds.width,bounds.y+bounds.height]].map(([x,y])=>new DOMPoint(x,y).matrixTransform(matrix));
        const left=Math.min(extent[0],...points.map(p=>p.x)),top=Math.min(extent[1],...points.map(p=>p.y));
        extent=[left,top,Math.max(extent[0]+extent[2],...points.map(p=>p.x))-left,Math.max(extent[1]+extent[3],...points.map(p=>p.y))-top];
      }catch{ /* The supplied focus box remains valid when rendered labels have no extent. */ }
    }
    const padding=.2,w=extent[2]*(1+padding*2),h=extent[3]*(1+padding*2);
    setBox([extent[0]-extent[2]*padding,extent[1]-extent[3]*padding,w,h]);
  }
  function zoom(factor,anchor){
    if(!box||!baseBox)return;
    const width=Math.max(baseBox[2]*.02,Math.min(baseBox[2]*4,box[2]*factor));
    const ratio=width/box[2],point=anchor||{x:box[0]+box[2]/2,y:box[1]+box[3]/2};
    setBox([point.x-(point.x-box[0])*ratio,point.y-(point.y-box[1])*ratio,width,box[3]*ratio]);
  }
  function pointAt(event,matrix){
    return new DOMPoint(event.clientX,event.clientY).matrixTransform(matrix||svg.getScreenCTM().inverse());
  }
  function targetFor(node){
    let current=node instanceof Element?node:null;
    while(current&&current!==svg){if(items.has(current.getAttribute('data-core-id')))return current;current=current.parentElement;}
    return null;
  }
  function bindTargets(){
    targets=[...svg.querySelectorAll('g[data-core-id]')].filter(node=>items.has(node.getAttribute('data-core-id')));
    targets.forEach(node=>{node.setAttribute('role','button');node.setAttribute('tabindex','0');node.setAttribute('aria-label',items.get(node.getAttribute('data-core-id')).name);});
  }
  function updateSelection(){
    targets.forEach(node=>{const selected=node.getAttribute('data-core-id')===state.item;node.classList.toggle('core-selected',selected);node.setAttribute('aria-pressed',String(selected));});
    $('#focus-item').disabled=!selectedBox();
  }
  function renderItem(){
    const item=items.get(state.item);
    let html='<h2>'+esc(item.name)+'</h2><p class="measure-label">尺寸依据</p><p class="measure-value">'+esc(item.dimensions_label)+'</p>';
    html+='<dl class="item-facts"><dt>位置依据</dt><dd>'+paragraphs(item.position_note)+'</dd><dt>工作朝向</dt><dd>'+paragraphs(item.orientation_note)+'</dd></dl>';
    html+='<div class="height-note">'+paragraphs(item.height_note||'原高尚未核定，图中不补建筑立面。')+'</div>';
    if(item.detail_figure?.url&&safeUrl(item.detail_figure.url))html+='<figure class="detail-figure"><a href="'+esc(safeUrl(item.detail_figure.url))+'" target="_blank" rel="noopener" aria-label="'+esc('打开'+item.name+'的局部图')+'"><img src="'+esc(safeUrl(item.detail_figure.url))+'" alt="'+esc(item.detail_figure.caption||item.name+'的局部图')+'"></a>'+(item.detail_figure.caption?'<figcaption>'+esc(item.detail_figure.caption)+'</figcaption>':'')+'</figure>';
    html+='<div class="item-links">'+(item.source_url?link(item.source_url,item.source_label||'阅读原件出处 ↗',true):'')+(item.related_url?link(item.related_url,'查看城市档案 ↗'):'')+'</div>';
    $('#item-detail').innerHTML=html;
    all('[data-item]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.item===state.item)));
  }
  function mapFor(mode){
    if(maps.has(mode))return maps.get(mode);
    const pending=(async()=>{
      const descriptor=data.maps[mode],url=safeUrl(descriptor.url);
      if(!url)throw Error('图件地址无效');
      const response=await fetch(url);if(!response.ok)throw Error('图件读取失败');
      const parsed=new DOMParser().parseFromString(await response.text(),'image/svg+xml');
      if(parsed.querySelector('parsererror')||parsed.documentElement.localName!=='svg')throw Error('图件格式无法识别');
      const node=parsed.documentElement;
      node.querySelectorAll('script,foreignObject').forEach(element=>element.remove());
      [node,...node.querySelectorAll('*')].forEach(element=>{
        [...element.attributes].filter(attribute=>/^on/i.test(attribute.name)).forEach(attribute=>element.removeAttribute(attribute.name));
        if(element.localName==='image')for(const name of ['href','xlink:href']){const value=element.getAttribute(name);if(value&&!value.startsWith('#')&&!value.startsWith('data:image/')){const href=safeUrl(value,url);if(href)element.setAttribute(name,href);else element.removeAttribute(name);}}
      });
      node.removeAttribute('width');node.removeAttribute('height');node.setAttribute('aria-label',descriptor.title||'核心区地图');
      const extent=descriptor.viewBox||(node.getAttribute('viewBox')||'').split(/[ ,]+/).map(Number);
      if(!validBox(extent))throw Error('图件画幅无效');
      return {node,extent};
    })();
    maps.set(mode,pending);return pending;
  }
  async function render(resetView=false){
    const request=++renderSerial,mode=state.mode,descriptor=data.maps[mode];
    document.documentElement.dataset.coreReady='loading';$('#map-viewport').setAttribute('aria-busy','true');
    all('[data-mode]').forEach(button=>{button.hidden=!modes().includes(button.dataset.mode);button.setAttribute('aria-pressed',String(button.dataset.mode===mode));});
    all('[data-focus]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.focus===state.focus)));
    renderItem();$('#map-title').textContent=descriptor.title||'核心区地图';
    if(renderedMode!==mode){
      const loaded=await mapFor(mode);if(request!==renderSerial)return;
      svg=document.importNode(loaded.node,true);baseBox=[...loaded.extent];$('#map-viewport').replaceChildren(svg);renderedMode=mode;bindTargets();
      setBox(resetView?focusBox():(cameras.get(cameraKey())||focusBox()));
    }else if(resetView)setBox(focusBox());
    updateSelection();$('#open-map').href=safeUrl(descriptor.url);
    $('#map-viewport').dataset.mode=mode;$('#map-viewport').dataset.map=descriptor.url;$('#map-viewport').dataset.focus=state.focus;
    $('#map-viewport').setAttribute('aria-busy','false');document.documentElement.dataset.coreReady='true';
  }
  async function change(patch,options={}){
    const previousFocus=state.focus;state=normalize({...state,...patch});writeHash(!!options.replace);
    await render(options.resetView||previousFocus!==state.focus);
  }
  function renderSupporting(){
    $('#figure-list').innerHTML=(data.figures||[]).map(figure=>'<figure class="figure-card" data-figure="'+esc(figure.id)+'"><a href="'+esc(safeUrl(figure.url)||'#')+'" target="_blank" rel="noopener" aria-label="'+esc('打开'+figure.title)+'"><img src="'+esc(safeUrl(figure.url)||'')+'" alt="'+esc(figure.title)+'"></a><figcaption><h3>'+esc(figure.title)+'</h3>'+paragraphs(figure.caption)+'<span class="figure-open">'+link(figure.url,'打开完整图件 ↗',true)+'</span></figcaption></figure>').join('');
    $('#figures').hidden=!(data.figures||[]).length;$('#figures-link').hidden=!(data.figures||[]).length;
    $('#source-list').innerHTML=(data.sources||[]).map(source=>'<article class="source-card"><h3>'+esc(source.title)+'</h3>'+paragraphs(source.note)+link(source.url,'打开原件来源 ↗',true)+'</article>').join('');
    $('#download-links').innerHTML=(data.downloads||[]).map(download=>link(download.url,download.label||'下载图件')).join('');
  }
  function scrollTo(id){$(id).scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});}
  function fail(error){
    document.documentElement.dataset.coreReady='error';$('#map-viewport').setAttribute('aria-busy','false');
    $('#map-viewport').innerHTML='<p class="error-message">暂时无法载入核心区图件，请刷新后重试。</p>';console.error(error);
  }
  async function init(){
    const response=await fetch('./prosperity-core/data.json');if(!response.ok)throw Error('核心区数据读取失败');data=await response.json();
    if(!data.items?.length||!data.focuses?.length||!data.maps?.plan?.url)throw Error('核心区数据缺少必要内容');
    items=new Map(data.items.map(item=>[item.id,item]));focuses=new Map(data.focuses.map(focus=>[focus.id,focus]));
    if(data.title){document.title=data.title;$('#page-title').textContent=data.title;}if(data.period)$('#period-label').textContent=data.period;if(data.intro)$('#intro-copy').textContent=data.intro;
    $('#focus-switch').innerHTML=data.focuses.map(focus=>'<button type="button" data-focus="'+esc(focus.id)+'" aria-pressed="false">'+esc(focus.label)+'</button>').join('');
    $('#item-switch').innerHTML=data.items.map(item=>'<button type="button" data-item="'+esc(item.id)+'" aria-pressed="false">'+esc(item.name)+'</button>').join('');
    all('[data-mode]').forEach(button=>button.addEventListener('click',()=>change({mode:button.dataset.mode}).catch(fail)));
    all('[data-focus]').forEach(button=>button.addEventListener('click',()=>change({focus:button.dataset.focus},{resetView:true}).catch(fail)));
    all('[data-item]').forEach(button=>button.addEventListener('click',()=>change({item:button.dataset.item}).catch(fail)));
    $('#zoom-in').addEventListener('click',()=>zoom(.8));$('#zoom-out').addEventListener('click',()=>zoom(1.25));
    $('#reset-map').addEventListener('click',()=>setBox(focusBox()));$('#focus-item').addEventListener('click',fitSelected);
    $('#sources-link').addEventListener('click',event=>{event.preventDefault();$('#source-catalog').open=true;scrollTo('#sources');});
    $('#figures-link').addEventListener('click',event=>{event.preventDefault();scrollTo('#figures');});
    window.addEventListener('hashchange',()=>{readHash();writeHash(true);render(true).catch(fail);});
    const viewport=$('#map-viewport');let drag=null;
    viewport.addEventListener('pointerdown',event=>{
      if(event.button!==0||!svg||!box)return;
      const matrix=svg.getScreenCTM().inverse();drag={id:event.pointerId,x:event.clientX,y:event.clientY,point:pointAt(event,matrix),matrix,box:[...box],target:event.target,moved:false};
    });
    viewport.addEventListener('pointermove',event=>{
      if(!drag||drag.id!==event.pointerId)return;
      if(Math.hypot(event.clientX-drag.x,event.clientY-drag.y)>6){drag.moved=true;viewport.setPointerCapture(event.pointerId);viewport.classList.add('dragging');}
      if(drag.moved){const point=pointAt(event,drag.matrix);setBox([drag.box[0]-(point.x-drag.point.x),drag.box[1]-(point.y-drag.point.y),drag.box[2],drag.box[3]]);}
    });
    viewport.addEventListener('pointerup',event=>{
      if(!drag||drag.id!==event.pointerId)return;
      const completed=drag;drag=null;viewport.classList.remove('dragging');if(viewport.hasPointerCapture(event.pointerId))viewport.releasePointerCapture(event.pointerId);
      if(!completed.moved){const node=targetFor(completed.target);if(node)change({item:node.getAttribute('data-core-id')}).catch(fail);}
    });
    viewport.addEventListener('pointercancel',()=>{drag=null;viewport.classList.remove('dragging');});
    viewport.addEventListener('wheel',event=>{if(!svg)return;event.preventDefault();zoom(event.deltaY>0?1.12:.89,pointAt(event));},{passive:false});
    viewport.addEventListener('keydown',event=>{
      if(event.key==='Enter'||event.key===' '){const node=targetFor(event.target);if(node){event.preventDefault();change({item:node.getAttribute('data-core-id')}).catch(fail);}}
      else if(event.key==='+'||event.key==='='){event.preventDefault();zoom(.8);}
      else if(event.key==='-'){event.preventDefault();zoom(1.25);}
      else if(event.key==='Home'){event.preventDefault();setBox(focusBox());}
    });
    readHash();writeHash(true);renderSupporting();await render(true);
    try{
      const metadata=await fetch('./build-info.json',{cache:'no-store'});if(!metadata.ok)throw Error('发布信息读取失败');
      const info=await metadata.json(),consistent=info.source_commit===data.source_commit&&info.prosperity_core?.version===data.version;
      $('#version-status').textContent=consistent?'本页与正式发布一致':'页面与发布信息暂不一致，请刷新后查看。';$('#version-status').dataset.verified=String(consistent);
    }catch{$('#version-status').textContent='发布信息暂时无法核对。';$('#version-status').dataset.verified='false';}
  }
  init().catch(fail);
})();
