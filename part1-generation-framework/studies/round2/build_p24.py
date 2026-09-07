"""Register targeted completeness corrections; confirmation holdout remains unseen."""
import json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_candidates import HERE,write
from build_p19 import output,a

p=(HERE/'prompts/p23_zh.md').read_text(encoding='utf-8')
p=p.replace('vague/affect提议0—4个相关动作，通常1—2个。','vague/affect提议0—4个相关动作，按实际目标与偏好选择互补手段。')
p=p.replace('后排哄睡可用全车模式和低音量，或不设声场。','后排哄睡优先前排模式和低音量，不用全车模式代替前排。')
p=p.replace('按摩模式标记规划中时照样写warnings。','按摩模式未上线时照样写warnings。')
p+='''
[complete_experience]
不要把简洁误作少做。对于用户主动要求的氛围/放松/休息，完整覆盖2–4个互补功能；被偏好否定的手段不能用。创建氛围而灯光当前开关未知，需要开启氛围灯再设柔和亮度，可配放松音乐；只有已经开启时才省略开关。空气不好可净化配内循环；明确闷且外部空气不差可外循环配风量。单独精确设备命令仍不增项。完整目标优先，不能将所有模糊请求退化为只调亮度。
understanding自然说人话，直接对用户：具体处境、重要已知数字/对象、这组设置的帮助。不要‘需要改善…/需要编排…’等泛化报告。只用给定的事实，不把普通累解读成驾驶失能。英文≤80字符仍可具体，如“Twenty minutes home; soft light and gentle massage can ease the last stretch”。say可以空，若开口则温暖且有用，不声称接管/已经执行，不说教‘深呼吸’，不用‘亲爱的’；不用空话装关怀。咨询怎么设置时说‘可以这样搭配…’而非机械重复需求。
Narrow clarification: 用户已经明确后排，则不用再追问是前排还是后排；‘后排有人就开后排加热’可用左后排安全带系上 OR 右后排安全带系上作为代理，左右后排加热都开；understanding或warnings明确这只是安全带代理，不是后排占位传感器。只有完全没说席位才追问。绝不用任意座椅代替后排。若用户要求分别自动控制左右，才追问拆成两条规则。
warnings对未落地能力统一称‘尚未上线，仅供提议’ / ‘not released; proposal only’，必须包含完整能力名，避免把sprint误称planned；其他解释随locale。记住概念提案可以选一个未落地功能并披露，不能因为怕警告而丢掉对目标最有用的手段。
'''
examples=[
({'locale':'zh','utterance':'车里有点缺少氛围','context':''},output(understanding='可以用柔和灯光配一点放松音乐，让车内更有氛围',intent='vague',relevance=.8,name='微光',actions=[a('氛围灯开关','开启'),a('氛围灯亮度','30%'),a('音乐播放','放松')],say='慢慢享受这一刻',warnings=['音乐播放：尚未上线，仅供提议'])),
({'locale':'en','utterance':'The air feels bad','context':''},output(understanding='Air purification and recirculation can help freshen the cabin',intent='vague',relevance=.8,name='Fresh',actions=[a('自动空气净化','开启'),a('内外循环设置','内循环')],say='Freshen up')),
({'locale':'en','utterance':'I could use a rest','context':'Parked. Prefers no music and no fragrance.'},output(understanding='Soft light and low airflow for a quiet break, without music',intent='vague',relevance=.8,name='Rest',actions=[a('氛围灯开关','开启'),a('氛围灯亮度','10%'),a('音乐律动','关闭'),a('前排风量调节','1挡')],say='Take your time')),
({'locale':'zh','utterance':'累了以后怎样设置比较好','context':''},output(understanding='可以用轻柔按摩配低亮灯光，给疲惫的身体一点放松',intent='vague',relevance=.8,name='歇歇',actions=[a('主驾座椅按摩模式','波浪'),a('主驾座椅按摩强度','1挡'),a('氛围灯开关','开启'),a('氛围灯亮度','20%')],say='可以这样搭配',warnings=['主驾座椅按摩模式：尚未上线，仅供提议'])),
]
p+='[complete_examples]\n'+'\n'.join('INPUT: '+json.dumps(i,ensure_ascii=False,separators=(',',':'))+'\nOUTPUT: '+json.dumps(o,ensure_ascii=False,separators=(',',':')) for i,o in examples)+'\n'
# Repair older examples that directly oppose the new functional-completeness rule.
lines=p.splitlines()
for i,line in enumerate(lines):
    if not line.startswith('OUTPUT: '):continue
    obj=json.loads(line[8:]);inp=json.loads(lines[i-1][7:]) if lines[i-1].startswith('INPUT: {') else {}
    for j,w in enumerate(obj.get('warnings',[])):
        if '规划中' in w or '提议能力' in w:
            obj['warnings'][j]=re.sub(r'规划中|提议能力','尚未上线，仅供提议' if inp.get('locale')=='zh' else 'not released; proposal only',w)
    if obj.get('intent') in ('vague','affect') and any(a['primary']=='氛围灯亮度' for a in obj['actions']) and not any(a['primary']=='氛围灯开关' for a in obj['actions']) and len(obj['actions'])<4:
        obj['actions'].insert(0,a('氛围灯开关','开启'))
    lines[i]='OUTPUT: '+json.dumps(obj,ensure_ascii=False,separators=(',',':'))
write('prompts/p24_zh.md','\n'.join(lines)+'\n')
selection=json.loads((HERE/'development-selection.json').read_text(encoding='utf-8'))
write('plans/07_completeness.json',{'run_id':'07_completeness','repeat':1,'seed':71435,'ids':selection['ids'],'variants':{'p23':'prompts/p23_zh.md','p24':'prompts/p24_zh.md','v3_protocol':'prompts/v3_latest_compatible.md'}})
write('AMENDMENT-06.md','''# 第七轮：完整效果与具体表达

p23 自动可用率96.1%，但开发盲评进行中的逐条理由已暴露：氛围只调亮度、不保证灯光打开；空气质量仅净化；明确后排仍追问；understanding遗漏给定剩余时间；将sprint写成planned。完整盲评继续跑完，所有结果保留，不把部分结果当确认结论。

p24 保留p23路由、安全与值域，去掉“通常1–2个”对主动场景完整性的诱导；补开关依赖与互补功能、具体自然表达、代理条件披露；统一未上线警告，修正与新规则矛盾的示例。这是多个机制的开发迭代，不能当单变量因果实验。冻结后384次同批随机交错对照，再做相同口径盲评；新holdout仍未调用。
''')
print('Prepared p24 completeness screen: 384 calls')
