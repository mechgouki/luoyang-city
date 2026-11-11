"""Audited R07 atoms and explicit scenario premises; no drawing coordinates."""
from itertools import product
from qualitative_space import Model,select,minimal_core

SHORT={
 'Y':'ic_yongning','J':'ic_jingle','P':'ic_changhe_palace','R':'ic_palace_avenue',
 'T':'ic_taiwei','Z':'ic_zhaoxuan','U':'ic_yushi','L':'ic_zuowei','S':'ic_situ',
 'G':'ic_guozixue','O':'ic_zongzheng','M':'ic_taimiao','H':'ic_hujun','I':'ic_yiguan',
 'V':'ic_youwei','B':'ic_jiangzuo','K':'ic_jiuji','A':'ic_taishe','N':'ic_lingyin',
 'W':'ic_yongkang','Q':'ic_gaozhao_house','D':'ic_yijing',
 'HM':'mention_h_inner_miao','HA':'mention_h_inner_she','OM':'mention_h_outer_miao',
 'OA':'mention_h_outer_she','TF':'mention_h_taifu','SZ':'mention_h_sizhou',
 'WM':'mention_w_miao','WA':'mention_w_she','WC':'mention_w_channel',
 'YT':'mention_yongning_tower','YD':'mention_yongning_hall'}
EXTRA_NAMES={'HM':'H城内太庙条','HA':'H城内太社条','OM':'H门外太庙条','OA':'H门外太社条',
 'TF':'H太府寺条','SZ':'H司州条','WM':'W太庙条','WA':'W太社条','WC':'W夹路渠段',
 'YT':'永宁塔（构件）','YD':'永宁佛殿（构件）'}
GROUPS={
 'west_side':'西侧官署序列继承御道西',
 'east_side':'东侧官署序列继承御道东',
 'jingle_east':'采用景乐条校补〈东〉',
 'H_identity':'H城内庙社与本图对象对应为同体',
 'W_context':'W流经庙社仍属入城段，且同体同城同研究时相',
 'outer_identity':'H门外与城内庙社视为同一对象',
 'outer_phase':'H门外与城内记载视为同一时相',
 'outer_boundary':'H门外与城内使用同一城界参照',
 'merge_taifu':'将H太府寺与太尉府视为同一对象'}

def build_atoms(evidence):
    by_e={e['id']:e for e in evidence['evidence']};atoms=[]
    def add(i,e,kind,quote,group='always',families=None,requires=(),**kw):
        card=by_e[e]
        fam=families if families is not None else (['H'] if e in {'E06','E09','E11','E12','E16'} else ['W'] if e in {'E10','E15'} else ['L'])
        d={'id':i,'evidence_id':e,'kind':kind,'quote':quote,'families':fam,'group':group,
           'requires':list(requires),'layer':'explicit_assumption' if group!='always' else 'text_projection' if kind=='order' else 'text_record',
           'source_locator':card['locator'],'source_links':card['sources'],'evidence_panel':card['group'],
           'verification':'电子文本或既有节录；未声称书影逐叶校勘',
           'valid_from':None,'valid_to':None,'phase':'t0','reference':'R07-axes',**kw}
        if kind=='note':d['layer']='non_executable_note'
        atoms.append(d);return i
    def order(i,e,axis,lo,hi,quote,**kw):
        return add(i,e,'order',quote,axis=axis,less=SHORT.get(lo,lo),more=SHORT.get(hi,hi),**kw)
    def alias(i,e,a,b,group,domain='entity',**kw):
        return add(i,e,'alias','工作前提：'+GROUPS[group],group=group,domain=domain,
                   a=SHORT.get(a,a) if domain=='entity' else a,b=SHORT.get(b,b) if domain=='entity' else b,**kw)
    order('F01','E01','y','Y','P','在宮前閶闔門南')
    order('F02','E01','x','Y','R','御道西')
    add('F03','E01','note','南一里；参照宫前阊阖门，非城西同名门。',note_type='quantity_and_reference')
    for i,axis,lo,hi,q in [('F04','x','Y','T','其寺東有太尉府'),('F05','x','W','Y','西對永康里'),
                          ('F06','y','Z','Y','南界昭玄曹'),('F07','y','Y','U','北鄰御史臺')]:
        order(i,'E02',axis,lo,hi,q,projection_limit='仅编码方向；不等于完整邻接或建筑边界。')
    order('F08','E03','x','R','L','御道東有左衛府')
    order('F09','E03','y','S','L','府南有司徒府')
    for i,lo,hi,q in [('F10','G','S','司徒府南有國子學堂'),('F11','O','G','國子南有宗正寺'),
                       ('F12','M','O','寺南有太廟'),('F13','H','M','廟南有護軍府'),('F14','I','H','府南有衣冠里')]:
        order(i,'E04','y',lo,hi,q)
    order('F15','E05','x','V','R','御道西有右衛府')
    for i,lo,hi,q in [('F16','T','V','府南有太尉府'),('F17','B','T','府南有將作曹'),
                       ('F18','K','B','曹南有九級府'),('F19','A','K','府南有太社'),('F20','N','A','社南有凌陰里')]:
        order(i,'E05','y',lo,hi,q)
    for k,i in [('T','GWT'),('B','GWB'),('K','GWK'),('A','GWA'),('N','GWN')]:
        order(i,'E05','x',k,'R','本项目把后续西侧序列承接为御道西；原文未逐项重写。',group='west_side',requires=[f'F{n:02d}' for n in range(15,17+['T','B','K','A','N'].index(k))])
    for k,i in [('S','GES'),('G','GEG'),('O','GEO'),('M','GEM'),('H','GEH'),('I','GEI')]:
        order(i,'E04','x','R',k,'本项目把后续东侧序列承接为御道东；原文未逐项重写。',group='east_side',requires=[f'F{n:02d}' for n in range(8,10+['S','G','O','M','H','I'].index(k))])
    for i,lo,hi,q in [('H01','TF','V','太府寺，右衛府南'),('H02','B','TF','將作曹，太府寺南'),
                      ('H03','A','B','太社，將作曹南'),('H04','SZ','A','司州，太社南'),('H05','N','SZ','凌陰里，司州南')]:
        order(i,'E06','y',lo,hi,q,identity_scope='H同名官署按工作案对应；太府、司州保留独立文本提及ID。')
    add('C07','E07','note','范氏据水经太尉司徒两坊间，判河南志太府为误；属校者论证，不新增方向证据。',note_type='editorial_judgment',families=['L','W'])
    add('C08','E08','note','周记太府异文、九级未详和司州增列。未列出不等于不存在。',note_type='editorial_note')
    order('H06','E09','y','T','P','在閭闔門南')
    order('H07','E09','x','Y','T','永寧寺東')
    for i,k in [('H08','HM'),('H09','HA')]:
        add(i,'E09','membership','对应城内条目，列表末署右城內。',node=SHORT[k],boundary='city_inner',value='inside')
    alias('AHM','E09','HM','M','H_identity',families=['H'],requires=['H08'])
    alias('AHA','E09','HA','A','H_identity',families=['H'],requires=['H09'])
    add('W01','E10','note','門左枝渠東派入城，逕太社前，又東逕太廟南。',note_type='route_sequence',families=['W'])
    for i,k in [('W02','WM'),('W03','WA')]:
        add(i,'E10','membership','从入城与流经段推断设施在城内；未记录出城且同体同时是额外前提。',group='W_context',
            families=['W'],requires=['W01'],node=SHORT[k],boundary='city_inner',value='inside')
    alias('AWM','E10','WM','M','W_context',families=['W'],requires=['W02'])
    alias('AWA','E10','WA','A','W_context',families=['W'],requires=['W03'])
    add('H10','E11','membership','清陽門外有太廟。',node=SHORT['OM'],boundary='city_outer',value='outside',phase='outer_unknown')
    add('H11','E12','membership','西明門外一里有太社。',node=SHORT['OA'],boundary='city_outer',value='outside',phase='outer_unknown')
    add('H12','E12','note','一里不换算为像素；下句御道北属于王宅，不转给太社。',note_type='quantity_and_scope')
    alias('AOM','E11','OM','M','outer_identity',families=['H'],requires=['H10'])
    alias('AOA','E12','OA','A','outer_identity',families=['H'],requires=['H11'])
    alias('AOT','E11','outer_unknown','t0','outer_phase',domain='phase',families=['H'])
    alias('AOR','E11','city_outer','city_inner','outer_boundary',domain='reference',families=['H'])
    order('F21','E13','x','Y','J','西望永寧寺正相當；只编码西望方向，不编码同一中轴。')
    order('GJE','E13','x','R','J','御道〈東〉；东为校补。',group='jingle_east',requires=['F21'],projection_limit='不把补字记作无异文正文。')
    order('F22','E14','x','S','J','寺西有司徒府')
    order('F23','E14','x','J','Q','東有大將軍高肇宅')
    order('F24','E14','y','J','D','北連義井里')
    order('W04','E15','x','Y','WC','水西有永寧寺',families=['W'])
    add('W05','E15','note','渠水夹路、太尉司徒两坊间。未知两坊左右顺序及两条渠具体几何；不把渠线等同御道中线。',families=['W'],note_type='topology_requires_interpretation')
    order('H13','E16','y','Z','T','昭元曹，太尉府南')
    order('H14','E16','y','T','U','御史臺，太尉府北')
    order('F25','E17','y','YT','YD','浮圖北有佛殿一所')
    add('F26','E17','note','九层塔与佛殿为寺内构件；不据此设塔殿同轴或院落边界。',note_type='composition')
    add('P18','E18','note','九级/司州南向关系的相容性由模型计算；此条项目推理不再反过来当作输入证据。',families=[],note_type='project_inference')
    alias('ATF','E07','TF','T','merge_taifu',families=['H','L'],requires=['H01','F16','C07'])
    assert {a['evidence_id'] for a in atoms}==set(by_e)
    return atoms

QUERIES=[
 {'id':'taiwei_west','title':'太尉府在御道西','kind':'order','axis':'x','less':SHORT['T'],'more':SHORT['R']},
 {'id':'taiwei_east','title':'太尉府在御道东','kind':'order','axis':'x','less':SHORT['R'],'more':SHORT['T']},
 {'id':'jingle_east','title':'景乐寺在御道东','kind':'order','axis':'x','less':SHORT['R'],'more':SHORT['J']},
 {'id':'yongning_west','title':'永宁寺在御道西','kind':'order','axis':'x','less':SHORT['Y'],'more':SHORT['R']},
 {'id':'lingyin_south_jiuji','title':'凌阴里在九级府南','kind':'order','axis':'y','less':SHORT['N'],'more':SHORT['K']},
 {'id':'sizhou_south_jiuji','title':'司州在九级府南','kind':'order','axis':'y','less':SHORT['SZ'],'more':SHORT['K']},
 {'id':'miao_inside','title':'当前太庙对象在城内','kind':'membership','node':SHORT['M'],'boundary':'city_inner','value':'inside'},
 {'id':'she_inside','title':'当前太社对象在城内','kind':'membership','node':SHORT['A'],'boundary':'city_inner','value':'inside'},
 {'id':'taifu_identity','title':'太府寺与太尉府同体','kind':'alias','a':SHORT['TF'],'b':SHORT['T']},
 {'id':'yushi_north_taiwei','title':'御史台在太尉府北','kind':'order','axis':'y','less':SHORT['T'],'more':SHORT['U']}]

def proof_subset(atoms,q):
    expected=Model(atoms).query(q)['status']
    if expected not in ('entailed','contradicted'):return []
    core=list(atoms)
    for a in list(core):
        t=[b for b in core if b['id']!=a['id']]
        if Model(t).query(q)['status']==expected:core=t
    return [a['id'] for a in core]

def scenarios(atoms):
    base={'H_identity','W_context'}
    cases=[]
    for w,e,j in product((0,1),repeat=3):
        enabled=base|({ 'west_side'} if w else set())|({'east_side'} if e else set())|({'jingle_east'} if j else set())
        cases.append({'id':f's{w}{e}{j}','title':f'西侧继承{w} · 东侧继承{e} · 景乐补东{j}','enabled':sorted(enabled),'excluded_families':[],
           'question':'路侧解释变化；固定同名官署工作对应、地方北向及研究同相假设。'})
    allside=base|{'west_side','east_side','jingle_east'}
    for fam in ('L','H','W'):
        cases.append({'id':'without_'+fam,'title':'撤去来源组 '+fam,'enabled':sorted(allside),'excluded_families':[fam],
                      'question':'也撤去依赖该来源的假设；H可能转引L，删源不是独立证据统计。'})
    for ident,phase,boundary,name in [(1,1,1,'合并同体＋同时＋同城界'),(0,1,1,'不合并门内外同体'),(1,0,1,'不合并未知时相'),(1,1,0,'不合并城界参照')]:
        enabled=allside|({'outer_identity'} if ident else set())|({'outer_phase'} if phase else set())|({'outer_boundary'} if boundary else set())
        cases.append({'id':f'ritual{ident}{phase}{boundary}','title':name,'enabled':sorted(enabled),'excluded_families':[],
                      'question':'分别改变三个前提；相容不证明真的不同体、分期或迁建。'})
    cases.append({'id':'merge_taifu','title':'试把太府与太尉合并','enabled':sorted(allside|{'merge_taifu'}),'excluded_families':[],
                  'question':'与不合并的s111比较；可满足不等于身份已证。'})
    out=[]
    for case in cases:
        selected=select(atoms,set(case['enabled']),case['excluded_families']);model=Model(selected)
        case={**case,'sat':model.sat,'active_ids':[a['id'] for a in selected],
              'queries':[{**q,**model.query(q)} for q in QUERIES],
              'witness_certificate':model.certificate()}
        for q in case['queries']:q['support_subset']=proof_subset(selected,q)
        if not model.sat:
            honly=select(selected,set(case['enabled']),['W'])
            case['conflict_cores']=[minimal_core(honly)]
            # Obtain one separate core for each ritual object, not claim exhaustive MUS enumeration.
            for forbidden in ('H10','H11'):
                rest=[a for a in honly if a['id']!=forbidden]
                core=minimal_core(rest)
                if core and set(core) not in [set(c) for c in case['conflict_cores']]:case['conflict_cores'].append(core)
        out.append(case)
    return out
