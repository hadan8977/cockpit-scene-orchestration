"""One bounded provider call, streaming a complete understanding field first."""
import json
import re
import time

import requests

from core import strict_tool_schema, output_schema


def parse_json(text):
    def pairs(items):
        obj={}
        for k,v in items:
            if k in obj:raise ValueError("Duplicate JSON key")
            obj[k]=v
        return obj
    def bad(value):raise ValueError("Non-finite JSON number")
    obj=json.loads(text,object_pairs_hook=pairs,parse_constant=bad)
    if not isinstance(obj,dict):raise ValueError("Expected JSON object")
    return obj


def request_body(prompt,user,snapshot,mode):
    common={"model":"deepseek-v4-flash","temperature":0,"stream":True}
    if mode=="responses_schema":
        return "https://api.deepseek.com/responses",{**common,"instructions":prompt,"input":user,"reasoning":{"effort":"none"},"max_output_tokens":1000,"text":{"format":{"type":"json_schema","name":"cabin_scene","schema":output_schema(snapshot)}}}
    body={**common,"messages":[{"role":"system","content":prompt},{"role":"user","content":user}],"thinking":{"type":"disabled"},"max_tokens":1000,"stream_options":{"include_usage":True}}
    if mode=="strict_tool":
        body["tools"]=[{"type":"function","function":{"name":"propose_scene","description":"Return a proposed cabin scene. Does not execute anything.","strict":True,"parameters":strict_tool_schema(snapshot)}}]
        body["tool_choice"]={"type":"function","function":{"name":"propose_scene"}}
        return "https://api.deepseek.com/beta/chat/completions",body
    if mode!="json_object":raise ValueError("Unknown decoding mode")
    body["response_format"]={"type":"json_object"}
    return "https://api.deepseek.com/chat/completions",body


class DeepSeek:
    def __init__(self,key,mode="json_object",deadline=8,http=None):
        self.key=key;self.mode=mode;self.deadline=deadline;self.http=http or requests

    def events(self,prompt,user,snapshot,cancel=None):
        url,body=request_body(prompt,user,snapshot,self.mode)
        raw="";start=time.monotonic();first=None;understanding=None;finish=None;usage=None
        # No retry, repair call or undocumented fallback changes the generation.
        try:
            with self.http.post(url,headers={"Authorization":"Bearer "+self.key},json=body,stream=True,timeout=(min(5,self.deadline),self.deadline),allow_redirects=False) as response:
                if response.status_code!=200:raise ValueError("Provider HTTP "+str(response.status_code))
                for line in response.iter_lines(chunk_size=1):
                    if (cancel and cancel.is_set()) or time.monotonic()-start>self.deadline:raise TimeoutError("Generation cancelled or timed out")
                    if not line.startswith(b"data:"):continue
                    data=line[5:].strip()
                    if data==b"[DONE]":break
                    item=json.loads(data);delta=""
                    if self.mode=="responses_schema":
                        if item.get("type")=="response.output_text.delta":delta=item.get("delta","")
                        if item.get("type") in ("response.completed","response.incomplete","response.failed"):
                            final=item.get("response",{});finish=final.get("status");usage=final.get("usage")
                    else:
                        usage=item.get("usage") or usage
                        for choice in item.get("choices",[]):
                            finish=choice.get("finish_reason") or finish
                            content=choice.get("delta",{})
                            if self.mode=="strict_tool":
                                for call in content.get("tool_calls",[]):
                                    if call.get("index",0)!=0:raise ValueError("Multiple tool calls are not a single scene")
                                    fn=call.get("function",{})
                                    if fn.get("name") and fn["name"]!="propose_scene":raise ValueError("Unknown tool")
                                    delta+=fn.get("arguments","")
                            else:delta+=content.get("content") or ""
                    if delta and first is None:first=time.monotonic()-start
                    raw+=delta
                    if len(raw.encode())>64000:raise ValueError("Provider output too large")
                    if understanding is None:
                        match=re.match(r'^\s*\{\s*"understanding"\s*:\s*',raw)
                        if match:
                            try:
                                value,_=json.JSONDecoder().raw_decode(raw[match.end():])
                                if isinstance(value,str):
                                    understanding=time.monotonic()-start
                                    yield {"type":"understanding","text":value,"provisional":True,"seconds":understanding}
                            except ValueError:pass
            if finish not in ("stop","tool_calls","completed"):raise ValueError("Incomplete provider response")
            yield {"type":"model_result","raw":parse_json(raw),"raw_text":raw,"decoding":self.mode,"usage":usage,"timing":{"ttft":first,"understanding":understanding,"total":time.monotonic()-start}}
        except requests.RequestException as error:
            raise RuntimeError("Provider transport "+type(error).__name__) from None


class Fixture:
    """Explicitly labeled offline dependency for integration tests/demo walkthrough."""
    mode="fixture"
    def __init__(self,raw):self.raw=raw
    def events(self,prompt,user,snapshot,cancel=None):
        yield {"type":"understanding","text":self.raw.get("understanding",""),"provisional":True,"seconds":0}
        yield {"type":"model_result","raw":self.raw,"raw_text":json.dumps(self.raw,ensure_ascii=False),"decoding":"fixture","usage":None,"timing":{"ttft":0,"understanding":0,"total":0}}
