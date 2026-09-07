"""Recover valid dimension scores without inventing missing overall preferences.

No API calls. Original judge responses and the strict first summary are preserved.
"""
import json
from pathlib import Path
from safe_eval import read_rows, atomic

ROOT=Path(__file__).resolve().parent/'results'/'prompt-lab-v3'/'09_blind_review'
DIMS=('grounding','restraint','wording','composition')

def main():
    original=read_rows(ROOT/'judge.jsonl')
    mapping={r['sample_id']:r for r in json.loads((ROOT/'mapping.json').read_text(encoding='utf-8'))}
    latest={};invalid=[]
    for row in original:
        try:
            scores=json.loads(row['provider_response']['choices'][0]['message']['content'])
            assert all(type(scores[s][d]) is int and 1<=scores[s][d]<=5 for s in ('A','B') for d in DIMS)
        except (AssertionError,ValueError,KeyError,TypeError):
            invalid.append(row['sample_id']);continue
        preference=scores.get('preference')
        latest[row['sample_id']]={'sample_id':row['sample_id'],'scores':scores,
                                 'preference':preference if preference in ('A','B','tie') else None,
                                 'preference_missing_or_invalid':preference not in ('A','B','tie')}
    groups={'p3':[],'final':[]};prefs={'p3':0,'final':0,'tie':0,'missing':0}
    for sid,row in latest.items():
        m=mapping[sid]
        for side in ('A','B'):groups[m[side]].append(row['scores'][side])
        preference=row['preference']
        prefs['missing' if preference is None else 'tie' if preference=='tie' else m[preference]]+=1
    costs=[(r.get('provider_response') or {}).get('usage',{}).get('cost') for r in original]
    summary={'model':'qwen/qwen3.8-27b','human_review':False,'position_randomized':True,
             'pairs_completed':len(latest),'requests':len(original),'preference':prefs,
             'preference_available_pairs':len(latest)-prefs['missing'],
             'arms':{arm:{d:sum(x[d] for x in rows)/len(rows) if rows else None for d in DIMS} for arm,rows in groups.items()},
             'known_cost_usd':sum(c for c in costs if isinstance(c,(int,float))),
             'unknown_cost_calls':sum(not isinstance(c,(int,float)) for c in costs),
             'invalid_dimensions':invalid,
             'note':'Post-response parser amendment: valid original 1..5 integer dimension ratings retained even when preference is absent. Missing preferences are missing, never ties or inferred from scores. No model reruns or rubric changes.'}
    old=ROOT/'summary.json'
    if old.exists() and not (ROOT/'summary.strict-original.json').exists():
        (ROOT/'summary.strict-original.json').write_bytes(old.read_bytes())
    atomic(ROOT/'audited-ratings.json',list(latest.values()))
    atomic(ROOT/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
