"""Offline checks for the September 2026 repository organization and delivery."""
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
BASE = "856817d817891b328861dc712b2013320537ec29"
PART = ROOT / "part1-generation-framework"
TEXT = {".md", ".py", ".json", ".jsonl", ".txt", ".sh", ".tsv", ".html", ".log"}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def normalized(data, name):
    return data.replace(b"\r\n", b"\n") if Path(name).suffix in TEXT else data


def main():
    tracked = set(git("ls-files", "-z").decode("utf-8").split("\0")) - {""}
    errors = []
    moves = json.loads((ROOT / "archive/file-moves-2026-09-07.json").read_text(encoding="utf-8"))["moves"]
    for entry in moves:
        if entry["from"] in tracked or entry["to"] not in tracked:
            errors.append("Migration missing or old path still tracked: " + entry["from"])
        if not (ROOT / entry["to"]).is_file():
            errors.append("Missing moved file: " + entry["to"])
        # Markdown links were intentionally relocated; all other moved assets
        # retain their bytes, apart from checkout newline conversion for text.
        elif Path(entry["to"]).suffix != ".md":
            original = git("show", BASE + ":" + entry["from"])
            current = (ROOT / entry["to"]).read_bytes()
            if normalized(original, entry["from"]) != normalized(current, entry["to"]):
                errors.append("Moved asset changed: " + entry["to"])

    delivery = PART / "delivery"
    manifest = json.loads((delivery / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["assets"]:
        data = normalized((delivery / entry["file"]).read_bytes(), entry["file"])
        source = normalized((delivery / entry["source"]).read_bytes(), entry["source"])
        if data != source or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            errors.append("Delivery copy/hash mismatch: " + entry["file"])
    expected_prompt = "57488940054541ba99365f4e9521391783b42902d468ef68699ae171804d8c12"
    if manifest["assets"][0]["sha256"] != expected_prompt:
        errors.append("Frozen p13 hash changed")

    administrative = {"README.md", "make_prompt_report.py", "package_release.py", "export_cases.py", "results/prompt-lab/STATE.md"}
    preserved = 0
    for name in git("ls-tree", "-r", "--name-only", BASE, "part1-generation-framework/eval").decode("utf-8").splitlines():
        if name.removeprefix("part1-generation-framework/eval/") in administrative:
            continue
        original = git("show", BASE + ":" + name)
        file = ROOT / name
        if not file.exists() or normalized(file.read_bytes(), name) != normalized(original, name):
            errors.append("Experiment artifact changed: " + name)
        preserved += 1

    active = ["README.md", "tools/README.md", "archive/README.md", "part1-generation-framework/README.md", "part1-generation-framework/notes/README.md", "part1-generation-framework/archive/README.md", "part1-generation-framework/eval/README.md", "part1-generation-framework/eval/results/prompt-lab/STATE.md"]
    active += sorted(p for p in tracked if p.endswith(".md") and (p.startswith("docs/") or p.startswith("part1-generation-framework/delivery/") or p.startswith("part1-generation-framework/studies/round2/") or p.startswith("part1-generation-framework/runtime/")))
    link_count = 0
    for name in active:
        fenced = False
        for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            if fenced:
                continue
            for raw in re.findall(r"!?\[[^\]\n]*\]\(([^)\n]+)\)", line):
                target = raw.strip().strip("<>")
                parsed = urlsplit(target)
                if parsed.scheme or target.startswith("#"):
                    continue
                path = (ROOT / name).parent / unquote(parsed.path)
                try:
                    relative = path.resolve().relative_to(ROOT).as_posix()
                except ValueError:
                    errors.append("Link escapes repository: " + name + " -> " + target)
                    continue
                if relative not in tracked and not any(p.startswith(relative.rstrip("/") + "/") for p in tracked):
                    errors.append("Untracked/broken link: " + name + " -> " + target)
                link_count += 1

    result = {"status": "failed" if errors else "verified", "moved_files": len(moves), "frozen_experiment_files_unchanged": preserved, "delivery_assets_verified": len(manifest["assets"]), "current_document_links_checked": link_count, "new_model_calls": 0, "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
