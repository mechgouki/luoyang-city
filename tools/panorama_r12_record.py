#!/usr/bin/env python3
"""Bind the rejected fifth rendering and sixth-trial appendix to R12 evidence.

This builder records a rejection; it cannot approve a candidate or homepage.
The source PNG and independent review are frozen inputs, never regenerated.
"""
from pathlib import Path
import copy
import csv
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from panorama_v14 import WEBP_CONVERSION, encode_candidate_webp, png_size

OUT = ROOT / 'research/panorama-r12'
PNG_SHA = '45813547ae4555e9b60226f72adfd6df75aa0a36324a23c50966adc3092a0fa6'
REVIEW_SHA = '63d50a665ae7f20cc679132f6f693045fcac4c3863033283c9280ab2e4476bc3'
MEASUREMENT_NOTICE = ('图面位置为人工约读，通常有约5—10像素读数不确定性，并受遮挡、台基高度和可见边缘辨识影响；不作考古量测。'
    '第五次门槛约y477与底稿中心y451不是同名控制点；以同侧来源南缘y452.4—453.3参照，画面上约前移24像素。'
    '佛殿可见前基约y426与同侧来源前缘y416—417参照，约差9—10像素；不能把与来源框心y414相减所得12像素称为精确位移。'
    '塔脚附近可见边缘不自动等于塔座接地边或框心，遮挡部位保持未核。原始独立审查与偏差图保留原字节，其中异名参考点间的连线或差值只作画面诊断，均不构成同名控制点残差或遗址误差。')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


BLOCKERS = [
    '南门实际只能辨出两层，未保持三层楼观要求；后方木塔楼层不能并入门楼计数。',
    '南门门槛约在画面(515,477)，以底稿同侧南缘约y452.4—453.3参照，画面上仍约前移24像素；门基正面约38—43像素，底稿约22.5像素，位置与尺度未落实。这是人工约读，不是门槛与底稿框心(512,451)之间的同名控制点残差。',
    '佛殿虽已横向回到塔后中轴附近，可见前基约y426，与底稿同侧前缘约y416—417相比仍约偏前9—10像素；基宽约45—50像素，底稿约26像素。塔脚附近可见前缘约y440—445不能直接等同来源塔座边线，完整塔座中心仍受遮挡，不能宣布配准通过。',
    '可见寺墙约在x454—578、y420—483，底稿约x459—565、y399—454，整体向前漂移约20—30像素，七段墙线未可靠落实。',
    '宫城二、三号门尚不能分别可靠辨识，两阙关系与完整宫轴仍待改绘；大面积裸土宫区是待补的艺术概化，不能解释成资料已证空地。',
]


ACTUAL = {
 'common-ground-frame': (
    '共同透视底稿已完成：89项来源几何、863个顶点共用一套H；第五次试绘仍有明确的基脚与墙段偏差，整体图面未通过。',
    '交付整幅与永宁寺局部透视底稿、计层绘图占位和偏差核验图；原始几何与来源角色保持。没有把底稿通过改写成成图通过。',
    'changed'),
 'yongning-whole-footprint': (
    '寺院已比前三次试绘缩小，并与前景城墙间出现街坊间隔；第五张低墙/篱墙约x454—578、y420—483，仍整体偏前约20—30像素。',
    '尝试缩回来源占地，但未达到x459—565、y399—454的冻结底稿；本次公开未通过样张及差异，不接纳为已完成复原。',
    'attempted_not_accepted'),
 'south-gate-ground-and-storeys': (
    '实际可辨底层门洞与一层木楼，共两层。门槛约(515,477)，对照同侧来源南缘约y452.4—453.3，画面上约前移24像素；正面基部约38—43像素。门槛、来源地面边线与框心不是同名控制点，台阶或屋檐也不能算成门基。',
    '已尝试加宽并调整三层门，但最终楼层、基脚位置和尺度均未通过；仍须按底稿重新处理，不能沿用前版通过结论。',
    'attempted_not_accepted'),
 'tower-plinth-and-nine-storeys': (
    '第五张九个主要木构层可辨，未把顶部窄檐带、金刹或门楼计入；最低木构及塔脚附近可见前缘约y440—445，完整塔座中心仍受遮挡，该可见边缘不能直接等同来源塔座南缘。',
    '九层视觉特征保持，塔的地面落位仍未通过；在审查中分别记录层数与基脚，不把前者替代后者。',
    'attempted_not_accepted'),
 'buddha-hall-and-wall-gaps': (
    '佛殿从塔右后方回到塔后中轴附近x517；可见前基约y426、宽45—50像素，与底稿同侧前缘约y416—417及宽约26像素仍不符。前后约差9—10像素是人工画面诊断，不是可见前基对来源框心y414的精确位移。低墙重新出现，但七段墙线与门缺口仍未确认落实。',
    '横向归轴与墙体显现是实际试改；深度、尺度与墙段仍不接纳。未知北门、回廊和僧房格网没有据空白补成已证建筑。',
    'attempted_not_accepted'),
 'changhe-local-outline': (
    '第三张后宫前主门与太极的大体位置趋近底稿，后续局部寺院修订沿用该宫区；两阙间距和门组构件未获得完整匹配结论。',
    '全景尝试收小宫前门组；精确底稿仍保留S37十项来源构件与开放边。成图只作为未通过的试绘，不声称十项已经全部化为可靠建筑形体。',
    'attempted_not_accepted'),
 'taiji-and-palace-depth': (
    '太极主体的大体地面位置较前两次试绘接近底稿；二、三号门仍不可分别可靠辨识，宫区画成大面积单一裸土场。',
    '减少旧图夸大的主殿与重复宫院，但尚未完成宫轴层次；裸土空场列为待修的艺术假设，绝不把资料缺省解释为历史空置。',
    'attempted_not_accepted'),
 'palace-2013-comparison-role': (
    '冻结投影记录中24项2013宫城概览构件保持独立结构对照角色，clean绘图底稿没有把它们直接立成建筑；图像不能证明这些构件共时。',
    '沿用来源身份与时相限制；调查标位、版筑面和道路带不转为已证宫门、殿身或北宫墙。',
    'retained'),
 'unlocated-city-details': (
    '前景城墙、城门、河岸、桥头和无名街坊仍以完整艺术场景出现；不能从生成图回填精确历史坐标、普通房基或全部坊界。',
    '这些内容继续以未具体定位或艺术概括登记；浮桥舟体支承木桥面的视觉特征保留，不新增古岸几何或证据等级。',
    'not_located'),
}


def main():
    png = OUT / 'panorama-v14-source.png'
    review_path = OUT / 'reviews/v14-attempt5-review.json'
    assert sha(png) == PNG_SHA and sha(review_path) == REVIEW_SHA
    attempts = json.loads((OUT / 'generation-attempts.json').read_text())
    assert attempts['displayed_attempt'] == 5 and attempts['latest_attempt'] == 6
    assert attempts['total_attempts'] == len(attempts['attempts']) == 6
    assert attempts['all_attempts_rejected'] is True and attempts['accepted_attempt'] is None
    assert [item['attempt'] for item in attempts['attempts']] == list(range(1, 7))
    for item in attempts['attempts']:
        image_path, audit_path = ROOT / item['path'], ROOT / item['review_path']
        assert sha(image_path) == item['sha256'] and image_path.stat().st_size == item['bytes']
        assert list(png_size(image_path.read_bytes())) == item['size_px']
        assert sha(audit_path) == item['review_sha256'] and item['status'] == 'rejected'
        independent = json.loads(audit_path.read_text())
        assert independent['candidate_image']['sha256'] == item['sha256']
        assert independent['status'].startswith('rejected')
    assert attempts['attempts'][4]['sha256'] == PNG_SHA
    appendix = attempts['attempts'][5]
    assert sha(ROOT / appendix['prompt_path']) == appendix['prompt_sha256']
    assert (ROOT / appendix['prompt_path']).read_text().strip() in (OUT / 'generation-prompts.txt').read_text()
    audit = json.loads(review_path.read_text())
    assert audit['candidate_image']['sha256'] == PNG_SHA
    assert audit['status'].startswith('rejected')
    audit.update(source_png_sha256=PNG_SHA, review_status='rejected_needs_revision',
                 homepage_replacement_approved=False, blocking_findings=BLOCKERS,
                 measurement_notice=MEASUREMENT_NOTICE,
                 original_independent_review_path=str(review_path.relative_to(ROOT)),
                 original_independent_review_sha256=REVIEW_SHA)
    dump(OUT / 'visual-audit.json', audit)
    main_review = {
        'schema':'luoyang-r12-public-render-review-v1',
        'research_version':'R12.1', 'attempt':5,
        'source_png_sha256':PNG_SHA, 'review_status':'rejected_needs_revision',
        'homepage_replacement_approved':False, 'blocking_findings':BLOCKERS,
        'all_attempts_rejected':True,
        'total_attempts':6, 'displayed_attempt':5, 'latest_attempt':6,
        'source_projection_fidelity_passed':False,
        'entire_scene_historically_validated':False,
        'source_projection_completed':True,
        'actual_image_review_completed':True,
        'visible_storey_counts':audit['visible_storey_counts'],
        'manual_ground_observations':audit['manual_ground_observations'],
        'measurement_notice':MEASUREMENT_NOTICE,
        'independent_review':{'path':str(review_path.relative_to(ROOT)), 'sha256':REVIEW_SHA},
        'publication_meaning':'发布底稿与失败原因供回查；不等于接纳全景，更不批准替换首页。',
    }
    dump(OUT / 'candidate-review.json', main_review)

    draft = json.loads((OUT / 'change-evidence-draft.json').read_text())
    changes=[]
    for item in draft['changes']:
        item=copy.deepcopy(item)
        observation,change,treatment=ACTUAL[item['id']]
        item.update(observation=observation, change=change, treatment_type=treatment,
                    review_status='actual_review_completed_rejected_image', source_png_sha256=PNG_SHA)
        for key in ['planned_treatment_type','planned_adjustment','actual_image_measurements']:
            item.pop(key,None)
        changes.append(item)
    evidence={
        'schema':'luoyang-r12-space-evidence-change-table-v1',
        'research_version':'R12.1','source_png_sha256':PNG_SHA,
        'status':'needs_revision','review_status':'rejected_needs_revision',
        'homepage_replacement_approved':False,'blocking_findings':BLOCKERS,
        'source_inputs_sha256':draft['source_inputs_sha256'],
        'measurement_notice':MEASUREMENT_NOTICE,
        'changes':changes,
    }
    dump(OUT / 'change-evidence.json',evidence)
    with (OUT / 'change-evidence.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.writer(f, lineterminator='\n')
        writer.writerow(['对象ID','空间判断/对象','本轮状态','实际成图观察','来源与空间依据','图面处理','保留限制','逐段/逐图来源定位','回查链接'])
        for item in changes:
            writer.writerow([item['id'],item['title'],item['treatment_type'],item['observation'],item['evidence'],item['change'],item['limitation'],
                '\n'.join(x['path']+'#'+x['pointer']+' | '+x.get('locator','') for x in item['source_refs']),
                '\n'.join(x['label']+' '+x['url'] for x in item['evidence_links'])])

    encoded=encode_candidate_webp(png.read_bytes())
    width,height=png_size(png.read_bytes())
    variants={}
    for kind in ['full','small']:
        path=ROOT/'web/assets'/('luoyang-panorama-candidate-v14'+('-small' if kind=='small' else '')+'.webp')
        path.write_bytes(encoded[kind])
        variants[kind]={'path':str(path.relative_to(ROOT)),'sha256':sha(path),
                        'width':width if kind=='full' else 960,
                        'height':height if kind=='full' else round(height*960/width)}
    old=json.loads((ROOT/'research/city-spatial-r9/panorama-image-record.json').read_text())
    supports=[]
    def support(ident,title,description,path,role):
        p=ROOT/path
        assert p.is_file(),p
        supports.append(dict(id=ident,title=title,description=description,path=path,sha256=sha(p),role=role,download=True))
    support('projection-overview','统一透视总览 SVG','89项来源几何共用一套地面投影；示意视点不是历史测绘。','research/panorama-r12/projection-overview.svg','projection_overview')
    support('projection-yongning','永宁寺同源平面透视详图 SVG','塔座、佛殿、南门与七段墙线保持来源内比例；局部放大只改变显示。','research/panorama-r12/projection-yongning.svg','projection_yongning')
    support('massing-counted','九层塔与三层门计层底稿 PNG','高度、收分及屋顶均为绘图参数，非考古立面复原；此底稿的正确计层不等于试绘通过。','research/panorama-r12/massing-yongning-counted.png','massing_display')
    support('alignment-audit','底稿目标与第五次试绘偏差 SVG','冻结投影和人工约读分别画出；红色偏差不是新的遗址坐标，也没有改写试绘PNG。','research/panorama-r12/alignment-audit.svg','alignment_audit')
    for ident,title,description,path,role in [
        ('projection-data','共同投影数据 JSON','完整矩阵、来源几何及输入身份，外部注册仍未验证。','research/panorama-r12/projection.json','projection_data'),
        ('projection-qa','投影核对记录 JSON','单一H、原来源身份与关键地面范围。','research/panorama-r12/projection-qa.json','method'),
        ('massing-parameters','计层绘图参数 JSON','所有高度仅用展示单位；屋顶、收分、上部体量不称考古量测。','research/panorama-r12/massing-display-parameters.json','method'),
        ('alignment-data','图面偏差记录 JSON','实际第五张PNG与独立审查身份及人工观察范围。','research/panorama-r12/alignment-audit.json','method'),
        ('change-evidence','空间判断—依据—图面变化 JSON','九项判断及精确来源定位，失败试改保留。','research/panorama-r12/change-evidence.json','change_evidence'),
        ('change-evidence-table','空间判断—依据—图面变化 CSV','可筛查的证据对照表，含逐段/逐图回查链接。','research/panorama-r12/change-evidence.csv','change_evidence'),
        ('projection-method','共同透视与计层方法说明','来源图比例、艺术投影和外部候选落位分别说明。','docs/panorama-r12-projection.md','method'),
        ('generation-attempts','六次试绘及拒用记录 JSON','六次均未接纳；主显示第五次，第六次作为独立附录。每轮图像、审查与原始生成身份分别保存。','research/panorama-r12/generation-attempts.json','method'),
        ('attempt-6-image','第6次未通过试绘原始 PNG（附录）','实际第六次局部修订仍未通过；此附录不替换第五次主图，也不沿用第五次偏差数据。','research/panorama-r12/attempts/attempt-6.png','attempt_image'),
        ('attempt-6-prompt','第6次未通过试绘的实际提示词 TXT','保存本次局部编辑的原始指令；提示中的目标位置和层数不表示实际成图已经达标。','research/panorama-r12/attempts/attempt-6-prompt.txt','attempt_prompt'),
    ]: support(ident,title,description,path,role)
    summaries = [
        '寺院约为目标的2.2倍；门只有两层，九层塔不能核清。',
        '寺院仍偏前且增加额外南墙；门只有两层，九层塔不能核清。',
        '南门三层可辨；寺院仍约1.9倍，塔九层不能核清，佛殿偏右。',
        '塔九层可辨、寺院宽度接近；门只有两层，佛殿仍偏右，寺墙不清。',
        '塔九层可辨、佛殿横向归轴；门仍两层，寺门、殿基与寺墙再向前漂移。',
        '南门仍两层，前基约y477—479；寺南墙偏前，塔门独立基脚未核明。第六次修订未获接纳，单独附录回查。',
    ]
    for attempt, description in enumerate(summaries, 1):
        support('attempt-'+str(attempt)+'-review','第'+str(attempt)+'次试绘审查 · 未通过',description,
                'research/panorama-r12/reviews/v14-attempt'+str(attempt)+'-review.json','attempt_review')
    record={
        'schema':'luoyang-panorama-v14-image-v1','revision':'panorama-candidate-v14',
        'status':'needs_revision','review_status':'rejected_needs_revision',
        'total_attempts':6, 'displayed_attempt':5, 'latest_attempt':6, 'all_attempts_rejected':True,
        'homepage_replacement_approved':False,'blocking_findings':BLOCKERS,
        'measurement_notice':MEASUREMENT_NOTICE,
        'generation_tool':'built-in image_gen','title':'V14试绘审查 · 未通过',
        'alt':'北魏洛阳盛时全景第五次试绘。实际未通过：南门两层、门基与佛殿偏前，不能作为已校正的历史复原图。',
        'source_image':{'path':old['full']['path'],'sha256':old['full']['sha256']},
        'source_png':{'path':str(png.relative_to(ROOT)),'width':width,'height':height,'sha256':PNG_SHA},
        'source_png_sha256':PNG_SHA,'full':variants['full'],'small':variants['small'],
        'conversion':copy.deepcopy(WEBP_CONVERSION),
        'prompt_file':'research/panorama-r12/generation-prompts.txt',
        'candidate_review_file':'research/panorama-r12/candidate-review.json',
        'visual_audit_file':'research/panorama-r12/visual-audit.json',
        'changes':changes,
        'remaining_limits':[
            '本页第五次试绘明确未通过；发布审查不表示图像可作为已核复原，更不批准替换首页。',
            '第六次局部修订同样未通过，作为独立PNG、提示词与审查附录保留；主图及图面偏差记录仍绑定第五次，不能混用两轮观察。',
            '平面底稿来源的统一投影已经完成，艺术全景并未逐点服从该底稿；像素偏差不能转成古代实测误差。',
            MEASUREMENT_NOTICE,
            '7项候选绑定、0个已核现场共同控制点；没有新增古代实测坐标、真方位、古岸几何或建筑高度。',
            '516—528年是综合研究窗口，不证明画中所有建筑在同一年共存；2013概览构件时相未明，不自动纳入该窗口。',
            '佛殿图示框与太极尺度片各保留其来源角色；计层底稿中的高度、收分、屋顶和上部体量均为绘图占位。',
            '宫区大面积裸土是待修的艺术概化，来源缺省不证明历史空置；二、三号门与两阙细部仍待改绘。',
            '外郭相关遗存范围不等于连续城墙，片区视窗不等于坊界；前景城门、河岸、桥头、普通街坊及房屋仍含艺术假设。',
            '339项名录与237项几何不等于339座或237座已核建筑；165项仍未空间落位，不能由全景丰富程度宣称全城房基已经绘全。',
        ],
        'supporting_assets':supports,
    }
    dump(OUT/'image-record.json',record)
    print(json.dumps({'status':record['status'],'source_png_sha256':PNG_SHA,'changes':len(changes),'supporting_assets':len(supports),'blocking_findings':len(BLOCKERS),
                      'total_attempts':record['total_attempts'],'displayed_attempt':record['displayed_attempt'],'latest_attempt':record['latest_attempt']},ensure_ascii=False))


if __name__=='__main__':
    main()
