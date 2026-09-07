"""Deterministic compressed raw records, checksums, and a compact campaign snapshot."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
from safe_eval import atomic
HERE=Path(__file__).resolve().parent

def archive(run):
    root=HERE/"results"/"prompt-lab-v3"
    p=root/run/"raw.jsonl"
    summary=json.loads(p.with_name("summary.json").read_text(encoding="utf-8"))
    if summary["status"]!="complete": raise RuntimeError("Run is not complete")
    raw=p.read_bytes(); packed=gzip.compress(raw,mtime=0)
    p.with_suffix(".jsonl.gz").write_bytes(packed)
    atomic(p.with_name("archive.json"),{"raw_sha256":hashlib.sha256(raw).hexdigest(),"gzip_sha256":hashlib.sha256(packed).hexdigest(),"rows":len(raw.splitlines()),"archive":"raw.jsonl.gz"})
    ledger=json.loads((root/"campaign.json").read_text(encoding="utf-8"))
    atomic(root/"campaign-summary.json",{"attempts":len(ledger["attempts"]),"initial_balance_cny":ledger["initial_balance_cny"],"latest_observed_balance_cny":ledger["last_balance_cny"],"reserve_cny":ledger["reserve_cny"],"max_attempts":ledger["max_attempts"],"note":"Account balance change may include other sessions; unknown provider costs are not zero.","by_run":{r:sum(a["run_id"]==r for a in ledger["attempts"]) for r in sorted({a["run_id"] for a in ledger["attempts"]})}})
    print("Archived",run,len(raw.splitlines()),"rows")

if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("runs",nargs="+");a=ap.parse_args()
    for run in a.runs: archive(run)
