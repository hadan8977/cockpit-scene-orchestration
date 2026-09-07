"""Restore archived response JSONL for offline analysis, without credentials."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent/'results'/'prompt-lab-v3'

def main():
    count=0
    for descriptor in sorted(ROOT.glob('*/archive.json')):
        meta=json.loads(descriptor.read_text(encoding='utf-8'))
        packed=(descriptor.parent/meta.get('archive','raw.jsonl.gz')).read_bytes()
        assert hashlib.sha256(packed).hexdigest()==meta['gzip_sha256'],descriptor
        raw=gzip.decompress(packed)
        assert hashlib.sha256(raw).hexdigest()==meta['raw_sha256'],descriptor
        target=descriptor.parent/'raw.jsonl'
        if target.exists():
            assert target.read_bytes()==raw,'Existing raw differs: '+str(target)
        else:target.write_bytes(raw)
        count+=1
    print('Restored or verified',count,'response archives; no API calls')
    ledger_meta=ROOT/'campaign-archive.json'
    if ledger_meta.exists():
        meta=json.loads(ledger_meta.read_text(encoding='utf-8'))
        packed=(ROOT/meta['archive']).read_bytes()
        assert hashlib.sha256(packed).hexdigest()==meta['gzip_sha256']
        raw=gzip.decompress(packed)
        assert hashlib.sha256(raw).hexdigest()==meta['raw_sha256']
        target=ROOT/'campaign.json'
        if target.exists():assert target.read_bytes()==raw,'Active ledger differs from archive'
        else:target.write_bytes(raw)
        print('Restored or verified campaign ledger')

if __name__=='__main__':main()
