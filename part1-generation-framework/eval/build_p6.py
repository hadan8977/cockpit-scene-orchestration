"""Build matched prompt languages and one-component ablations from the same registry."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent

def build(lang, remove=()):
    blocks=json.loads((HERE/"prompts"/("p6_%s_blocks.json"%lang)).read_text(encoding="utf-8"))
    vocab=json.loads((HERE/"vocab.json").read_text(encoding="utf-8"))
    parts=["["+k+"]\n"+v for k,v in blocks.items() if k not in remove]
    for kind in ("conditions","actions"):
        groups={}
        for name,values in vocab[kind].items():
            meta=vocab["meta"][kind].get(name,{})
            maturity=meta.get("maturity","released") if kind=="actions" else ""
            key=(json.dumps(values,ensure_ascii=False,separators=(",",":")),maturity)
            groups.setdefault(key,[]).append(name)
        parts.append("["+kind+" dictionary; names=values; maturity applies to actions]")
        for (value,maturity),names in groups.items():
            parts.append("、".join(names)+"="+value+(" ["+maturity+"]" if maturity else ""))
    parts.append("[typed payloads]\n生效时间=HH:MM; 指定日期=YYYYMMDD; 日期区间=YYYYMMDD-YYYYMMDD; 生效时间段=HH:MM-HH:MM; 播放指定音乐=actual song name; 壁纸/主题=actual name. 小塔播报=自定义内容 uses say. Values marked range=[min,max,step,unit].")
    return "\n\n".join(parts)+"\n"

if __name__=="__main__":
    for lang in ("zh","en"):
        (HERE/"prompts"/("p6_%s.md"%lang)).write_text(build(lang),encoding="utf-8")
