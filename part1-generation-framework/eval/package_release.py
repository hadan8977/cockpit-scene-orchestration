"""Build a portable, credential-free prompt and evidence package from tracked files."""
import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parent.parent

def main(out_path):
    freeze=json.loads((HERE/'experiments'/'RELEASE_FREEZE.json').read_text(encoding='utf-8'))
    report=HERE.parent/'docs'/'第一部分-Prompt优化-最终实验报告.md'
    assert report.exists(),'Final report is required'
    verification=json.loads((HERE/'results'/'prompt-lab-v3'/'evidence-verification.json').read_text(encoding='utf-8'))
    assert verification['status']=='verified'
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=REPO).decode('utf-8').split('\0')
    docs={str(p.relative_to(REPO)).replace('\\','/') for p in (report,HERE.parent/'docs'/'第一部分-Prompt接入说明.md',HERE.parent/'docs'/'第一部分-进度看板.md')}
    names=[p for p in tracked if p.startswith('part1-generation-framework/eval/') or p in docs]
    out=Path(out_path).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    hashes={}
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name in sorted(names):
            assert not any(part in ('.env','__pycache__') for part in Path(name).parts),name
            data=(REPO/name).read_bytes()
            if Path(name).suffix in ('.md','.py','.json','.jsonl','.txt'):
                data=data.replace(b'\r\n',b'\n')
            hashes[name]=hashlib.sha256(data).hexdigest()
            archive.writestr(name,data)
        readme=('DeepSeek V4 Flash prompt study\n\n'
                'Start with part1-generation-framework/docs/第一部分-Prompt优化-最终实验报告.md\n'
                'Prompt: part1-generation-framework/eval/'+freeze['prompt_path']+'\n'
                'Parameters and language policy: eval/experiments/RELEASE_FREEZE.json\n'
                'Evidence: compressed raw responses, manifests, summaries and analysis source.\n'
                'Historical rejected/partial runs are retained and labeled.\n'
                'Recomputing archived results is offline; new model calls require your own credentials and budget.\n'
                'No API credentials are included. Remote upload status is in the progress board.\n')
        archive.writestr('START-HERE.txt',readme.encode('utf-8'))
        archive.writestr('SHA256SUMS.json',json.dumps(hashes,ensure_ascii=False,indent=2).encode('utf-8'))
    # Read every member back and check against the generated manifest.
    with zipfile.ZipFile(out) as archive:
        for name,sha in hashes.items():assert hashlib.sha256(archive.read(name)).hexdigest()==sha,name
    print('Packaged',len(hashes),'tracked files:',out)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();main(a.out)
