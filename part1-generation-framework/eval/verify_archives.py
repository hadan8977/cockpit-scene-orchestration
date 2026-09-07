"""Offline integrity audit of compressed evidence; never invokes a model."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent/'results'/'prompt-lab-v3'

def main():
    checked=[]
    for descriptor in sorted(ROOT.glob('*/archive.json')):
        meta=json.loads(descriptor.read_text(encoding='utf-8'))
        packed=(descriptor.parent/meta.get('archive','raw.jsonl.gz')).read_bytes()
        raw=gzip.decompress(packed)
        assert hashlib.sha256(packed).hexdigest()==meta['gzip_sha256'],descriptor
        assert hashlib.sha256(raw).hexdigest()==meta['raw_sha256'],descriptor
        rows=[json.loads(line) for line in raw.splitlines() if line]
        assert len(rows)==meta['rows'],descriptor
        loose=descriptor.parent/'raw.jsonl'
        if loose.exists():assert loose.read_bytes()==raw,loose
        checked.append({'run':descriptor.parent.name,'rows':len(rows),'sha256':meta['raw_sha256']})
    # A selected policy is a view of existing calls, not additional evidence.
    for manifest in ROOT.glob('*/manifest.json'):
        m=json.loads(manifest.read_text(encoding='utf-8'))
        if m.get('kind')!='derived_selection':continue
        source=ROOT/m['source_run']/'raw.jsonl.gz'
        raw=gzip.decompress(source.read_bytes())
        assert hashlib.sha256(raw).hexdigest()==m['source_raw_sha256'],manifest
        src={ (r['variant'],r['id'],r['lang'],r['rep']):r for r in map(json.loads,raw.splitlines()) }
        selected=gzip.decompress((manifest.parent/'raw.jsonl.gz').read_bytes())
        for row in map(json.loads,selected.splitlines()):
            restored=dict(row)
            restored['variant']=restored.pop('source_variant')
            restored.pop('source_run')
            assert restored==src[restored['variant'],restored['id'],restored['lang'],restored['rep']],manifest
        assert m['new_api_calls']==0,manifest
    result={'status':'verified','archives':checked,'note':'Checks gzip/raw hashes, JSON parse, row counts and exact derived response provenance. No model requests.'}
    (ROOT/'evidence-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Verified',len(checked),'archives; no API calls')

if __name__=='__main__':main()
