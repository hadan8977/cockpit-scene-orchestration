"""Run the blind reviews with the fast judges: qwen (OpenRouter) and dsv4 (DeepSeek, Tencent proxy
with automatic failover to the official endpoint). Luna stays in the record but is not waited on."""
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
env = {}
for line in Path(sys.argv[-1]).read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); env[k.strip()] = v.strip().strip("'\"")
os.environ["JUDGE_DS_BASE_URL"] = env["DEEPSEEK_BASE_URL"]
os.environ["JUDGE_DS_KEY"] = env["DEEPSEEK_API_KEY"]
os.environ["JUDGE_DS_OFFICIAL_KEY"] = env["DEEPSEEK_OFFICIAL_API_KEY"]
import review as J
from study import HERE, sha, encoded

name = sys.argv[1]; models = sys.argv[2].split(",")
samples = json.loads((HERE / "judge" / (name + "-samples.json")).read_text(encoding="utf-8"))
out = HERE / "judge" / name
manifest = {"run": name, "sample_sha256": sha(encoded(samples)), "rubric_sha256": sha(J.RUBRIC.encode()),
            "schema": J.schema(), "models": {m: J.MODELS[m] for m in models},
            "source_sha256": sha(Path(HERE / "review.py").read_bytes().replace(b"\r\n", b"\n"))}
out.mkdir(parents=True, exist_ok=True)
(out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
res = J.run_review(name, samples, models, sys.argv[-1])
print(json.dumps({"run": name, "records": len(res), "errors": sum(1 for r in res if r.get("error"))}))
