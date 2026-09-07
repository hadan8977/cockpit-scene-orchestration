"""Compare complete deployment policies from the crossed language experiment."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from study import HERE,rows,save
from analysis import metrics,paired,mean,pct,holm

def main():
 data=rows(HERE/'results/09_language/raw.jsonl');report={}
 for version in ('p24','p25'):
  policies={
   'uniform_zh':[r for r in data if r['variant']==version+'_zh'],
   'uniform_en':[r for r in data if r['variant']==version+'_en'],
   'routed':[r for r in data if r['variant']==version+'_'+r['lang']],
  };summary={};tests={}
  for name,subset in policies.items():
   summary[name]={'n':len(subset),'rates':{k:mean([metrics(r)[k] for r in subset]) for k in metrics(subset[0])},'latency_p50':pct([r['latency'] for r in subset],.5),'latency_p95':pct([r['latency'] for r in subset],.95),'by_input_language':{lang:{k:mean([metrics(r)[k] for r in subset if r['lang']==lang]) for k in metrics(subset[0])} for lang in ('zh','en')}}
  for other in ('uniform_en','routed'):
   lookup={(r['id'],r['lang'],r['rep']):r for r in policies['uniform_zh']};result={}
   for key in metrics(policies[other][0]):
    clusters={}
    for a in policies[other]:
     b=lookup[a['id'],a['lang'],a['rep']];clusters.setdefault(a['id'],[]).append(metrics(a)[key]-metrics(b)[key])
    result[key]=paired(clusters)
   holm(result);tests[other+'_minus_uniform_zh']=result
  report[version]={'policies':summary,'comparisons':tests}
 save(HERE/'analysis/language-policies.json',{'results':report,'new_calls':0,'generation_calls':len(data),'note':'Each policy uses exactly one output per input. Routed rows are selected from the crossed arms, not fresh calls. Chinese and English examples and capability dictionaries remain unchanged; translated rule prose may still have semantic nuances. Both prompt versions are development candidates; no claim of universal language superiority.'})
 print(json.dumps({v:{p:{'usable':s['rates']['usable'],'schema':s['rates']['schema'],'locale_v2':s['rates']['locale_v2'],'safe':s['rates']['safe'],'p50':s['latency_p50'],'p95':s['latency_p95']} for p,s in d['policies'].items()} for v,d in report.items()}))

if __name__=='__main__':main()
