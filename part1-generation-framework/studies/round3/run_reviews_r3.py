import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import review as J
from study import HERE, rows

name = sys.argv[1]; env = sys.argv[2]
samples = json.loads((HERE / "judge" / (name + "-samples.json")).read_text(encoding="utf-8"))
out = J.run_review(name, samples, ["luna", "qwen"], env)
print(json.dumps({"run": name, "records": len(out), "errors": sum(1 for r in out if r.get("error"))}))
