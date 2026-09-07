"""Resumable, bounded DeepSeek-official prompt experiments. No proxy routing.

Example: python safe_eval.py --env-file /private/.env --plan experiment.json
The plan is immutable once a run starts. Every completed response is fsynced;
an interrupted attempt stays charged/reserved in the campaign ledger.
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import random
import statistics
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import requests
import run_eval as R

HERE = Path(__file__).resolve().parent
LOCK = threading.RLock()

def digest(x):
    return hashlib.sha256(x if isinstance(x, bytes) else json.dumps(x, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

def atomic(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.flush(); os.fsync(f.fileno())
    os.replace(temp, path)

def append(path, obj):
    with Path(path).open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, ensure_ascii=False, allow_nan=False) + "\n")
        f.flush(); os.fsync(f.fileno())

def read_rows(path):
    if not Path(path).exists():
        return []
    # A partial tail must be repaired explicitly; never silently drop completed rows.
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]

@contextmanager
def campaign_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as f:
        if f.tell() == 0:
            f.write(b"0"); f.flush()
        f.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            f.seek(0)
            if os.name == "nt":
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)

def credentials(path):
    vals = {}
    if path:
        for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
            k, sep, v = line.partition("=")
            if sep and k.strip() in ("DEEPSEEK_OFFICIAL_API_KEY", "DEEPSEEK_API_KEY"):
                vals[k.strip()] = v.strip().strip('"').strip("'")
    key = os.environ.get("DEEPSEEK_OFFICIAL_API_KEY") or vals.get("DEEPSEEK_OFFICIAL_API_KEY") or vals.get("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("Missing official DeepSeek credential; Tencent keys are never loaded")
    return key

def balance(key):
    r = requests.get("https://api.deepseek.com/user/balance", headers={"Authorization": "Bearer " + key}, timeout=20, allow_redirects=False)
    if r.status_code != 200:
        raise RuntimeError("Balance query failed: HTTP %d" % r.status_code)
    j = r.json()
    cny = next((float(x["total_balance"]) for x in j.get("balance_infos", []) if x.get("currency") == "CNY"), None)
    if cny is None or not j.get("is_available"):
        raise RuntimeError("No available CNY balance; cannot enforce reserve")
    return cny

class Budget:
    def __init__(self, path, key, max_attempts=3000, reserve=3.0):
        self.path, self.key = Path(path), key
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            if (self.data["max_attempts"], self.data["reserve_cny"]) != (max_attempts, reserve):
                raise RuntimeError("Campaign budget configuration changed")
        else:
            b = balance(key)
            self.data = {"max_attempts": max_attempts, "reserve_cny": reserve, "initial_balance_cny": b,
                         "last_balance_cny": b, "attempts": [], "price_upper_cny_per_million": {"input": 3, "output": 9},
                         "price_source": "https://api-docs.deepseek.com/zh-cn/quick_start/pricing/"}
            atomic(self.path, self.data)

    def start(self, run_id, job, system, user, max_tokens):
        with LOCK:
            if len(self.data["attempts"]) >= self.data["max_attempts"]:
                raise RuntimeError("STOP: campaign attempt budget reached")
            b = balance(self.key)
            # Byte count is a conservative input-token bound; reserve peak prices.
            upper = ((len(system.encode()) + len(user.encode()) + 128) * 3 + max_tokens * 9) / 1e6
            pending = sum(x["reserved_cny"] for x in self.data["attempts"] if x["status"] == "started")
            if b - pending - upper < self.data["reserve_cny"]:
                raise RuntimeError("STOP: DeepSeek balance reserve reached")
            attempt = {"index": len(self.data["attempts"]), "run_id": run_id, "job": job, "status": "started",
                       "reserved_cny": upper, "balance_before_cny": b, "ts": datetime.now(timezone.utc).isoformat()}
            self.data["attempts"].append(attempt)
            self.data["last_balance_cny"] = b
            atomic(self.path, self.data)
            return attempt["index"]

    def finish(self, index, result):
        with LOCK:
            a = self.data["attempts"][index]
            a.update(status="completed", error=result.get("error"), usage=result.get("usage"))
            atomic(self.path, self.data)

def strict_json(text):
    def unique(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise ValueError("duplicate JSON key")
            d[k] = v
        return d
    return json.loads(text, object_pairs_hook=unique, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))

def summarize(rows, expected, repeats):
    done = {(r["variant"], r["id"], r["lang"], r["rep"]): r for r in rows}
    result = {"expected": expected, "completed": len(done), "coverage": len(done) / expected if expected else 0,
              "status": "complete" if len(done) == expected and all(not r["error"] for r in done.values()) else "incomplete", "variants": {}}
    def stats(rs):
        good = [r for r in rs if not r["error"]]
        rate = lambda key: sum(bool(r["score"].get(key)) for r in good) / len(good) if good else None
        lat = [r["latency"] for r in good]
        und = [r["t_und"] for r in good if r.get("t_und") is not None]
        groups = {}
        for r in good:
            groups.setdefault((r["id"], r["lang"]), []).append(r)
        complete = [g for g in groups.values() if len({r["rep"] for r in g}) == repeats and repeats >= 3]
        signatures = lambda g: {json.dumps({k:r["score"].get("parsed", {}).get(k) for k in ("intent", "conditions", "actions", "logic")}, sort_keys=True, ensure_ascii=False) for r in g}
        return {"n": len(rs), "successful": len(good), "errors": len(rs)-len(good), "pass_rate": rate("pass"),
                "strict_json_valid": rate("strict_json_valid"), "schema_valid": rate("schema_valid"), "intent_ok": rate("intent_ok"),
                "safety_violations": sum(any("安全违规" in v for v in r["score"]["violations"]) for r in good),
                "injection_action_or_memory": sum(r["cat"] == "attack" and bool((r["score"].get("parsed") or {}).get("actions") or (r["score"].get("parsed") or {}).get("memory")) for r in good),
                "latency_p50": R.pct(lat, .5), "latency_p95": R.pct(lat, .95), "understanding_p50": R.pct(und, .5),
                "input_tokens_mean": statistics.mean((r.get("usage") or {}).get("prompt_tokens", 0) for r in good) if good else None,
                "output_tokens_mean": statistics.mean((r.get("usage") or {}).get("completion_tokens", 0) for r in good) if good else None,
                "complete_repeat_groups": len(complete), "consistency": sum(len(signatures(g)) == 1 for g in complete)/len(complete) if complete else None}
    for v in sorted({r["variant"] for r in done.values()}):
        rs = [r for r in done.values() if r["variant"] == v]
        result["variants"][v] = {**stats(rs), "by_lang": {l: stats([r for r in rs if r["lang"] == l]) for l in ("zh", "en")},
                                  "by_cat": {c: stats([r for r in rs if r["cat"] == c]) for c in sorted({r["cat"] for r in rs})}}
    return result

def run(plan_path, env_file, max_new=0):
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    key = credentials(env_file)
    if plan.get("model", "deepseek-v4-flash") != "deepseek-v4-flash" or plan.get("base_url", "https://api.deepseek.com") != "https://api.deepseek.com":
        raise RuntimeError("Only the official DeepSeek V4 Flash endpoint is permitted")
    R.apply_style("p3")
    root = HERE / "results" / "prompt-lab-v3"
    out = root / plan["run_id"]
    out.mkdir(parents=True, exist_ok=True)
    prompt_texts = {v["name"]: (HERE / v["prompt"]).read_text(encoding="utf-8") for v in plan["variants"]}
    items = read_rows(HERE / plan["testset"])
    if plan.get("ids"):
        items = [i for i in items if i["id"] in plan["ids"]]
    variants = [v["name"] for v in plan["variants"]]
    jobs = [(i, lang, rep, v) for rep in range(plan["repeat"]) for i in items for lang in ("zh", "en") for v in variants]
    # Randomization is blocked by repetition. Incomplete screens can resume to triplicates.
    rng = random.Random(plan.get("seed", 20260907))
    for rep in range(plan["repeat"]):
        positions = [j for j, x in enumerate(jobs) if x[2] == rep]
        shuffled = [jobs[j] for j in positions]; rng.shuffle(shuffled)
        for j, x in zip(positions, shuffled): jobs[j] = x
    manifest = {"plan": plan, "prompt_sha256": {v: digest(t.encode()) for v,t in prompt_texts.items()},
                "items_sha256": digest(items), "files": {p: digest((HERE / p).read_bytes()) for p in
                ("safe_eval.py", "run_eval.py", "output_contract.py", "validator.py", "vocab.json", "capabilities.json", "schema.json", "requirements.txt")},
                "expected": len(jobs), "provider": "DeepSeek official", "style": "p3"}
    mp = out / "manifest.json"
    if mp.exists() and json.loads(mp.read_text(encoding="utf-8")) != manifest:
        raise RuntimeError("Manifest mismatch: use a new run_id; do not mix scores or configurations")
    atomic(mp, manifest)
    old = read_rows(out / "raw.jsonl")
    completed = {(r["id"], r["lang"], r["rep"], r["variant"]) for r in old if not r["error"]}
    jobs = [j for j in jobs if (j[0]["id"], j[1], j[2], j[3]) not in completed]
    if max_new: jobs = jobs[:max_new]
    cfg = {"base_url": "https://api.deepseek.com", "api_key": key, "model": "deepseek-v4-flash",
           "temperature": plan.get("temperature", 0), "max_tokens": plan.get("max_tokens", 1000), "timeout": 60,
           "thinking": "off", "thinking_style": "deepseek", "json_mode": plan.get("json_mode", False), "_budget_guarded": True}
    with campaign_lock(root / "campaign.lock"):
        budget = Budget(root / "campaign.json", key, plan.get("campaign_max_attempts", 3000))
        def work(job):
            item, lang, rep, variant = job
            inp = item["input_en" if lang == "en" else "input"]
            ctx = item.get("context_en" if lang == "en" else "context") or ""
            user = ctx + ("\nUser: " if lang == "en" else "\n用户：") + inp if ctx else inp
            index = budget.start(plan["run_id"], [item["id"], lang, rep, variant], prompt_texts[variant], user, cfg["max_tokens"])
            started = time.perf_counter()
            # Exactly one transport attempt. HTTP/network failures are durable and may be resumed.
            r = R._call_model_once(cfg, prompt_texts[variant], user)
            r["latency"] = time.perf_counter() - started
            budget.finish(index, r)
            obj = R.extract_json(r.get("text"))
            sc = R.score_item(dict(item, _lang=lang), obj, "p3")
            try:
                strict_json(r.get("text") or "")
                sc["strict_json_valid"] = True
            except (ValueError, TypeError):
                sc["strict_json_valid"] = False
                sc["pass"] = False
            row = {"id": item["id"], "cat": item["cat"], "lang": lang, "rep": rep, "variant": variant,
                   "input": inp, "context": ctx, "raw_text": r.get("text"), "error": r.get("error"), "usage": r.get("usage"),
                   "latency": r["latency"], "ttft": r.get("ttft"), "t_und": r.get("t_und"), "score": sc,
                   "attempt_index": index, "ts": datetime.now(timezone.utc).isoformat()}
            with LOCK:
                append(out / "raw.jsonl", row)
            return row
        rows = list(old)
        try:
            # Bounded batches avoid leaving hundreds of queued calls after a budget stop.
            concurrency = plan.get("concurrency", 3)
            with cf.ThreadPoolExecutor(max_workers=concurrency) as pool:
                for offset in range(0, len(jobs), concurrency):
                    futures = [pool.submit(work, j) for j in jobs[offset:offset+concurrency]]
                    for future in cf.as_completed(futures):
                        row = future.result(); rows.append(row)
                        print("%s %s %s r%d %s %.2fs" % (row["variant"], row["id"], row["lang"], row["rep"], "PASS" if row["score"]["pass"] else "FAIL", row["latency"]), flush=True)
                    atomic(out / "summary.json", summarize(rows, manifest["expected"], plan["repeat"]))
        finally:
            # Reload because another worker may have fsynced a response during exception handling.
            rows = read_rows(out / "raw.jsonl")
            atomic(out / "summary.json", summarize(rows, manifest["expected"], plan["repeat"]))
        final_balance = balance(key)
        budget.data["last_balance_cny"] = final_balance
        atomic(budget.path, budget.data)
        print("BALANCE_CNY %.4f; campaign attempts %d" % (final_balance, len(budget.data["attempts"])), flush=True)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--plan", required=True)
    p.add_argument("--env-file", default="")
    p.add_argument("--max-new", type=int, default=0)
    a = p.parse_args()
    run(a.plan, a.env_file, a.max_new)
