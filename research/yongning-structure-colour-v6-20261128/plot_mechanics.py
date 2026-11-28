"""Publication-style charts of assumptions, with no generated raster diagrams."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

ROOT=Path(__file__).resolve().parent
R=json.loads((ROOT/'mechanics-results.json').read_text())
FONT=FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
plt.rcParams.update({'font.family':FONT.get_name(),'axes.unicode_minus':False,
                     'font.size':12,'axes.spines.top':False,'axes.spines.right':False,
                     'figure.facecolor':'#faf8f2','axes.facecolor':'#faf8f2',
                     'text.color':'#263e38','axes.labelcolor':'#263e38',
                     'xtick.color':'#4d5d56','ytick.color':'#4d5d56'})
fig=plt.figure(figsize=(14,9.4))
gs=fig.add_gridspec(1,2,left=.09,right=.96,bottom=.28,top=.72,wspace=.42)
ax=fig.add_subplot(gs[0,0]);cx=fig.add_subplot(gs[0,1])
ids=['sq1-eta0.3-p1','sq1-eta1-p1','sq1.2-eta0.5-p1']
cases=[next(s for s in R['lateral_scenarios'] if s['id']==k) for k in ids]
values=[s['max_interstory_drift_ratio']*100 for s in cases]
labels=['1.0 m 方柱\nη = 0.30','1.0 m 方柱\nη = 1.00（理想上界）','1.2 m 方柱\nη = 0.50']
bars=ax.bar(range(3),values,width=.58,color=['#b46247','#557e81','#557e81'])
ax.axhline(.5,color='#836d42',ls='--',lw=1.8)
ax.text(2.5,.53,'自定筛查线 0.5%（1/200）',ha='right',va='bottom',fontsize=10,color='#836d42')
ax.set_xticks(range(3),labels,fontsize=10)
ax.set_ylim(0,1.55)
ax.set_ylabel('最大层间位移 / 层高  （%）')
ax.set_title('A  相同外形，连接刚度改变结果',loc='left',pad=23,fontweight='bold')
ax.yaxis.grid(True,color='#deded4',lw=.8);ax.set_axisbelow(True)
for bar,v,s in zip(bars,values,cases):
    ax.text(bar.get_x()+bar.get_width()/2,v+.035,f'{v:.2f}%',ha='center',va='bottom',fontsize=13,fontweight='bold')
    ax.text(bar.get_x()+bar.get_width()/2,.06,f'屋顶侧移\n{s["roof_displacement_m"]:.2f} m',ha='center',va='bottom',fontsize=10,color='white')

core=R['core_self_weight_scenarios']; xx=np.arange(len(core));vals=[c['base_mean_self_compression_MPa'] for c in core]
bb=cx.bar(xx,vals,width=.58,color='#a6926c')
cx.set_ylim(0,1.4)
cx.set_xticks(xx,[f'芯高 {c["height_assumed_m"]:.0f} m\n约 {c["mass_t"]/10000:.2f} 万吨' for c in core],fontsize=10)
cx.set_ylabel('土芯底部平均自重压应力  （MPa）')
cx.set_title('B  土芯越高，自重压力越大',loc='left',pad=23,fontweight='bold')
cx.yaxis.grid(True,color='#deded4',lw=.8);cx.set_axisbelow(True)
for bar,v in zip(bb,vals):
    cx.text(bar.get_x()+bar.get_width()/2,v+.04,f'{v:.2f}',ha='center',va='bottom',fontsize=13,fontweight='bold')
cx.text(.04,.93,'底宽19.8 m → 顶宽10 m；线性收分\n容重18 kN/m³；仅计自重，不是材料强度',transform=cx.transAxes,va='top',fontsize=10,color='#6c6656')

fig.text(.06,.935,'永宁寺塔 V6｜力学敏感性结果',fontsize=24,fontweight='bold')
fig.text(.06,.885,'147 m 外形不能独自决定结构是否可行：以下均为公开假设下的筛查。',fontsize=14)
fig.text(.06,.831,'木架与瓦屋面中值重力 58.8 MN（约6,000吨）  ·  有效风压情景 1.0 kPa  ·  未借用土芯抗侧刚度',fontsize=11)
fig.text(.06,.211,'A：64 根等效方柱，E=8 GPa，上部截面随塔身收分；η 是刚度比例假设，不是实测榫卯参数。',fontsize=11)
fig.text(.06,.171,'η=0.03 的 1.0 m 方柱方案出现负有效刚度，在此模型中失稳；通过位移筛查也不等于可建。',fontsize=11,color='#9c4c37')
fig.text(.06,.131,'B：土芯高度与顶宽均未由考古确定。没有套用现代土样强度作永宁寺容许值，也未计算木土共同抗侧。',fontsize=11)
fig.text(.06,.077,'模型：九自由度剪切弹簧 + 重力几何软化。风力上移为节点荷载包络；不代替非线性、地震谱与地基验算。',fontsize=10,color='#68766a')
fig.text(.06,.043,'53组风/参数情景与9组惯性力情景。改变截面时恒载固定，仅作敏感性；可复算数据见 mechanics-results.json。',fontsize=10,color='#68766a')
fig.savefig(ROOT/'mechanics-summary.png',dpi=170)
fig.savefig(ROOT/'mechanics-summary.svg')
print('Wrote mechanics-summary.png and .svg')
