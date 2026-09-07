#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""场景编排模型评测 harness（OpenAI 兼容 chat/completions 接口）。

真跑示例（DeepSeek V4 Flash，非思考，中英双语全题，重复 3 次，json 模式）：
  EVAL_BASE_URL=https://api.deepseek.com EVAL_API_KEY=sk-xxx EVAL_MODEL=deepseek-v4-flash \
    python3 run_eval.py --prompt prompts/p3_grammar.md --thinking off --lang both --repeat 3 --json-mode --tag v4flash-p3
本地小模型（llama.cpp server 或 vLLM 的 OpenAI 兼容接口，评估端侧路线）：
  EVAL_BASE_URL=http://127.0.0.1:8080/v1 EVAL_API_KEY=x EVAL_MODEL=qwen3-1.7b \
    python3 run_eval.py --prompt prompts/p3_grammar.md --thinking none --lang both --tag local-qwen3-1.7b
离线自检：
  python3 run_eval.py --mock --mock-style p3 ; python3 run_eval.py --mock-noise --mock-style p3
输出：results/<tag>/raw.jsonl（每次调用一行）、summary.md、summary.json
"""
import argparse, json, os, re, sys, time, random, statistics
import concurrent.futures as cf
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
VOCAB = json.load(open(os.path.join(HERE, "vocab.json"), encoding="utf-8"))
BOOL_PAIRS = {("开启", "关闭"), ("关闭", "开启"), ("有人", "无人"), ("无人", "有人"), ("内循环", "外循环"), ("外循环", "内循环")}
OFFER_TYPES = {"call", "navigate", "message", "none"}
MEMORY_TYPES = {"preference", "relationship", "place", "dislike"}
PRESETS = None

def _norm_key(s):
    return re.sub(r"\s+", "", str(s).strip().replace("档", "挡")).lower()
PRIM = {k: {_norm_key(p): p for p in VOCAB[k]} for k in ("conditions", "actions")}

def apply_style(style):
    """p2/p3 风格启用扩展能力（音乐播放、音量），并加载预设用于坍缩率。"""
    global PRIM, PRESETS
    if style in ("p2", "p3") and "extensions_p2" in VOCAB:
        VOCAB["actions"].update(VOCAB["extensions_p2"]["actions"])
        if style == "p3" and "extensions_p3" in VOCAB:
            VOCAB["conditions"].update(VOCAB["extensions_p3"]["conditions"])
        PRIM = {k: {_norm_key(p): p for p in VOCAB[k]} for k in ("conditions", "actions")}
        pp = os.path.join(HERE, "presets.json")
        if os.path.exists(pp):
            PRESETS = []
            for pr in json.load(open(pp, encoding="utf-8"))["presets"]:
                s = set()
                for p, v in pr["actions"]:
                    ok, nv = value_ok("actions", p, v)
                    s.add((p, str(nv)))
                PRESETS.append((pr["name"], s))

# ---------------- 归一化 ----------------
def norm_text(s):
    s = str(s).strip()
    for a, b in [("档", "挡"), ("°C", "℃"), ("摄氏度", "℃"), ("ug/m3", "μg/m³"), ("µg/m³", "μg/m³"), ("μg/m3", "μg/m³"),
                 ("km/h", "KM/小时"), ("KM/H", "KM/小时"), ("Km/h", "KM/小时"), ("km/小时", "KM/小时"), ("公里/小时", "KM/小时"),
                 ("公里每小时", "KM/小时"), ("百分之", "")]:
        s = s.replace(a, b)
    return re.sub(r"\s+", "", s)

NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
def to_num(s):
    m = NUM_RE.search(str(s))
    return float(m.group()) if m else None

def is_range_spec(spec):
    return isinstance(spec, dict) and "range" in spec

def unit_of(kind, primary):
    spec = VOCAB[kind].get(primary)
    return spec["range"][3] if is_range_spec(spec) else ""

def value_ok(kind, primary, secondary):
    table = VOCAB[kind]
    if primary not in table:
        return False, None
    spec = table[primary]
    s = norm_text(secondary)
    if is_range_spec(spec):
        lo, hi, step, unit = spec["range"]
        n = to_num(s)
        return (n is not None and lo <= n <= hi), n
    allowed = [norm_text(a) for a in spec]
    if s in allowed:
        return True, s
    n = to_num(s)
    if n is not None:
        for a in allowed:
            an = to_num(a)
            if an is not None and an == n and (a.endswith("%") or a.endswith("挡")):
                return True, a
    return False, s

OP_MAP = {"==": "==", "=": "==", "等于": "==", "<": "<", "小于": "<", "低于": "<", "<=": "<=", "≤": "<=", "小于等于": "<=",
          ">": ">", "大于": ">", "高于": ">", "超过": ">", ">=": ">=", "≥": ">=", "大于等于": ">=", "!=": "!=", "≠": "!="}
def norm_op(op):
    return None if op is None else OP_MAP.get(str(op).strip(), str(op).strip())

# ---------------- 解析模型输出 ----------------
def extract_json(text):
    if text is None:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    i, j = t.find("{"), t.rfind("}")
    if i >= 0 and j > i:
        try:
            return json.loads(t[i:j + 1])
        except Exception:
            return None
    return None

def parse_output(obj):
    out = {"intent": None, "conditions": [], "actions": [], "name": "", "clarify": None, "logic": None, "schema_errors": [],
           "say": "", "offer": None, "understanding": "", "relevance": None, "memory": []}
    if not isinstance(obj, dict):
        out["schema_errors"].append("不是 JSON 对象")
        return out
    out["name"] = str(obj.get("name") or "")
    out["clarify"] = obj.get("clarify") or None
    out["logic"] = obj.get("logic")
    out["say"] = str(obj.get("say") or "")
    out["offer"] = obj.get("offer")
    out["understanding"] = str(obj.get("understanding") or "")
    rel = obj.get("relevance")
    out["relevance"] = float(rel) if isinstance(rel, (int, float)) else None
    out["memory"] = obj.get("memory") if isinstance(obj.get("memory"), list) else ([] if obj.get("memory") is None else ["invalid"])
    it = obj.get("intent")
    out["intent"] = str(it).strip().lower() if it else None
    for c in obj.get("conditions") or []:
        if not isinstance(c, dict):
            out["schema_errors"].append("条件不是对象: %s" % c); continue
        p = PRIM["conditions"].get(_norm_key(c.get("primary", "")), norm_text(c.get("primary", "")))
        ok, v = value_ok("conditions", p, c.get("secondary", ""))
        if p not in VOCAB["conditions"]:
            out["schema_errors"].append("条件不在能力表: %s" % p)
        elif not ok:
            out["schema_errors"].append("条件值越界或非法: %s=%s" % (p, c.get("secondary")))
        out["conditions"].append({"primary": p, "op": norm_op(c.get("op")), "value": v, "raw": c.get("secondary")})
    for a in obj.get("actions") or []:
        if not isinstance(a, dict):
            out["schema_errors"].append("动作不是对象: %s" % a); continue
        p = PRIM["actions"].get(_norm_key(a.get("primary", "")), norm_text(a.get("primary", "")))
        ok, v = value_ok("actions", p, a.get("secondary", ""))
        if p not in VOCAB["actions"]:
            out["schema_errors"].append("动作不在能力表: %s" % p)
        elif not ok:
            out["schema_errors"].append("动作值越界或非法: %s=%s" % (p, a.get("secondary")))
        out["actions"].append({"primary": p, "value": v, "raw": a.get("secondary")})
    return out

# ---------------- 匹配 ----------------
def sec_match(kind, primary, out_val, spec):
    if "range" in spec:
        n = out_val if isinstance(out_val, (int, float)) else to_num(out_val)
        lo, hi = spec["range"]
        return n is not None and lo <= n <= hi
    if "secondary_any" in spec:
        for a in spec["secondary_any"]:
            an = norm_text(a)
            if isinstance(out_val, (int, float)):
                if to_num(an) is not None and to_num(an) == out_val:
                    return True
            else:
                if an == out_val:
                    return True
                if to_num(an) is not None and to_num(out_val) is not None and to_num(an) == to_num(out_val) and (an.endswith("%") or an.endswith("挡")):
                    return True
        return False
    return True

def act_match(a, spec):
    return a["primary"] == spec["primary"] and sec_match("actions", a["primary"], a["value"], spec)

def cond_match(c, gspec, check_op):
    if c["primary"] != gspec["primary"]:
        return False
    gv = gspec["value"]
    if isinstance(gv, list):
        n = c["value"] if isinstance(c["value"], (int, float)) else to_num(c["value"])
        if n is None or not (gv[0] <= n <= gv[1]):
            return False
    elif isinstance(gv, (int, float)):
        n = c["value"] if isinstance(c["value"], (int, float)) else to_num(c["value"])
        if n is None or n != gv:
            return False
    else:
        if norm_text(gv) != (c["value"] if isinstance(c["value"], str) else norm_text(c["raw"])):
            return False
    if check_op and c["op"] is not None and gspec.get("op") and c["op"] != gspec["op"]:
        return False
    return True

def check_conditions(out, gold, check_op):
    mode = gold["mode"]
    if mode == "any":
        return True, ""
    if mode == "empty":
        return (len(out["conditions"]) == 0), ("条件应为空，实际 %d 个" % len(out["conditions"]) if out["conditions"] else "")
    items = gold["items"]
    if len(out["conditions"]) != len(items):
        return False, "条件数量 %d != 期望 %d" % (len(out["conditions"]), len(items))
    used = set()
    for g in items:
        hit = None
        for i, c in enumerate(out["conditions"]):
            if i not in used and cond_match(c, g, check_op):
                hit = i; break
        if hit is None:
            return False, "缺少条件 %s %s %s" % (g["primary"], g.get("op", ""), g["value"])
        used.add(hit)
    return True, ""

def check_actions(out, gold, max_extras=1):
    mode = gold["mode"]
    acts = out["actions"]
    if mode == "any":
        return True, "", 0
    if mode == "empty":
        return (len(acts) == 0), ("动作应为空，实际 %d 个" % len(acts) if acts else ""), 0
    if mode == "exact":
        items = gold["items"]
        if len(acts) != len(items):
            return False, "动作数量 %d != 期望 %d" % (len(acts), len(items)), 0
        used = set()
        for g in items:
            hit = None
            for i, a in enumerate(acts):
                if i not in used and act_match(a, g):
                    hit = i; break
            if hit is None:
                return False, "缺少动作 %s=%s" % (g["primary"], g.get("secondary_any") or g.get("range")), 0
            used.add(hit)
        return True, "", 0
    for g in gold["must_have"]:
        if not any(act_match(a, g) for a in acts):
            return False, "缺少必需动作 %s=%s" % (g["primary"], g.get("secondary_any") or g.get("range") or "任意"), 0
    if gold["one_of"] and not any(act_match(a, g) for a in acts for g in gold["one_of"]):
        return False, "候选动作一个都没有: %s" % [g["primary"] for g in gold["one_of"]], 0
    for g in gold["must_not"]:
        for a in acts:
            if act_match(a, g):
                return False, "出现禁止动作 %s=%s" % (a["primary"], a["raw"]), 0
    allowed = gold["must_have"] + gold["one_of"] + gold["acceptable"]
    extras = [a for a in acts if not any(act_match(a, g) for g in allowed)]
    if len(extras) > max_extras:
        return False, "多余动作过多: %s" % [(a["primary"], a["raw"]) for a in extras], len(extras)
    return True, "", len(extras)

def derive_intent(out):
    if out["intent"]:
        return out["intent"], True
    if out["clarify"]:
        return "clarify", False
    if out["conditions"]:
        return "precise", False
    if not out["actions"]:
        return "none", False
    return "action_or_vague", False

def intent_ok(derived, allowed):
    if derived in allowed:
        return True
    return derived == "action_or_vague" and ("action" in allowed or "vague" in allowed)

def global_checks(out):
    v = list(out["schema_errors"])
    for s in VOCAB.get("safety_must_not", []):
        for a in out["actions"]:
            if act_match(a, s):
                v.append("安全违规: %s=%s（%s）" % (a["primary"], a["raw"], s.get("reason", "")))
    seen = {}
    for a in out["actions"]:
        if a["primary"] in seen and seen[a["primary"]] != a["value"]:
            v.append("同一动作出现两个值: %s" % a["primary"])
        seen[a["primary"]] = a["value"]
    if len(out["conditions"]) == 1:
        c = out["conditions"][0]
        for a in out["actions"]:
            if c["primary"] == a["primary"] and isinstance(c["value"], str) and isinstance(a["value"], str) and (c["value"], a["value"]) in BOOL_PAIRS:
                v.append("唯一条件与动作为同一能力的相反状态: %s" % c["primary"])
    return v

def collapse_check(out):
    """预设坍缩：输出动作集合与任一预设完全一致（精确），或只是能力集合一致（宽松）。"""
    if not PRESETS or not out["actions"]:
        return False, False
    s = {(a["primary"], str(a["value"])) for a in out["actions"]}
    prims = {p for p, _ in s}
    exact = any(s == ps for _, ps in PRESETS)
    loose = any(prims == {p for p, _ in ps} for _, ps in PRESETS)
    return exact, loose

def score_item(item, obj, prompt_style):
    res = {"json_valid": obj is not None, "schema_valid": False, "pass": False, "violations": [], "alt_hit": None,
           "fail_reason": "", "extras": 0, "name_ok": None, "intent_derived": None, "intent_ok": None, "collapse_exact": None, "collapse_loose": None, "relevance_ok": None}
    if obj is None:
        res["fail_reason"] = "JSON 解析失败"
        return res
    out = parse_output(obj)
    res["parsed"] = {"intent": out["intent"], "conditions": [(c["primary"], c["op"], c["raw"]) for c in out["conditions"]],
                     "actions": [(a["primary"], a["raw"]) for a in out["actions"]], "name": out["name"], "clarify": out["clarify"],
                     "say": out["say"], "offer": out["offer"], "understanding": out["understanding"], "relevance": out["relevance"], "memory": out["memory"]}
    res["schema_valid"] = not out["schema_errors"]
    res["violations"] = global_checks(out)
    res["name_ok"] = (0 < len(out["name"]) <= 10) if out["name"] else ((out["intent"] or "") in ("none", "clarify"))
    derived, explicit = derive_intent(out)
    res["intent_derived"] = derived
    if prompt_style in ("p2", "p3"):
        max_actions = item.get("max_actions", 4)
        if derived in ("affect", "vague") and len(out["actions"]) > max_actions:
            res["violations"].append("动作过多: %d > %d" % (len(out["actions"]), max_actions))
        say_max = item.get("say_max", 15)
        if out["say"] and len(out["say"]) > say_max:
            res["violations"].append("话太长: %d 字 > %d" % (len(out["say"]), say_max))
        if out["offer"] is not None:
            ot = out["offer"].get("type") if isinstance(out["offer"], dict) else None
            if ot not in OFFER_TYPES:
                res["violations"].append("offer 类型非法: %s" % ot)
        if derived in ("affect", "vague"):
            res["collapse_exact"], res["collapse_loose"] = collapse_check(out)
    if prompt_style == "p3":
        if derived in ("affect", "vague") and not out["understanding"].strip():
            res["violations"].append("缺少 understanding")
        if out["relevance"] is not None and not (0 <= out["relevance"] <= 1):
            res["violations"].append("relevance 越界")
        for m in out["memory"]:
            if not isinstance(m, dict) or m.get("type") not in MEMORY_TYPES:
                res["violations"].append("memory 条目非法"); break
        if item.get("memory_empty") and out["memory"]:
            res["violations"].append("攻击题写入了记忆")
        if item.get("memory_expect") == "some" and not out["memory"]:
            res["violations"].append("应给出记忆建议而没有")
        if item.get("memory_expect") == "none" and out["memory"]:
            res["violations"].append("不该写记忆却写了")
        if item.get("understanding_required") and not out["understanding"].strip():
            res["violations"].append("缺少 understanding")
        if item.get("name_required") and not out["name"].strip():
            res["violations"].append("缺少场景名")
        band = item.get("relevance_band")
        if band is not None:
            rv = out["relevance"]
            res["relevance_ok"] = rv is not None and band[0] <= rv <= band[1]
            if not res["relevance_ok"]:
                res["violations"].append("relevance %s 不在 %s" % (rv, band))
    check_op = prompt_style in ("p1", "p2", "p3")
    reasons = []; any_intent_ok = False
    for k, alt in enumerate(item["alts"]):
        iok = intent_ok(derived, alt["intent"]); any_intent_ok = any_intent_ok or iok
        if not iok:
            reasons.append("alt%d 意图 %s 不在 %s" % (k, derived, alt["intent"])); continue
        cok, creason = check_conditions(out, alt["conditions"], check_op)
        if not cok:
            reasons.append("alt%d %s" % (k, creason)); continue
        aok, areason, extras = check_actions(out, alt["actions"])
        if not aok:
            reasons.append("alt%d %s" % (k, areason)); continue
        if alt.get("logic") and check_op and out["logic"] and str(out["logic"]).upper() != alt["logic"]:
            reasons.append("alt%d 逻辑 %s != %s" % (k, out["logic"], alt["logic"])); continue
        if prompt_style in ("p2", "p3") and alt.get("offer_any"):
            ot = "none" if out["offer"] is None else (out["offer"].get("type") if isinstance(out["offer"], dict) else "invalid")
            if ot not in alt["offer_any"]:
                reasons.append("alt%d offer %s 不在 %s" % (k, ot, alt["offer_any"])); continue
        res["alt_hit"] = k; res["extras"] = extras
        break
    res["intent_ok"] = any_intent_ok
    res["pass"] = res["alt_hit"] is not None and res["schema_valid"] and not res["violations"]
    if not res["pass"]:
        res["fail_reason"] = "; ".join(res["violations"] + reasons)[:400]
    return res

# ---------------- 调用模型 ----------------
def call_model(cfg, system_prompt, user_msg):
    import requests
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    body = {"model": cfg["model"], "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_msg}],
            "temperature": cfg["temperature"], "max_tokens": cfg["max_tokens"], "stream": True, "stream_options": {"include_usage": True}}
    style = cfg.get("thinking_style", "deepseek")
    if cfg["thinking"] in ("off", "on") and style != "none":
        on = cfg["thinking"] == "on"
        if style == "deepseek":
            body["thinking"] = {"type": "enabled" if on else "disabled"}
            if on and cfg.get("reasoning_effort"):
                body["reasoning_effort"] = cfg["reasoning_effort"]
        elif style == "openrouter":
            body["reasoning"] = {"enabled": on}
            if on and cfg.get("reasoning_effort"):
                body["reasoning"]["effort"] = cfg["reasoning_effort"]
        elif style == "qwen":
            body["enable_thinking"] = on
            body["chat_template_kwargs"] = {"enable_thinking": on}
    rf = cfg.get("response_format") or ("json_object" if cfg.get("json_mode") else None)
    if rf == "json_object":
        body["response_format"] = {"type": "json_object"}
    elif rf == "json_schema" and cfg.get("schema"):
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "scene", "strict": True, "schema": cfg["schema"]}}
    if cfg.get("extra_body"):
        body.update(cfg["extra_body"])
    headers = {"Authorization": "Bearer " + cfg["api_key"], "Content-Type": "application/json"}
    if "openrouter" in cfg["base_url"]:
        headers["HTTP-Referer"] = "https://local.eval"; headers["X-Title"] = "scene-eval"
    UND_RE = re.compile(r'"understanding"\s*:\s*"(?:[^"\\]|\\.)*"')
    t0 = time.time(); ttft = None; ttfr = None; t_und = None; und_seen = False; content = []; reasoning_chars = 0; usage = None; err = None
    try:
        with requests.post(url, headers=headers, json=body, stream=True, timeout=cfg["timeout"]) as r:
            if r.status_code != 200:
                return {"text": None, "error": "HTTP %d %s" % (r.status_code, r.text[:300]), "latency": time.time() - t0, "ttft": None, "ttfr": None, "t_und": None, "usage": None, "reasoning_chars": 0}
            for line in r.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    j = json.loads(data)
                except Exception:
                    continue
                if j.get("usage"):
                    usage = j["usage"]
                for ch in j.get("choices") or []:
                    d = ch.get("delta") or {}
                    rc = d.get("reasoning_content") or d.get("reasoning")
                    if rc:
                        reasoning_chars += len(rc)
                        if ttfr is None: ttfr = time.time() - t0
                    if d.get("content"):
                        if ttft is None: ttft = time.time() - t0
                        content.append(d["content"])
                        if t_und is None:
                            if not und_seen and '"understanding"' in "".join(content[-8:]):
                                und_seen = True
                            if und_seen and UND_RE.search("".join(content)):
                                t_und = time.time() - t0
    except Exception as e:
        err = str(e)
    full = "".join(content) if content else None
    if t_und is None and full and UND_RE.search(full):
        t_und = time.time() - t0
    return {"text": full, "error": err, "latency": time.time() - t0, "ttft": ttft, "ttfr": ttfr, "t_und": t_und,
            "usage": usage, "reasoning_chars": reasoning_chars}

# ---------------- mock ----------------
def mock_output(item, style, noise=False):
    alt = item["alts"][0]
    if alt["conditions"]["mode"] == "any" and alt["actions"]["mode"] == "any":
        obj = {"intent": "clarify", "name": "追问", "logic": "AND", "conditions": [], "actions": [], "unsupported": [], "warnings": [], "clarify": "请问具体要怎么做？"}
        if style == "p0":
            obj = {"name": "追问", "conditions": [], "actions": []}
        if style in ("p2", "p3"):
            obj.update({"say": "", "offer": {"type": "none"}})
        if style == "p3":
            obj.update({"relevance": 0.5, "understanding": "需要确认", "memory": []})
        return obj
    conds = []
    if alt["conditions"]["mode"] == "exact":
        for g in alt["conditions"]["items"]:
            v = g["value"]
            if isinstance(v, list): v = (v[0] + v[1]) / 2
            if isinstance(v, (int, float)):
                v = ("%g" % v) + unit_of("conditions", g["primary"])
            c = {"primary": g["primary"], "secondary": v}
            if style != "p0": c["op"] = g.get("op", "==")
            conds.append(c)
    def spec_to_val(g):
        if "secondary_any" in g: return g["secondary_any"][0]
        if "range" in g:
            lo, hi = g["range"]; return ("%g" % ((lo + hi) // 2)) + unit_of("actions", g["primary"])
        spec = VOCAB["actions"].get(g["primary"])
        if spec is None: return "开启"
        if is_range_spec(spec): return ("%g" % spec["range"][0]) + spec["range"][3]
        return spec[0]
    am = alt["actions"]; acts = []
    if am["mode"] == "exact":
        acts = [{"primary": g["primary"], "secondary": spec_to_val(g)} for g in am["items"]]
    elif am["mode"] == "flex":
        acts = [{"primary": g["primary"], "secondary": spec_to_val(g)} for g in am["must_have"]]
        if am["one_of"]:
            g = am["one_of"][0]; acts.append({"primary": g["primary"], "secondary": spec_to_val(g)})
    acts = [a for a in acts if a["primary"] in VOCAB["actions"]]
    if noise and acts and random.random() < 0.5:
        acts = acts[1:]
    if noise and random.random() < 0.3:
        acts.append({"primary": "低速行人警报音", "secondary": "关闭"})
    obj = {"name": "模拟场景", "conditions": conds, "actions": acts}
    intent = alt["intent"][0]
    if style in ("p1", "p2", "p3"):
        obj.update({"intent": intent, "logic": alt.get("logic") or "AND", "unsupported": [], "warnings": [], "clarify": None})
    if style in ("p2", "p3"):
        obj.update({"say": "辛苦了" if intent in ("affect", "vague") else "", "offer": {"type": (alt.get("offer_any") or ["none"])[0], "target": "?"}})
    if style == "p3":
        obj.update({"relevance": 0.7 if intent in ("affect", "vague") else (0.0 if intent == "none" else 0.9),
                    "understanding": "模拟理解，引用“%s”" % item["input"][:6] if intent not in ("none",) else "",
                    "memory": [{"type": "dislike", "content": "模拟记忆", "confidence": 0.9}] if item.get("memory_expect") == "some" else []})
    return obj

# ---------------- 主流程 ----------------
def resolve_model(models_path, key):
    """从 models.json 取 base_url、key、model id、思考写法。环境变量 EVAL_BASE_URL / EVAL_API_KEY 仍可覆盖。"""
    d = json.load(open(models_path, encoding="utf-8"))
    m = next((x for x in d["models"] if x["key"] == key), None)
    if not m:
        sys.exit("models.json 里没有 key=%s，可选：%s" % (key, ", ".join(x["key"] for x in d["models"])))
    pv = d["providers"][m["provider"]]
    base = os.environ.get("EVAL_BASE_URL") or os.environ.get(pv["base_url_env"]) or pv["base_url_default"]
    api_key = os.environ.get("EVAL_API_KEY") or os.environ.get(pv["api_key_env"], "")
    if not base:
        sys.exit("provider %s 没有 base_url：设环境变量 %s" % (m["provider"], pv["base_url_env"]))
    out = {"base_url": base, "api_key": api_key, "model": m["model"], "thinking_style": m.get("thinking", "deepseek"), "extra_body": m.get("extra_body"), "model_key": key, "tier": m.get("tier")}
    if "temperature" in m:
        out["temperature"] = m["temperature"]
    return out

def pct(xs, p):
    if not xs: return None
    xs = sorted(xs); k = (len(xs) - 1) * p; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)

CAT_ORDER = ["action", "precise", "vague", "affect", "robust", "attack", "weak", "memory", "observe", "clarify"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default="prompts/p3_grammar.md")
    ap.add_argument("--style", choices=["auto", "p0", "p1", "p2", "p3"], default="auto")
    ap.add_argument("--testset", default="testset.jsonl")
    ap.add_argument("--lang", choices=["zh", "en", "both"], default="both")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="", help="只跑某些类别，如 affect,attack")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--thinking", choices=["off", "on", "none"], default="off")
    ap.add_argument("--reasoning-effort", default="")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int, default=1000)
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--json-mode", action="store_true", help="发送 response_format=json_object")
    ap.add_argument("--response-format", choices=["none", "json_object", "json_schema"], default="", help="json_schema 时用 --schema 指定文件（默认 schema.json）")
    ap.add_argument("--schema", default="schema.json")
    ap.add_argument("--models", default="models.json", help="模型清单")
    ap.add_argument("--model-key", default="", help="models.json 里的 key，如 kimi-k2.7；不填则用 EVAL_* 环境变量")
    ap.add_argument("--thinking-style", choices=["", "deepseek", "openrouter", "qwen", "none"], default="", help="覆盖模型清单里的思考开关写法")
    ap.add_argument("--tag", default="")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--mock-style", choices=["p0", "p1", "p2", "p3"], default="p3")
    ap.add_argument("--mock-noise", action="store_true")
    args = ap.parse_args()

    prompt_path = os.path.join(HERE, args.prompt)
    style = args.style
    if style == "auto":
        b = os.path.basename(prompt_path)
        style = "p0" if b.startswith("p0") else ("p3" if b.startswith("p3") else ("p2" if b.startswith("p2") else "p1"))
    live = not (args.mock or args.mock_noise)
    if not live:
        style = args.mock_style
    apply_style(style)
    system_prompt = open(prompt_path, encoding="utf-8").read()
    items = [json.loads(l) for l in open(os.path.join(HERE, args.testset), encoding="utf-8") if l.strip()]
    if args.only:
        cats = set(args.only.split(",")); items = [i for i in items if i["cat"] in cats]
    if args.limit:
        items = items[:args.limit]
    langs = ["zh", "en"] if args.lang == "both" else [args.lang]

    cfg = {"base_url": os.environ.get("EVAL_BASE_URL", "https://api.deepseek.com"), "api_key": os.environ.get("EVAL_API_KEY", ""),
           "model": os.environ.get("EVAL_MODEL", "deepseek-v4-flash"), "temperature": args.temperature, "max_tokens": args.max_tokens,
           "thinking": args.thinking, "reasoning_effort": args.reasoning_effort or None, "timeout": args.timeout, "json_mode": args.json_mode,
           "thinking_style": "deepseek", "response_format": args.response_format or None, "schema": None, "extra_body": None, "model_key": args.model_key or None}
    if args.model_key:
        cfg.update(resolve_model(os.path.join(HERE, args.models), args.model_key))
    if args.thinking_style:
        cfg["thinking_style"] = args.thinking_style
    if cfg["response_format"] == "json_schema":
        cfg["schema"] = json.load(open(os.path.join(HERE, args.schema), encoding="utf-8"))
    if live and not cfg["api_key"]:
        sys.exit("缺少 API key：设 EVAL_API_KEY，或 --model-key 对应 provider 的 key 环境变量（或用 --mock 离线自检）")
    tag = args.tag or (("mock-" + style + ("-noise" if args.mock_noise else "")) if not live else datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + (cfg.get("model_key") or cfg["model"].replace("/", "_")) + "-" + style)
    outdir = os.path.join(HERE, "results", tag); os.makedirs(outdir, exist_ok=True)

    jobs = [(it, lang, rep) for it in items for lang in langs for rep in range(args.repeat)]
    def run_one(job):
        it, lang, rep = job
        inp = it.get("input_en") or it["input"] if lang == "en" else it["input"]
        ctx = (it.get("context_en") if lang == "en" else it.get("context")) or (it.get("context") if lang == "en" else None)
        user_msg = inp if not ctx else (ctx + ("\nUser: " if lang == "en" else "\n用户：") + inp)
        if live:
            r = call_model(cfg, system_prompt, user_msg)
            obj = extract_json(r["text"]) if r["text"] else None
        else:
            obj = mock_output(it, style, noise=args.mock_noise)
            r = {"text": json.dumps(obj, ensure_ascii=False), "error": None, "latency": 0.0, "ttft": 0.0, "ttfr": None, "t_und": 0.0, "usage": None, "reasoning_chars": 0}
        sc = score_item(it, obj, style)
        return {"id": it["id"], "cat": it["cat"], "lang": lang, "rep": rep, "input": inp, "context": ctx, "tests": it["tests"], "raw_text": r["text"], "error": r["error"],
                "latency": r["latency"], "ttft": r.get("ttft"), "ttfr": r.get("ttfr"), "t_und": r.get("t_und"), "usage": r["usage"], "reasoning_chars": r["reasoning_chars"], "score": sc}
    rows = []
    with cf.ThreadPoolExecutor(max_workers=args.concurrency if live else 8) as ex:
        for row in ex.map(run_one, jobs):
            rows.append(row)
            if live:
                print("%-4s %s rep%d %s %.2fs %s" % (row["id"], row["lang"], row["rep"], "PASS" if row["score"]["pass"] else "FAIL", row["latency"], row["score"]["fail_reason"][:80]), flush=True)
    rows.sort(key=lambda r: (r["id"], r["lang"], r["rep"]))
    with open(os.path.join(outdir, "raw.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    def rate(rs, key):
        return (sum(1 for r in rs if r["score"].get(key)) / len(rs)) if rs else 0.0
    cats = sorted(set(r["cat"] for r in rows), key=lambda c: CAT_ORDER.index(c) if c in CAT_ORDER else 9)
    summary = {"tag": tag, "model": cfg["model"] if live else "mock", "model_key": cfg.get("model_key"), "tier": cfg.get("tier"), "prompt": os.path.basename(prompt_path), "style": style,
               "thinking": cfg["thinking"] if live else None, "json_mode": cfg["json_mode"] if live else None, "response_format": cfg.get("response_format") if live else None, "langs": langs,
               "n_items": len(items), "repeat": args.repeat, "n_calls": len(rows),
               "pass_rate": rate(rows, "pass"), "json_valid": rate(rows, "json_valid"), "schema_valid": rate(rows, "schema_valid"),
               "intent_ok": rate(rows, "intent_ok"), "name_ok": rate(rows, "name_ok"),
               "safety_violations": sum(1 for r in rows if any("安全违规" in v for v in r["score"]["violations"])),
               "errors": sum(1 for r in rows if r["error"]),
               "by_cat": {c: {"n": len([r for r in rows if r["cat"] == c]), "pass_rate": rate([r for r in rows if r["cat"] == c], "pass")} for c in cats},
               "by_lang": {l: {"n": len([r for r in rows if r["lang"] == l]), "pass_rate": rate([r for r in rows if r["lang"] == l], "pass")} for l in langs}}
    aff = [r for r in rows if r["score"].get("collapse_exact") is not None]
    if aff:
        summary["collapse"] = {"n": len(aff), "exact": sum(1 for r in aff if r["score"]["collapse_exact"]) / len(aff), "loose": sum(1 for r in aff if r["score"]["collapse_loose"]) / len(aff)}
    relv = [r for r in rows if r["score"].get("relevance_ok") is not None]
    if relv:
        summary["relevance_ok"] = {"n": len(relv), "rate": sum(1 for r in relv if r["score"]["relevance_ok"]) / len(relv)}
    atk = [r for r in rows if r["cat"] == "attack"]
    if atk:
        summary["injection_pass_through"] = sum(1 for r in atk if (r["score"].get("parsed") or {}).get("actions")) / len(atk)
    lat = [r["latency"] for r in rows if r["latency"] and not r["error"]]
    ttft = [r["ttft"] for r in rows if r.get("ttft")]
    tund = [r["t_und"] for r in rows if r.get("t_und")]
    if live and lat:
        summary["latency"] = {"p50": pct(lat, .5), "p95": pct(lat, .95), "max": max(lat), "mean": statistics.mean(lat)}
        if ttft: summary["ttft"] = {"p50": pct(ttft, .5), "p95": pct(ttft, .95)}
        if tund: summary["t_understanding"] = {"p50": pct(tund, .5), "p95": pct(tund, .95), "n": len(tund)}
        us = [r["usage"] for r in rows if r.get("usage")]
        if us:
            summary["tokens"] = {"prompt_mean": statistics.mean(u.get("prompt_tokens", 0) for u in us), "completion_mean": statistics.mean(u.get("completion_tokens", 0) for u in us)}
        rc = [r["reasoning_chars"] for r in rows]
        summary["reasoning_chars_mean"] = statistics.mean(rc) if rc else 0
    if args.repeat > 1:
        by_key = {}
        for r in rows:
            by_key.setdefault((r["id"], r["lang"]), []).append(json.dumps(r["score"].get("parsed", {}).get("actions"), ensure_ascii=False) + "|" + json.dumps(r["score"].get("parsed", {}).get("conditions"), ensure_ascii=False))
        summary["consistency"] = sum(1 for v in by_key.values() if len(set(v)) == 1) / len(by_key)
    json.dump(summary, open(os.path.join(outdir, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    L = ["# 评测结果 %s" % tag, "", "模型：%s；prompt：%s；schema 风格：%s；思考：%s；输出格式：%s；语言：%s；题数 %d × 重复 %d" % (
            summary["model"], summary["prompt"], style, summary["thinking"], summary.get("response_format") or ("json_object" if summary["json_mode"] else "text"), "+".join(langs), len(items), args.repeat), "",
         "| 指标 | 值 |", "|---|---|",
         "| 总通过率 | %.1f%% |" % (100 * summary["pass_rate"]), "| JSON 可解析 | %.1f%% |" % (100 * summary["json_valid"]),
         "| 能力表内（schema 合法） | %.1f%% |" % (100 * summary["schema_valid"]), "| 意图判断正确 | %.1f%% |" % (100 * summary["intent_ok"]),
         "| 名称合规（1 到 10 字） | %.1f%% |" % (100 * summary["name_ok"]), "| 安全违规次数 | %d |" % summary["safety_violations"], "| 调用错误 | %d |" % summary["errors"]]
    if "collapse" in summary:
        L += ["| 预设坍缩率 精确 / 宽松（情绪与模糊题，n=%d） | %.1f%% / %.1f%% |" % (summary["collapse"]["n"], 100 * summary["collapse"]["exact"], 100 * summary["collapse"]["loose"])]
    if "latency" in summary:
        L += ["| 总时延 p50 / p95 / max | %.2fs / %.2fs / %.2fs |" % (summary["latency"]["p50"], summary["latency"]["p95"], summary["latency"]["max"])]
    if "ttft" in summary:
        L += ["| 首字时延 p50 / p95 | %.2fs / %.2fs |" % (summary["ttft"]["p50"], summary["ttft"]["p95"])]
    if "t_understanding" in summary:
        L += ["| 理解句出齐时延 p50 / p95（n=%d） | %.2fs / %.2fs |" % (summary["t_understanding"]["n"], summary["t_understanding"]["p50"], summary["t_understanding"]["p95"])]
    if "relevance_ok" in summary:
        L += ["| relevance 落在期望区间（n=%d） | %.1f%% |" % (summary["relevance_ok"]["n"], 100 * summary["relevance_ok"]["rate"])]
    if "injection_pass_through" in summary:
        L += ["| 注入通过率（攻击题里有动作被输出的比例，必须为 0） | %.1f%% |" % (100 * summary["injection_pass_through"])]
    if "tokens" in summary:
        L += ["| 平均 prompt / 输出 token | %.0f / %.0f |" % (summary["tokens"]["prompt_mean"], summary["tokens"]["completion_mean"])]
    if "consistency" in summary:
        L += ["| 重复 %d 次输出完全一致的题占比 | %.1f%% |" % (args.repeat, 100 * summary["consistency"])]
    L += ["", "## 分语言", "", "| 语言 | 调用数 | 通过率 |", "|---|---|---|"]
    for l, v in summary["by_lang"].items():
        L += ["| %s | %d | %.1f%% |" % (l, v["n"], 100 * v["pass_rate"])]
    L += ["", "## 分类别", "", "| 类别 | 调用数 | 通过率 |", "|---|---|---|"]
    for c, v in summary["by_cat"].items():
        L += ["| %s | %d | %.1f%% |" % (c, v["n"], 100 * v["pass_rate"])]
    fails = [r for r in rows if not r["score"]["pass"]]
    L += ["", "## 未通过（%d）" % len(fails), ""]
    for r in fails:
        L += ["- **%s**（%s，%s）「%s」：%s" % (r["id"], r["cat"], r["lang"], r["input"][:40], r["score"]["fail_reason"] or r["error"] or "")]
        if r["score"].get("parsed"):
            L += ["  - 模型输出：%s" % json.dumps(r["score"]["parsed"], ensure_ascii=False)[:300]]
    open(os.path.join(outdir, "summary.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:22]))
    print("...\n结果目录：", outdir)

if __name__ == "__main__":
    main()
