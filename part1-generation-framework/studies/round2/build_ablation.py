"""Single-block removal definitions fixed before p24 ablation calls."""
import json,re,random,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_candidates import HERE,write

p=(HERE/'prompts/p24_zh.md').read_text(encoding='utf-8')
def drop(text,names):
    for name in names:
        text,n=re.subn(r'^\['+re.escape(name)+r'\]\n.*?(?=^\[|\Z)','',text,flags=re.S|re.M)
        assert n==1,name
    return text
modules={'routing':['intent'],'composition':['selection','composition_gate'],'personalization':['memory','personalization'],'wording':['brevity'],'examples':['examples','experience_examples','complete_examples'],'safety':['safety'],'finalcheck':['final_check','completion_gate']}
variants={'p24':'prompts/p24_zh.md','v3_protocol':'prompts/v3_latest_compatible.md'}
for module,blocks in modules.items():
    value=drop(p,blocks)
    # The newer complete_experience paragraphs are attributed in advance.
    if module in ('composition','wording'):
        lines=value.splitlines();start=lines.index('[complete_experience]')
        del lines[start+(1 if module=='composition' else 2)]
        value='\n'.join(lines)+'\n'
    file='prompts/p24_without_'+module+'.md';write(file,value);variants['without_'+module]=file
# Lossless grouping of dictionary lines with exactly equal values and maturity.
headers=re.findall(r'^\[(?:CONDITIONS|ACTIONS) ONLY;.*\]$',p,re.M)
compact=p
for header in headers:
    pattern=re.escape(header)+r'\n(.*?)(?=^\[)'
    m=re.search(pattern,compact,re.M|re.S);groups={}
    for line in m[1].splitlines():
        if not line.strip():continue
        left,sep,right=line.partition(' = ')
        assert sep,line
        star=left.startswith('*');name=left[1:] if star else left
        groups.setdefault((right,star),[]).append(name)
    replacement=header+'\n'+'\n'.join(('*' if star else '')+'、'.join(names)+' = '+values for (values,star),names in groups.items())+'\n'
    compact=compact[:m.start()]+replacement+compact[m.end():]
write('prompts/p25_zh.md',compact);variants['p25_grouped_dictionary']='prompts/p25_zh.md'
# Fixed quality sample IDs plus 16 covering remaining categories, before calls.
quality=json.loads((HERE/'judge/development-p23-plan.json').read_text(encoding='utf-8'))['ids']
all_ids=json.loads((HERE/'development-selection.json').read_text(encoding='utf-8'))['ids']
items=[json.loads(x) for x in (HERE.parents[1]/'eval/testset.jsonl').read_text(encoding='utf-8').splitlines()]
selected=list(quality);rng=random.Random(71436)
for cat,count in {'precise':3,'robust':3,'attack':4,'memory':2,'observe':2,'clarify':2}.items():
    ids=sorted(x['id'] for x in items if x['cat']==cat and x['id'] in all_ids and x['id'] not in selected);rng.shuffle(ids);selected+=ids[:count]
assert len(selected)==32
write('plans/08_ablation.json',{'run_id':'08_ablation','repeat':1,'seed':71436,'ids':selected,'variants':variants})
write('ablation-map.json',{'parent':'p24','blocks_removed':modules,'additional_paragraph_removal':{'composition':'complete_experience paragraph 1','wording':'complete_experience paragraph 2'},'dictionary':'p25 groups names with exactly equal value strings and star maturity; no capacity/value removal','ids':selected,'calls':640,'limitation':'Rules are duplicated in examples, values and completion blocks. Removal estimates incremental contribution of these blocks, not the necessity of an entire concept. No final selection from ablation alone.'})
print('Prepared 8 module contrasts + full + baseline: 640 calls')
