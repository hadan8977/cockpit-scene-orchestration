"""Export safe checkpoints, verify archives, and restore a fresh checkout offline."""
import argparse,gzip,json,sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from study import HERE,save,sha,rows

CHECKPOINTS={'generation':'private-ledger.json','judge':'judge-private-ledger.json'}
def export():
    snapshots={};amounts={}
    for kind,name in CHECKPOINTS.items():
        original=json.loads((HERE/name).read_text(encoding='utf-8'))
        assert not any(a['status']=='reserved' for a in original['attempts']),'Wait for all calls to finish'
        allowed=('created','initial_cny','last_cny','ds_floor_cny','ds_max_calls','or_max_usd','or_max_calls') if kind=='generation' else ('max_calls','max_usd')
        checkpoint={k:original[k] for k in allowed if k in original}
        fields=('index','provider','model','job','upper','status','at','error','charged')
        checkpoint['attempts']=[{k:a[k] for k in fields if k in a} for a in original['attempts']]
        # No API keys, headers, raw prompts, response bodies or private paths.
        payload=json.dumps(checkpoint,ensure_ascii=False,separators=(',',':')).encode();packed=gzip.compress(payload,mtime=0)
        name=kind+'.json.gz';folder=HERE/'handoff-budget';folder.mkdir(exist_ok=True);(folder/name).write_bytes(packed)
        snapshots[kind]={'file':name,'sha256':sha(packed),'json_sha256':sha(payload),'attempts':len(checkpoint['attempts']),'reserved':0}
        amounts[kind]=({'attempts':len(original['attempts']),'max_calls':original['ds_max_calls'],'remaining_calls':original['ds_max_calls']-len(original['attempts']),'initial_observed_cny':original['initial_cny'],'last_observed_cny':original['last_cny'],'floor_cny':original['ds_floor_cny'],'observed_balance_change_cny':round(original['initial_cny']-original['last_cny'],4)} if kind=='generation' else {'attempts':len(original['attempts']),'max_calls':original['max_calls'],'remaining_calls':original['max_calls']-len(original['attempts']),'charged_or_reserved_usd':sum(a.get('charged',a['upper']) for a in original['attempts']),'max_usd':original['max_usd']})
    save(HERE/'handoff-budget/manifest.json',{'exported_at_utc':datetime.now(timezone.utc).isoformat(),'files':snapshots,'budget':amounts,'note':'Accounting checkpoints only; no credentials. Generation balance change may include outside calls. Restore before any paid call in a fresh checkout.'})
    runs={}
    for folder in sorted((HERE/'results').iterdir()):
        if (folder/'manifest.json').exists():
            m=json.loads((folder/'manifest.json').read_text(encoding='utf-8'));a=json.loads((folder/'archive.json').read_text(encoding='utf-8')) if (folder/'archive.json').exists() else {}
            runs[folder.name]={'expected':m['expected'],'archived_rows':a.get('rows',0),'complete':a.get('rows')==m['expected'],'summary':(folder/'summary.json').relative_to(HERE).as_posix()}
    reviews={}
    for folder in sorted((HERE/'judge').iterdir()):
        if folder.is_dir() and (folder/'raw.jsonl').exists():
            r=rows(folder/'raw.jsonl');reviews[folder.name]={'calls':len(r),'valid':sum(x.get('rating') is not None for x in r),'summary_exists':(folder/'summary.json').exists()}
    state={'as_of_utc':datetime.now(timezone.utc).isoformat(),'status':'handoff; no paid evaluation jobs running','final_prompt_accepted':False,'working_candidates':['p24_zh','p24_without_wording'],'screening_control':'p24_zh; not P-final','baseline':'v3_protocol primary, v0_protocol supplementary; both current 114-capability adapters','registry_version':'2026-09-07.0807','runs':runs,'reviews':reviews,'budget':amounts,'next_registered_generation':'plans/10_wording_followup.json','next_registered_review':'judge/ablation-all-plan.json','holdout':{'file':'holdout-v2.1.jsonl','cases':80,'model_calls':0,'status':'frozen; do not tune prompts after first query'},'demo':{'repository':'https://github.com/hadan8977/scene-studio-demo','integration_commit':'0ad75616f80610d82987a46ef37867edc74e6996','python_offline_tests':30,'product_logic_tests':67,'product_ui_tests':29,'runtime_ui_tests':1,'live_smoke_cases':6,'live_smoke_passed':6,'live_smoke_paid_calls':5,'public_runtime_enabled':False,'local_demo_url':'http://127.0.0.1:3101','browser_visual_walkthrough':'blocked: no browser available; not claimed completed'}}
    save(HERE/'STATE.json',state);print(json.dumps({'exported':True,'generation_calls':amounts['generation']['attempts'],'review_calls':amounts['judge']['attempts']}))

def verify(restore=False):
    count=0
    for folder in (HERE/'results').iterdir():
        archive=folder/'archive.json'
        if not archive.exists():continue
        manifest=json.loads(archive.read_text(encoding='utf-8'));packed=(folder/'raw.jsonl.gz').read_bytes();assert sha(packed)==manifest['gzip_sha256'],folder.name
        raw=gzip.decompress(packed);assert sha(raw)==manifest['raw_sha256'] and len(raw.splitlines())==manifest['rows'],folder.name
        target=folder/'raw.jsonl'
        if restore:
            if target.exists():assert sha(target.read_bytes())==manifest['raw_sha256'],'Existing raw differs: '+folder.name
            else:target.write_bytes(raw)
        count+=1
    manifest=json.loads((HERE/'handoff-budget/manifest.json').read_text(encoding='utf-8'))
    for kind,name in CHECKPOINTS.items():
        item=manifest['files'][kind];packed=(HERE/'handoff-budget'/item['file']).read_bytes();assert sha(packed)==item['sha256']
        raw=gzip.decompress(packed);assert sha(raw)==item['json_sha256'];checkpoint=json.loads(raw)
        target=HERE/name
        if restore:
            if target.exists():
                existing=json.loads(target.read_text(encoding='utf-8'));assert len(existing['attempts'])>=item['attempts'],'Existing budget is older; do not silently overwrite'
            else:save(target,checkpoint)
    print(json.dumps({'verified_generation_archives':count,'budget_checkpoints':2,'restored_missing_files':restore,'paid_calls':0}))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['export','verify','restore']);a=ap.parse_args()
    export() if a.action=='export' else verify(a.action=='restore')
