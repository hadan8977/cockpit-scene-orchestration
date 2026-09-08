import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
env = {}
for line in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); env[k.strip()] = v.strip().strip("'\"")
os.environ["JUDGE_DS_BASE_URL"] = env["DEEPSEEK_BASE_URL"]
os.environ["JUDGE_DS_KEY"] = env["DEEPSEEK_API_KEY"]
import review as J
from study import HERE
name = sys.argv[1]
samples = json.loads((HERE / "judge" / (name + "-samples.json")).read_text(encoding="utf-8"))
out = J.run_review(name + "-dsv4", samples, ["dsv4"], sys.argv[2])
print(json.dumps({"run": name + "-dsv4", "records": len(out), "errors": sum(1 for r in out if r.get("error"))}))
