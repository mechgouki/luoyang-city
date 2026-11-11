/* Point-level evidence links are derived from generated SVG circles, not a historical basemap. */
const renderWithoutPointLinks26=render26;
render26=function(params){
 renderWithoutPointLinks26(params);
 const img=document.getElementById('m26-plan-image');
 if(!img||!milestone26)return;
 const plan=milestone26.candidates.find(p=>'./'+p.path===img.getAttribute('src'));
 if(!plan?.display_points)return;
 const c=milestone26.cases.find(x=>x.id===plan.case_id);
 const chosen=params.get('entity');const [vx,vy,vw,vh]=plan.svg_view_box;
 const stage=document.createElement('div');stage.className='m26-plan-stage';
 img.before(stage);stage.append(img);
 for(const p of plan.display_points){
  const b=document.createElement('button');b.type='button';b.className='m26-point-link'+(p.entity_id===chosen?' selected':'');
  b.dataset.modelEntity=p.entity_id;b.style.left=((p.x-vx)/vw*100)+'%';b.style.top=((p.y-vy)/vh*100)+'%';
  b.setAttribute('aria-label','查看'+milestone26.names[p.entity_id]+'的模型依据');b.title=milestone26.names[p.entity_id]+'：查看依据';
  b.onclick=()=>location.hash=m26url(c.id,'plans',{pick:plan.selected_side,entity:p.entity_id});stage.append(b);
 }
 if(!chosen||!plan.display_points.some(p=>p.entity_id===chosen))return;
 const atoms=milestone26.atoms.filter(a=>[a.less,a.more,a.node,a.a,a.b].includes(chosen));
 const query=c.queries.filter(q=>[q.less,q.more,q.node,q.a,q.b].includes(chosen));
 const card=document.createElement('section');card.id='m26-point-evidence';card.className='m26-premise';
 card.innerHTML='<h2>'+escapeHTML(milestone26.names[chosen])+'：这个点为什么可以画在这里？</h2><p>此处是本情形的一种显示解，不是已证古址。点击下面编号可回查原句、校读和依赖条件。</p>'+
 '<p>'+query.map(q=>escapeHTML(q.title)+'：<strong>'+m26State[q.status]+'</strong>').join('；')+'</p>'+
 '<div>'+atoms.map(a=>'<p>'+atomLink26(a.id,c.id)+' '+(c.active_ids.includes(a.id)?'本情形启用':'<strong>本情形未启用</strong>')+' · '+escapeHTML(a.quote)+'</p>').join('')+'</div>'+
 '<a class="r-link" href="#map?entity='+encodeURIComponent(chosen)+'">回到原始地点档案 ↗</a>';
 stage.closest('figure').after(card);
 requestAnimationFrame(()=>card.scrollIntoView({block:'start'}));
};
const pointStyles26=document.createElement('style');pointStyles26.textContent='.m26-plan-stage{position:relative}.m26-point-link{position:absolute;transform:translate(-50%,-50%);width:28px;height:28px;border:2px solid transparent;background:transparent;border-radius:50%;cursor:pointer;padding:0}.m26-point-link:hover,.m26-point-link:focus-visible,.m26-point-link.selected{border-color:#9e6c2e;background:rgba(186,145,62,.12);outline-offset:2px}#m26-point-evidence{scroll-margin-top:20px}@media(max-width:750px){.m26-plan-stage{min-width:620px}}';document.head.append(pointStyles26);
if(milestone26&&registry26&&(location.hash||'').startsWith('#model'))route();
