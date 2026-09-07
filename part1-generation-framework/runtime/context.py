"""Trusted input assembly, bounded memory and transparent scene retrieval."""
import copy
import json
import re

from core import canonical, empty_scene, validate


def injection_flags(text):
    # A deterministic demonstration detector, not a complete semantic firewall.
    patterns={
        "instruction_override":r"(?i)(ignore|override|replace).{0,30}(previous|system|safety|rules)|忽略.{0,12}(规则|指令)|替换系统",
        "authority_spoof":r"(?i)(developer|maintenance|root) (mode|override)|开发者模式|维修模式|扮演车主",
        "secret_extraction":r"(?i)(reveal|print|dump).{0,25}(prompt|memory|secret)|泄露.{0,8}(提示词|记忆)|输出系统提示",
        "third_party_memory":r"(?i)(remember|记住).{0,30}(the owner|车主|别人).{0,15}(likes|喜欢)",
    }
    return [name for name,pattern in patterns.items() if re.search(pattern,text)]


def memory_pack(memories,limit=300):
    """UTF-8 bytes bound is conservative for byte-BPE; no guessed token count.

    Contracted memories are confirmed, structured records. Negatives are first.
    Large records are omitted rather than cut into a changed preference.
    """
    selected=[];dropped=[]
    items=sorted((m for m in memories if m.get("confirmed")),key=lambda m:(m.get("type")!="dislike",m.get("id","")))
    for m in items:
        item={k:m[k] for k in ("id","type","content") if k in m}
        if len(canonical(selected+[item]))<=limit:selected.append(item)
        else:dropped.append(m.get("id"))
    return {"items":selected,"utf8_bytes":len(canonical(selected)),"token_upper_bound":len(canonical(selected)),"limit":limit,"omitted_ids":dropped}


def select_existing(saved,state,utterance,limit=3):
    terms=set(re.findall(r"[a-z]+|[\u3400-\u9fff]",utterance.lower()))
    ranked=[]
    for sid,record in saved.items():
        s=record["scene"]
        text=json.dumps({k:s[k] for k in ("name","conditions","actions")},ensure_ascii=False).lower()
        overlap=len(terms&set(re.findall(r"[a-z]+|[\u3400-\u9fff]",text)))
        matches=sum(state.get(c["primary"])==c["secondary"] for c in s["conditions"])
        ranked.append((matches*10+overlap,sid,s))
    ranked.sort(key=lambda row:(-row[0],row[1]))
    return [{"id":sid,**{k:copy.deepcopy(s[k]) for k in ("name","logic","conditions","actions")},"retrieval_score":score} for score,sid,s in ranked[:limit]]


def relation_for(scene,existing):
    """Conservative exact-trigger relation; fuzzy merges always need review."""
    def signature(s):return (s.get("logic","AND"),sorted(canonical(c) for c in s.get("conditions",[])))
    if not scene.get("conditions"):return {"type":"new","scene_id":None}
    matches=[s for s in existing if signature(s)==signature(scene)]
    if len(matches)!=1:return {"type":"new","scene_id":None}
    old=matches[0];before={a["primary"]:a["secondary"] for a in old["actions"]}
    changed=any(a["primary"] in before and a["secondary"]!=before[a["primary"]] for a in scene["actions"])
    return {"type":"modify" if changed else "extend","scene_id":old["id"]}


def state_type(utterance):
    if re.search(r"(?i)累|困|冷|热|闷|tired|sleepy|cold|hot|stuffy",utterance):return "physiological"
    if re.search(r"(?i)开心|想念|难过|无聊|happy|miss|sad|bored",utterance):return "emotion"
    return "situation" if utterance.strip() else "none"


def assemble(request,engine):
    allowed={"locale","utterance","source","observation_candidate","current_proposal_id","edit_scope"}
    if not isinstance(request,dict) or set(request)-allowed:raise ValueError("Unknown request fields; vehicle state and memory come from trusted services")
    locale=request.get("locale","zh")
    if locale not in ("zh","en"):raise ValueError("locale must be zh/en")
    utterance=request.get("utterance","")
    if not isinstance(utterance,str) or len(utterance)>2000:raise ValueError("utterance must be a string of at most 2000 characters")
    source=request.get("source","explicit")
    if source not in ("explicit","state","observation","revision"):raise ValueError("Unknown source")
    snapshot=engine.registry.snapshot()
    pack=memory_pack(engine.state.get("memories",[]))
    existing=select_existing(engine.state["saved"],engine.state["vehicle"],utterance)
    flags=injection_flags(utterance)
    context={"state":copy.deepcopy(engine.state["vehicle"]),"driving":engine.context["driving"],"memory_pack":pack["items"],"existing_scenes":existing}
    flags+=injection_flags(json.dumps(context,ensure_ascii=False))
    if source=="observation":
        candidate=request.get("observation_candidate")
        # Imported candidates are never allowed to carry free-form instructions.
        if not isinstance(candidate,dict) or set(candidate)-{"name","logic","conditions","actions","evidence"}:raise ValueError("Invalid observation candidate")
        flags+=injection_flags(json.dumps(candidate,ensure_ascii=False))
        raw={**empty_scene(),"name":candidate.get("name","观察"),"intent":"observation","relevance":.9,**{k:candidate[k] for k in ("logic","conditions","actions") if k in candidate}}
        checked=validate(raw,snapshot,engine.context,engine.state["saved"])
        if not checked["valid"]:raise ValueError("Observation candidate rejected before model generation")
        context["observation_candidate"]=candidate
    previous=None
    if source=="revision":
        previous=engine.proposals.get(request.get("current_proposal_id"))
        if not previous or previous["status"]!="pending":raise ValueError("Revision requires a pending proposal")
        if not request.get("edit_scope"):raise ValueError("Revision requires explicit action scope")
        context["current_scene"]=previous["raw"];context["edit_scope"]=request["edit_scope"]
    return {"locale":locale,"utterance":utterance,"context":json.dumps(context,ensure_ascii=False,separators=(",",":"))}, {"source":source,"memory":pack,"existing_scenes":existing,"injection_flags":flags,"state_type":state_type(utterance),"previous":previous}
