"""Separate, versioned analysis; never changes frozen generation scores or rows."""
import argparse,json,math,random,re,statistics,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from study import HERE,rows,save,sha,strict_json

BOOT=5000
def mean(xs):return statistics.mean(xs) if xs else None
def pct(xs,q):
    xs=sorted(xs)
    if not xs:return None
    i=(len(xs)-1)*q;lo=math.floor(i);hi=math.ceil(i)
    return xs[lo]*(hi-i)+xs[hi]*(i-lo) if hi!=lo else xs[lo]

def paired(clusters):
    values=[mean(v) for v in clusters.values() if v]
    if not values:return {'n_clusters':0,'delta':None,'ci95':None,'p_two_sided':None}
    rng=random.Random(9471);observed=mean(values)
    boot=sorted(mean(rng.choices(values,k=len(values))) for _ in range(BOOT))
    # Cluster sign-flip randomization; both locales/repeats stay together.
    null=[mean([v*rng.choice((-1,1)) for v in values]) for _ in range(10000)]
    p=(1+sum(abs(v)>=abs(observed)-1e-12 for v in null))/(len(null)+1)
    return {'n_clusters':len(values),'delta':observed,'ci95':[pct(boot,.025),pct(boot,.975)],'p_two_sided':p}

def holm(metrics):
    ordered=sorted((d['p_two_sided'],name) for name,d in metrics.items() if d.get('p_two_sided') is not None)
    prior=0
    for i,(p,name) in enumerate(ordered):
        prior=max(prior,min(1,p*(len(ordered)-i)));metrics[name]['p_holm']=prior

def locale_ok(r):
    try:o=strict_json(r['raw_text'])
    except (ValueError,TypeError):return False
    texts=[str(o.get(k) or '') for k in ('understanding','say','clarify')]
    han=lambda x:bool(re.search('[\u3400-\u9fff]',x))
    return all(not han(t) for t in texts) if r['lang']=='en' else all(not t.strip() or han(t) for t in texts)

def metrics(r):
    s=r['score'];ok=not r['error']
    return {'usable':int(ok and s.get('usable',False)),'task_pass':int(ok and s.get('pass',False)),
      'schema':int(ok and s.get('schema_valid',False)),'intent':int(ok and s.get('intent_ok',False)),
      'name':int(ok and s.get('name_ok',False)),'locale_v2':int(ok and locale_ok(r)),
      'safe':int(ok and not any('安全违规' in v for v in s.get('violations',[])))}

def compare(run,candidate,baseline):
    data=rows(HERE/'results'/run/'raw.jsonl');index={(r['id'],r['lang'],r['rep'],r['variant']):r for r in data}
    pairs=[(r,index[(r['id'],r['lang'],r['rep'],baseline)]) for r in data if r['variant']==candidate and (r['id'],r['lang'],r['rep'],baseline) in index]
    results={};summary={}
    for arm in (candidate,baseline):
        subset=[r for r in data if r['variant']==arm];m=[metrics(r) for r in subset]
        summary[arm]={'n':len(subset),'errors':sum(bool(r['error']) for r in subset),'rates':{k:mean([x[k] for x in m]) for k in m[0]},'latency':{f'{key}_{q}':pct([r[key] for r in subset if r.get(key) is not None and not r['error']],quantile) for key in ('latency','ttft','t_und') for q,quantile in (('p50',.5),('p95',.95))}}
        summary[arm]['by_locale']={lang:{k:mean([metrics(r)[k] for r in subset if r['lang']==lang]) for k in m[0]} for lang in ('zh','en')}
        summary[arm]['by_cat']={cat:mean([metrics(r)['usable'] for r in subset if r['cat']==cat]) for cat in sorted({r['cat'] for r in subset})}
        groups={}
        for r in subset:
            try:
                o=strict_json(r['raw_text']);signature=json.dumps({k:o.get(k) for k in ('intent','conditions','actions')},ensure_ascii=False,sort_keys=True)
            except (ValueError,TypeError):signature='ERROR:'+str(r['rep'])
            groups.setdefault((r['id'],r['lang']),[]).append(signature)
        repeated=[v for v in groups.values() if len(v)>1]
        summary[arm]['consistency']={'eligible_id_locale_groups':len(repeated),'exact_intent_condition_action_rate':mean([len(set(v))==1 for v in repeated])}
    for key in metrics(pairs[0][0]):
        clusters={}
        for a,b in pairs:clusters.setdefault(a['id'],[]).append(metrics(a)[key]-metrics(b)[key])
        results[key]=paired(clusters)
    for key in ('latency','ttft','t_und'):
        clusters={}
        for a,b in pairs:
            if a.get(key) is not None and b.get(key) is not None and not a['error'] and not b['error']:clusters.setdefault(a['id'],[]).append(a[key]-b[key])
        results[key+'_mean_seconds']=paired(clusters)
    holm(results)
    report={'run':run,'candidate':candidate,'baseline':baseline,'pairs':len(pairs),'summary':summary,'paired_tests':results,'analysis_sha256':sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')),'method':'Original raw scores unchanged. Equal-weight original-id clusters; 5000 bootstrap resamples; 10000 cluster sign flips; two-sided Holm family across displayed aggregate metrics. Point latency percentiles descriptive; mean latency tests are separate. Locale v2 requires Chinese display text to contain Han characters unless empty; English excludes Han. Names follow legacy scorer. No missing-value imputation.'}
    out=HERE/'analysis'/(run+'--'+candidate+'--'+baseline+'.json');save(out,report);return report

def review(name):
    folder=HERE/'judge';samples=json.loads((folder/(name+'-samples.json')).read_text(encoding='utf-8'));lookup={s['sample_id']:s for s in samples};data=rows(folder/name/'raw.jsonl');report={}
    for model in sorted({r['model'] for r in data}):
        subset=[r for r in data if r['model']==model];valid=[r for r in subset if r['rating']];dims={}
        for dim in ('grounding','restraint','wording','composition'):
            clusters={};x=[];y=[]
            for r in valid:
                s=lookup[r['sample_id']];pos=s['candidate_position'];a=r['rating'][pos][dim];b=r['rating']['B' if pos=='A' else 'A'][dim]
                x.append(a);y.append(b);clusters.setdefault(s['id'],[]).append(a-b)
            dims[dim]={**paired(clusters),'candidate':mean(x),'baseline':mean(y)}
        holm(dims)
        report[model]={'valid':len(valid),'expected':len(samples),'coverage_complete':len(valid)==len(samples),'dimensions':dims,'all_higher_and_holm_significant':len(valid)==len(samples) and all(d['delta']>0 and d['ci95'][0]>0 and d['p_holm']<.05 for d in dims.values())}
        for partition in ('locale','candidate_position'):
            report[model]['by_'+partition]={level:{dim:mean([r['rating'][lookup[r['sample_id']]['candidate_position']][dim]-r['rating']['B' if lookup[r['sample_id']]['candidate_position']=='A' else 'A'][dim] for r in valid if lookup[r['sample_id']][partition]==level]) for dim in dims} for level in sorted({s[partition] for s in samples})}
    save(folder/name/'inference.json',{'judges':report,'method':'Separate judge families; four dimensions Holm adjusted within judge; cluster by original id. Descriptive scores are paired valid responses only. Missing coverage prohibits confirmed superiority. Locale and position diagnostics descriptive.'});return report

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('kind',choices=['generation','review']);ap.add_argument('name');ap.add_argument('--candidate');ap.add_argument('--baseline',default='v3_protocol');a=ap.parse_args()
    report=compare(a.name,a.candidate,a.baseline) if a.kind=='generation' else review(a.name)
    print(json.dumps(report,ensure_ascii=False))
