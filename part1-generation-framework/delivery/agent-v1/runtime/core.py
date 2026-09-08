"""Versioned registry, generated constraints, fail-closed validation and simulation."""
import copy
import hashlib
import json
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

PART = Path(__file__).resolve().parent.parent
RELEASED = {"released", "no_ux"}
IMMATURE = {"planned", "sprint", "proposed"}
FIELDS = ["understanding", "relevance", "intent", "name", "logic", "conditions", "actions", "say", "offer", "memory", "unsupported", "warnings", "clarify"]


def canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
def digest(value): return hashlib.sha256(canonical(value)).hexdigest()
def utc(): return datetime.now(timezone.utc).isoformat()


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_bytes(canonical(data) + b"\n")
    temp.replace(path)


class Conflict(ValueError): pass


class Registry:
    """All constraints for one generation come from a single immutable snapshot."""
    def __init__(self, source=None, storage=None):
        self.lock = threading.RLock()
        self.storage = Path(storage) if storage else None
        source = Path(source or PART / "eval/capabilities.json")
        self.base = json.loads(source.read_text(encoding="utf-8"))
        state = self.storage / "registry.json" if self.storage else None
        self.data = json.loads(state.read_text(encoding="utf-8")) if state and state.exists() else copy.deepcopy(self.base)
        self._check(self.data)

    @staticmethod
    def _check(data):
        ids = [c["id"] for c in data["capabilities"]]
        names = [c["zh"] for c in data["capabilities"]]
        if len(ids) != len(set(ids)) or len(names) != len(set(names)): raise ValueError("Duplicate registry id/name")
        for c in data["capabilities"]:
            if c["status"] not in ("enabled", "disabled"): raise ValueError("Invalid status")

    def snapshot(self):
        with self.lock:
            data = copy.deepcopy(self.data)
            semantic = [{k:c.get(k) for k in ("id","zh","class","status","maturity","cond_values","act_values","deny_act_values")} for c in data["capabilities"]]
            return {"version":data["version"], "revision":digest({"generation":data.get("runtime_generation",0),"capabilities":semantic}), "capabilities":data["capabilities"]}

    def set_enabled(self, capability_id, enabled, expected_revision):
        with self.lock:
            old = self.snapshot()
            if old["revision"] != expected_revision: raise Conflict("Registry changed; refresh before editing")
            cap = next((c for c in self.data["capabilities"] if c["id"] == capability_id), None)
            if cap is None: raise ValueError("Unknown capability id")
            if not isinstance(enabled,bool): raise ValueError("enabled must be boolean")
            cap["status"] = "enabled" if enabled else "disabled"
            self.data["runtime_generation"] = self.data.get("runtime_generation",0)+1
            if self.storage: atomic(self.storage/"registry.json",self.data)
            return self.snapshot()


def value_schema(cap, kind):
    values = cap["cond_values" if kind=="conditions" else "act_values"]
    name=cap["zh"]
    if isinstance(values,dict) and "range" in values:
        lo,hi,step,unit=values["range"]
        if name=="生效时间": return {"type":"string","pattern":r"^([01]\d|2[0-3]):[0-5]\d(?::00)?$"}
        return {"type":"string","enum":[f"{lo+i*step:g}{unit}" for i in range(round((hi-lo)/step)+1)]}
    allowed=list(values)
    if kind=="actions":
        denied=cap.get("deny_act_values",[])+(["关闭"] if cap["id"]=="safety.avas" else [])
        allowed=[v for v in allowed if v not in denied]
    patterns={"指定日期":r"^\d{8}$","日期区间":r"^\d{8}-\d{8}$","生效时间段":r"^(全天|([01]\d|2[0-3]):[0-5]\d-([01]\d|2[0-3]):[0-5]\d)$"}
    if name in patterns: return {"type":"string","pattern":patterns[name]}
    if name in ("播放指定音乐","壁纸","主题"): return {"type":"string","minLength":1,"maxLength":80,"pattern":r"^[^\r\n]+$"}
    return {"type":"string","enum":allowed}


def _schema_path():
    """按契约切换并支持自包含交付包：优先包内 contract/，回落到仓库 eval/。"""
    import os
    name="schema_v4.json" if os.environ.get("SCENE_CONTRACT","v3")!="v3" else "schema.json"
    for p in (PART/"contract/scene.schema.json", PART/"eval"/name, PART/"eval/schema.json"):
        if p.exists(): return p
    raise FileNotFoundError("No output schema found near %s"%PART)


def output_schema(snapshot):
    schema=json.loads(_schema_path().read_text(encoding="utf-8"))
    for kind,field in (("conditions","cond_values"),("actions","act_values")):
        options=[]
        for c in snapshot["capabilities"]:
            if c["status"]!="enabled" or not c.get(field): continue
            props={"primary":{"const":c["zh"]},"secondary":value_schema(c,kind)}
            if kind=="conditions": props["op"]={"enum":["==","<","<=",">",">="] if isinstance(c[field],dict) else ["=="]}
            options.append({"type":"object","properties":props,"required":list(props),"additionalProperties":False})
        schema["properties"][kind]["items"]={"oneOf":options} if options else False
    schema["properties"]["relation"]={"type":"object","properties":{"type":{"enum":["new","extend","modify"]},"scene_id":{"type":["string","null"]}},"required":["type","scene_id"],"additionalProperties":False}
    schema["properties"]["state_type"]={"enum":["situation","emotion","physiological","none"]}
    for field in ("offer",):
        schema["properties"][field]["additionalProperties"]=False
        schema["properties"][field]["required"]=list(schema["properties"][field]["properties"])
    schema["properties"]["memory"]["items"]["additionalProperties"]=False
    return schema


def dictionary(snapshot):
    compact=[]
    for kind,field in (("conditions","cond_values"),("actions","act_values")):
        compact.append("["+kind+": primary = values; * = 未落地，需warnings]")
        groups={}
        for c in snapshot["capabilities"]:
            if c["status"]!="enabled" or not c.get(field):continue
            vals=c[field]
            if kind=="actions" and isinstance(vals,list): vals=[v for v in vals if v not in c.get("deny_act_values",[]) and not(c["id"]=="safety.avas" and v=="关闭")]
            key=(json.dumps(vals,ensure_ascii=False,separators=(",",":")),kind=="actions" and c.get("maturity") in IMMATURE)
            groups.setdefault(key,[]).append(c["zh"])
        compact += ["、".join(names)+("*" if star else "")+"="+values for (values,star),names in groups.items()]
    compact.append("范围对象range=[最小,最大,步长,单位]。生效时间=HH:MM；生效时间段=全天或HH:MM-HH:MM；指定日期=YYYYMMDD；日期区间=YYYYMMDD-YYYYMMDD；播放指定音乐/壁纸/主题的自定义项填写真实名称；小塔播报自定义内容填say。占位词不是真实值。")
    return "\n".join(compact)+"\n"


def compile_prompt(snapshot, template):
    source=Path(template).read_text(encoding="utf-8")
    marker="[conditions: primary = values; * = 未落地，需warnings]"
    verbose="[CONDITIONS ONLY; * means planned/proposed/sprint ACTION requiring a named warning]"
    flat="[CONDITIONS ONLY]"
    if flat in source and verbose not in source and "[examples]" in source:
        # 第三轮起能力表不再分成熟度，表头去掉了星号图例
        flat_actions="[ACTIONS ONLY]"
        before,remaining=source.split(flat,1)
        previous_table,after=remaining.split("[examples]",1)
        parts=previous_table.split(flat_actions)
        order={kind:[n for line in part.splitlines() if " = " in line for n in line.split(" = ",1)[0].lstrip("*").split("、")] for kind,part in zip(("conditions","actions"),parts)}
        table=verbose_dictionary(snapshot,order)
        table=table.replace(verbose,flat).replace("[ACTIONS ONLY; * means planned/proposed/sprint ACTION requiring a named warning]",flat_actions)
        lines=[];groups={}
        def flush():
            lines.extend("、".join(names)+" = "+values for values,names in groups.items());groups.clear()
        for line in table.splitlines():
            if " = " not in line:
                flush();lines.append(line);continue
            left,values=line.split(" = ",1)
            groups.setdefault(values,[]).append(left.lstrip("*"))
        flush()
        # 模板里的能力表已由同一份注册表渲染过。这里只核对能力名集合是否仍然一致，
        # 一致就原样返回被评测过的那份 prompt，不重新渲染；不一致说明注册表漂移了，直接拒绝。
        rendered={k:set(v) for k,v in order.items()}
        live={"conditions":{c["zh"] for c in snapshot["capabilities"] if c["status"]=="enabled" and c.get("cond_values")},
              "actions":{c["zh"] for c in snapshot["capabilities"] if c["status"]=="enabled" and c.get("act_values")}}
        for kind in ("conditions","actions"):
            if rendered[kind]!=live[kind]:
                raise Conflict("Prompt table drifted from registry: %s missing=%s extra=%s"%(
                    kind,sorted(live[kind]-rendered[kind])[:5],sorted(rendered[kind]-live[kind])[:5]))
        return source,{"registry_revision":snapshot["revision"],"prompt_sha256":hashlib.sha256(source.encode()).hexdigest(),"schema_sha256":digest(output_schema(snapshot)),"table":"verified-in-place"}
    if marker in source:
        prompt=source.split(marker,1)[0]+dictionary(snapshot)
    elif verbose in source and "[examples]" in source:
        before,remaining=source.split(verbose,1)
        previous_table,after=remaining.split("[examples]",1)
        parts=previous_table.split("[ACTIONS ONLY; * means planned/proposed/sprint ACTION requiring a named warning]")
        order={kind:[name for line in part.splitlines() if " = " in line for name in line.split(" = ",1)[0].lstrip("*").split("、")] for kind,part in zip(("conditions","actions"),parts)}
        grouped=any("、" in line.split(" = ",1)[0] for line in previous_table.splitlines() if " = " in line)
        table=verbose_dictionary(snapshot,order)
        if grouped:
            grouped_lines=[];groups={}
            def flush_groups():
                grouped_lines.extend(("*" if star else "")+"、".join(names)+" = "+values for (values,star),names in groups.items());groups.clear()
            for line in table.splitlines():
                if " = " not in line:
                    flush_groups();grouped_lines.append(line);continue
                left,values=line.split(" = ",1);star=left.startswith("*")
                groups.setdefault((values,star),[]).append(left.lstrip("*"))
            flush_groups();table="\n".join(grouped_lines)+"\n"
        prompt=before+table+"[examples]"+after
    else: raise ValueError("Template has no replaceable registry section")
    return prompt,{"registry_revision":snapshot["revision"],"prompt_sha256":hashlib.sha256(prompt.encode()).hexdigest(),"schema_sha256":digest(output_schema(snapshot))}


def verbose_dictionary(snapshot,order=None):
    """Keep the evaluated p13/p16 layout, regenerated from the live registry."""
    parts=[]
    for kind,field in (("conditions","cond_values"),("actions","act_values")):
        parts.append("["+kind.upper()+" ONLY; * means planned/proposed/sprint ACTION requiring a named warning]")
        capabilities=snapshot["capabilities"]
        if order:
            positions={name:i for i,name in enumerate(order[kind])}
            capabilities=sorted(capabilities,key=lambda c:positions.get(c["zh"],len(positions)))
        for c in capabilities:
            if c["status"]!="enabled" or not c.get(field):continue
            name,spec=c["zh"],c[field]
            if isinstance(spec,dict):
                lo,hi,step,unit=spec["range"]
                val="/".join(str(n)+unit for n in range(lo,hi+1,step)) if kind=="actions" else "%s%s..%s%s; step %s%s"%(lo,unit,hi,unit,step,unit)
            else:
                vals=spec if kind=="conditions" else [v for v in spec if v not in c.get("deny_act_values",[]) and not(c["id"]=="safety.avas" and v=="关闭")]
                val="/".join(vals)
            special={"生效时间":"HH:MM (00:00..23:59)","指定日期":"YYYYMMDD","日期区间":"YYYYMMDD-YYYYMMDD","生效时间段":"全天/HH:MM-HH:MM","播放指定音乐":"actual song title / 实际歌名","壁纸":"actual name / 实际名称","主题":"actual name / 实际名称","延时":"1秒..600秒, step 1秒"}
            val=special.get(name,val)
            flag="*" if kind=="actions" and c.get("maturity") in IMMATURE else ""
            parts.append(flag+name+" = "+val)
    return "\n".join(parts)+"\n"


def strict_tool_schema(snapshot):
    """DeepSeek strict tool subset. External validator remains authoritative."""
    def convert(value):
        if isinstance(value,list):return [convert(x) for x in value]
        if not isinstance(value,dict):return value
        result={k:convert(v) for k,v in value.items() if k not in ("$schema","title")}
        if "const" in result:result["enum"]=[result.pop("const")]
        if "oneOf" in result:result["anyOf"]=result.pop("oneOf")
        if isinstance(result.get("type"),list):
            types=result.pop("type");result["anyOf"]=[{"type":t} for t in types]
        if result.get("type")=="object":
            result["required"]=list(result["properties"]);result["additionalProperties"]=False
        if "enum" in result and "type" not in result:result["type"]="string"
        return result
    return convert(output_schema(snapshot))


def _typed_value(cap,kind,value):
    values=cap["cond_values" if kind=="conditions" else "act_values"]
    if not isinstance(value,str):return False
    name=cap["zh"]
    if name=="生效时间":return bool(re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d(?::00)?",value))
    if isinstance(values,dict):
        lo,hi,step,unit=values["range"]
        m=re.fullmatch(r"(-?\d+(?:\.\d+)?)"+re.escape(unit),value)
        if not m:return False
        n=float(m[1]);return lo<=n<=hi and abs((n-lo)/step-round((n-lo)/step))<1e-8
    if name in ("指定日期","日期区间"):
        try:
            parts=value.split("-")
            if len(parts)!=(2 if name=="日期区间" else 1):return False
            dates=[datetime.strptime(x,"%Y%m%d") for x in parts if re.fullmatch(r"\d{8}",x)]
            return len(dates)==len(parts) and dates==sorted(dates)
        except ValueError:return False
    if name=="生效时间段":return bool(re.fullmatch(r"全天|([01]\d|2[0-3]):[0-5]\d-([01]\d|2[0-3]):[0-5]\d",value))
    if name in ("播放指定音乐","壁纸","主题"):
        return 0<len(value)<=80 and value not in ("自定义","歌曲名","选择壁纸","主题名") and "\n" not in value
    return value in values


def driving_issue(cap,value):
    name=cap["zh"]
    if cap["id"].startswith("window.") and value not in ("关闭","10%","20%"):return "行驶中车窗最多20%"
    if name=="氛围灯亮度" and int(value.rstrip("%"))>50:return "行驶中氛围灯亮度最多50%"
    if name=="音乐律动" and value!="关闭":return "行驶中音乐律动必须关闭"
    if cap["id"].startswith("door.") and value!="关闭":return "行驶中不开车门"
    if cap["id"]=="nav.destination":return "行驶中不更换导航目的地"
    if cap["id"].startswith("app.") and value not in ("关闭","停止","退出"):return "行驶中不打开视频或K歌"
    if cap["id"] in ("preset.enter","preset.exit"):return "行驶中不切换整车模式"
    return None


def empty_scene(locale="zh",message=""):
    return {"understanding":message,"relevance":0,"intent":"none","name":"","logic":"AND","conditions":[],"actions":[],"say":"","offer":{"type":"none","target":""},"memory":[],"unsupported":[],"warnings":[],"clarify":None}


def validate(raw,snapshot,context=None,existing_ids=()):
    """Never discard a condition to make a rejected rule executable."""
    context=context or {}
    decisions=[]
    def reject(code,message,capability=None):decisions.append({"status":"blocked","code":code,"reason":message,"capability":capability})
    if not isinstance(raw,dict):return {"valid":False,"savable":False,"executable":False,"scene":empty_scene(),"decisions":[{"status":"blocked","code":"structure","reason":"Output must be a JSON object"}]}
    errors=list(Draft202012Validator(output_schema(snapshot)).iter_errors(raw))
    if errors:reject("structure","JSON structure or capability enumeration is invalid")
    # 契约长度按语言把关：Schema 只能设一个上界，中文的更严格，在这里补
    _han=lambda t:any("\u4e00"<=ch<="\u9fff" for ch in t)
    for field,zh_max,en_max in (("understanding",120,200),("say",30,60),("name",14,14)):
        text=raw.get(field)
        if not isinstance(text,str) or not text:continue
        limit=zh_max if _han(text) else en_max
        if len(text)>limit:
            reject("contract_length","%s 超长：%d 字符 > %d"%(field,len(text),limit))
    by_name={c["zh"]:c for c in snapshot["capabilities"]}
    immature=[]
    for kind,field in (("conditions","cond_values"),("actions","act_values")):
        entries=raw.get(kind,[])
        if not isinstance(entries,list):continue
        seen=set()
        for entry in entries:
            if not isinstance(entry,dict):continue
            name,value=entry.get("primary"),entry.get("secondary")
            cap=by_name.get(name) if isinstance(name,str) else None
            if cap is None:reject("unknown_capability","能力不在注册表",name);continue
            if cap["status"]!="enabled":reject("disabled","能力已下线",name)
            if not cap.get(field) or not _typed_value(cap,kind,value):reject("invalid_value","值域、单位、步长或日期不合法",name);continue
            identity=(name,entry.get("op"),value) if kind=="conditions" else name
            if identity in seen and name!="延时":reject("duplicate","重复条件或动作",name)
            seen.add(identity)
            if kind=="actions":
                if value in cap.get("deny_act_values",[]) or (cap["id"]=="safety.avas" and value=="关闭"):reject("forbidden","安全功能禁止关闭",name)
                if context.get("driving"):
                    issue=driving_issue(cap,value)
                    if issue:reject("driving_policy",issue,name)
                if cap.get("maturity") not in RELEASED:
                    immature.append(name)
                    decisions.append({"status":"planned","code":"maturity","capability":name,"reason":"仅供概念提案，不执行未落地能力"})
                else:decisions.append({"status":"accepted","capability":name,"reason":"通过当前注册表与值域校验"})
    actions=raw.get("actions") if isinstance(raw.get("actions"),list) else []
    conditions=raw.get("conditions") if isinstance(raw.get("conditions"),list) else []
    if len(immature)>1:reject("maturity_count","一条提案最多一个未落地动作")
    if raw.get("intent") in ("none","clarify") and (actions or conditions):reject("non_action_intent","拒绝或追问不得携带可执行条件/动作")
    if raw.get("intent") in ("vague","affect") and len(actions)>4:reject("action_count","舒适/情绪提案最多4个动作")
    if sum(isinstance(a,dict) and a.get("primary")=="延时" for a in actions)>2:reject("delay_count","最多两段延时")
    if len(conditions)==1 and isinstance(conditions[0],dict):
        c=conditions[0]
        for a in actions:
            if isinstance(a,dict) and a.get("primary")==c.get("primary") and (c.get("secondary"),a.get("secondary")) in (("开启","关闭"),("关闭","开启")):
                reject("self_inverting","唯一条件与动作为同一能力的相反状态")
    relation=raw.get("relation")
    if isinstance(relation,dict):
        if relation.get("type") in ("extend","modify") and relation.get("scene_id") not in existing_ids:reject("unknown_scene_reference","并入目标场景不存在")
        if relation.get("type")=="new" and relation.get("scene_id") is not None:reject("invalid_scene_reference","新建不能引用已有场景id")
    if raw.get("intent") not in ("none","clarify") and not raw.get("name"):reject("missing_name","可呈现场景必须有名称")
    if context.get("injection_flags"):reject("injection","输入有指令注入标记，不执行其任何片段")
    for a in actions:
        if not isinstance(a,dict):continue
        for denial in context.get("denied_actions",[]):
            if a.get("primary")==denial.get("primary") and a.get("secondary") not in denial.get("except",[]) and (denial.get("secondary") is None or a.get("secondary")==denial["secondary"]):
                reject("negative_preference","动作违反已确认的负面偏好",a.get("primary"))
    valid=not any(d["status"]=="blocked" for d in decisions)
    # Preserve the complete proposal for explaining rejection; no executable sub-scene.
    return {"valid":valid,"savable":valid and raw.get("intent") not in ("none","clarify") and bool(actions or conditions),"executable":valid and bool(actions) and not immature and raw.get("intent") not in ("none","clarify"),"scene":copy.deepcopy(raw),"decisions":decisions,"registry_revision":snapshot["revision"]}


def revision(previous,delta,scope):
    """Apply only explicitly scoped action changes; unrelated state is immutable."""
    if not scope or not set(scope).issubset({a["primary"] for a in previous["actions"]}):raise ValueError("Choose existing actions to revise")
    if delta.get("clarify"):return {**copy.deepcopy(previous),"clarify":delta["clarify"]}
    changes=delta.get("actions",[])
    if not changes or any(a.get("primary") not in scope for a in changes):raise ValueError("Revision escaped the selected scope")
    if delta.get("conditions") and delta["conditions"]!=previous["conditions"]:raise ValueError("Action revision cannot change conditions")
    result=copy.deepcopy(previous)
    update={a["primary"]:a for a in changes}
    result["actions"]=[copy.deepcopy(update.get(a["primary"],a)) for a in previous["actions"]]
    result["understanding"]=delta["understanding"]
    return result


class Engine:
    """Explicit confirmation and versioned simulation; no real vehicle adapter."""
    def __init__(self,registry,storage=None,clock=time.monotonic):
        self.registry=registry;self.clock=clock;self.lock=threading.RLock()
        self.storage=Path(storage) if storage else None
        file=self.storage/"state.json" if self.storage else None
        self.state=json.loads(file.read_text(encoding="utf-8")) if file and file.exists() else {"vehicle":{},"saved":{},"audit":[],"last_execution":None}
        self.proposals={}
        self.context={"driving":False}

    def _persist(self):
        if self.storage:atomic(self.storage/"state.json",self.state)

    def propose(self,raw,provenance,request_id=None):
        with self.lock:
            snapshot=self.registry.snapshot()
            if provenance.get("registry_revision",snapshot["revision"])!=snapshot["revision"]:raise Conflict("Registry changed during generation")
            result=validate(raw,snapshot,{**self.context,"injection_flags":provenance.get("injection_flags",[])},self.state["saved"])
            pid=request_id or uuid.uuid4().hex
            if pid in self.proposals:raise Conflict("Duplicate proposal id")
            self.proposals[pid]={"raw":copy.deepcopy(raw),"provenance":provenance,"created":self.clock(),"status":"pending","revision":snapshot["revision"]}
            return {"proposal_id":pid,"status":"ready" if result["valid"] else "rejected",**result,"provenance":provenance,"executed":False,"trace":[{"layer":"registry","revision":snapshot["revision"]},{"layer":"structure","status":"pass" if result["valid"] else "inspect_decisions"},{"layer":"validator","decisions":result["decisions"]},{"layer":"execution","status":"awaiting_user_confirmation"}]}

    def confirm(self,pid,operation,expected_revision):
        with self.lock,self.registry.lock:
            p=self.proposals.get(pid)
            if not p or (p["status"]!="pending" and not(operation=="save" and p["status"]=="applied")):raise Conflict("Proposal missing or already handled")
            if self.clock()-p["created"]>300:raise Conflict("Proposal expired")
            if expected_revision!=p["revision"]:raise Conflict("Client proposal version mismatch")
            snapshot=self.registry.snapshot()
            # Revalidate under the latest registry and trusted vehicle state.
            result=validate(p["raw"],snapshot,{**self.context,"injection_flags":p["provenance"].get("injection_flags",[])},self.state["saved"])
            if snapshot["revision"]!=p["revision"]:
                raise Conflict("Registry changed: regenerate and confirm the updated proposal")
            if operation not in ("save","apply_once","reject"):raise ValueError("Invalid operation")
            if operation=="reject":p["status"]="rejected"
            elif operation=="save":
                if not result["savable"]:raise ValueError("Proposal is not savable")
                self.state["saved"][pid]={"id":pid,"scene":copy.deepcopy(p["raw"]),"registry_revision":snapshot["revision"]}
                p["status"]="saved_after_apply" if p["status"]=="applied" else "saved"
            else:
                if not result["executable"]:raise ValueError("Proposal cannot be executed in this state")
                if p["raw"]["conditions"]:raise ValueError("Conditional rules must be saved; cannot silently execute now")
                if any(a["primary"]=="延时" for a in p["raw"]["actions"]):raise ValueError("Timed actions need a scheduler; not executed synchronously")
                before=copy.deepcopy(self.state["vehicle"])
                for a in p["raw"]["actions"]:self.state["vehicle"][a["primary"]]=a["secondary"]
                self.state["last_execution"]={"id":pid,"before":before,"after":copy.deepcopy(self.state["vehicle"]),"restored":False}
                p["status"]="applied"
            event={"proposal_id":pid,"operation":operation,"at":utc(),"registry_revision":snapshot["revision"],"simulation":True,"executed":operation=="apply_once"}
            self.state["audit"].append(event);self._persist()
            return {**event,"status":p["status"]}

    def restore(self,pid):
        with self.lock:
            last=self.state["last_execution"]
            if not last or last["id"]!=pid or last["restored"]:raise Conflict("Only the latest active simulation can be restored once")
            if self.state["vehicle"]!=last["after"]:raise Conflict("Vehicle changed after simulation")
            self.state["vehicle"]=copy.deepcopy(last["before"]);last["restored"]=True
            self.state["audit"].append({"operation":"restore","proposal_id":pid,"at":utc(),"simulation":True});self._persist()
            return {"restored":True,"vehicle":copy.deepcopy(self.state["vehicle"])}
