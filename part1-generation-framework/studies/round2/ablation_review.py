"""Small prespecified experience diagnostics for every ablated module."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import review as J
from study import HERE,rows,save,encoded,sha,strict_json
from analysis import paired,holm,mean

NAME='ablation-all'
IDS={
 'without_routing':['N04','N05','F05','A10'],
 'without_composition':['C03','C08','E05','J04'],
 'without_personalization':['E06','E03','G02','G04'],
 'without_wording':['E03','E05','J04','C08'],
 'without_examples':['E03','C03','A10','N04'],
 'without_safety':['K03','K07','K04','K08'],
 'without_finalcheck':['N04','G04','D05','J05'],
 'p25_grouped_dictionary':['A10','N04','C03','E05'],
}

def prepare():
 records=rows(HERE/'results/08_ablation/raw.jsonl');index={(r['id'],r['lang'],r['variant']):r for r in records};samples=[]
 for contrast,ids in IDS.items():
  for case_id in ids:
   for lang in ('zh','en'):
    a=index[case_id,lang,contrast];b=index[case_id,lang,'p24']
    for reverse in (False,True):
     def output(r):
      try:return strict_json(r['raw_text'])
      except ValueError:return {'invalid_response':r['raw_text'],'transport_error':r['error']}
     samples.append({'sample_id':f'{contrast}:{case_id}-{lang}-'+('BA' if reverse else 'AB'),'contrast':contrast,'id':case_id,'locale':lang,'input':a['input'],'context':a['context'],'A':output(b if reverse else a),'B':output(a if reverse else b),'candidate_position':'B' if reverse else 'A'})
 save(HERE/'judge'/f'{NAME}-samples.json',samples)
 save(HERE/'judge'/f'{NAME}-plan.json',{'ids_by_contrast':IDS,'models':['luna','qwen'],'sample_sha256':sha(encoded(samples)),'calls':256,'selection':'Four mechanism-relevant development IDs per contrast, both locales and AB/BA. Fixed before these judge calls; selected for relevance, not observed delta.','limitation':'Four original IDs per component is exploratory, not a population necessity claim. Missing ratings retained. Within each judge Holm across all 32 component-dimension tests. The larger 16-ID wording study is separately disclosed.'})
 print('Prepared 256 blinded ablation review calls')

def summarize():
 samples=json.loads((HERE/'judge'/f'{NAME}-samples.json').read_text(encoding='utf-8'));lookup={s['sample_id']:s for s in samples};data=rows(HERE/'judge'/NAME/'raw.jsonl');report={}
 for model in ('luna','qwen'):
  all_tests={};contrasts={}
  for contrast in IDS:
   subset=[r for r in data if r['model']==model and lookup[r['sample_id']]['contrast']==contrast];valid=[r for r in subset if r['rating']];dims={}
   for d in J.DIMS:
    clusters={};cand=[];base=[]
    for r in valid:
     s=lookup[r['sample_id']];pos=s['candidate_position'];x=r['rating'][pos][d];y=r['rating']['B' if pos=='A' else 'A'][d]
     cand.append(x);base.append(y);clusters.setdefault(s['id'],[]).append(x-y)
    dims[d]={**paired(clusters),'ablated':mean(cand),'full_p24':mean(base)};all_tests[contrast+':'+d]=dims[d]
   contrasts[contrast]={'valid':len(valid),'expected':16,'dimensions':dims}
  holm(all_tests);report[model]=contrasts
 save(HERE/'judge'/NAME/'summary.json',report);print(json.dumps({'review':NAME,'complete':len(data),'expected':256}))

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','run','summarize']);ap.add_argument('--env-file');a=ap.parse_args()
 if a.action=='prepare':prepare()
 elif a.action=='run':
  samples=json.loads((HERE/'judge'/f'{NAME}-samples.json').read_text(encoding='utf-8'));J.run_review(NAME,samples,['luna','qwen'],a.env_file);summarize()
 else:summarize()
