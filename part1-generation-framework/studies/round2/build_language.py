"""Instruction-only translations; dictionary and example data remain identical."""
import json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_candidates import HERE,write
from study import sha
translations=json.loads((HERE/'instructions_en.json').read_text(encoding='utf-8'))
manifest={'translator':'assistant-authored English instruction translation; not an independently certified equivalence','invariants':'Same dictionary bytes, example bytes, section labels/order, JSON contract and Chinese capability tokens. Examples remain bilingual in both arms.','variants':{}}
for version in ('p24','p25'):
    source=(HERE/f'prompts/{version}_zh.md').read_text(encoding='utf-8');target=source
    for name,value in translations.items():
        target,n=re.subn(r'^\['+re.escape(name)+r'\]\n.*?(?=^\[|\Z)',lambda m:'['+name+']\n'+value+'\n',target,flags=re.S|re.M)
        assert n==1,name
    for name in ('examples','experience_examples','complete_examples'):
        pattern=r'^\['+name+r'\]\n.*?(?=^\[|\Z)'
        assert re.search(pattern,source,re.S|re.M)[0]==re.search(pattern,target,re.S|re.M)[0]
    table=lambda text:text.split('[CONDITIONS ONLY;',1)[1].split('[examples]',1)[0]
    assert table(source)==table(target)
    write(f'prompts/{version}_en.md',target)
    manifest['variants'][version]={'zh':sha(source.encode()),'en':sha(target.encode()),'sections':list(translations)}
write('language-translation.json',manifest)
selection=json.loads((HERE/'development-selection.json').read_text(encoding='utf-8'))
write('plans/09_language.json',{'run_id':'09_language','repeat':1,'seed':71437,'ids':selection['ids'],'variants':{f'{v}_{l}':f'prompts/{v}_{l}.md' for v in ('p24','p25') for l in ('zh','en')}})
print('Prepared 512 crossed candidate/language calls; examples and capability bytes preserved')
