"""Local technical service. The product Demo calls this from its server route."""
import argparse
import copy
import hmac
import json
import os
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0,str(Path(__file__).resolve().parent))
from core import Registry, Conflict, PART, canonical, compile_prompt, empty_scene, output_schema, revision, validate
from context import assemble, relation_for
from provider import DeepSeek, Fixture, parse_json
from scheduler import RuntimeEngine


class Service:
    def __init__(self,engine,provider,template):
        self.engine=engine;self.provider=provider;self.template=Path(template);self.pending={};self.lock=threading.RLock()

    def generate(self,request):
        with self.engine.lock:
            envelope,context=assemble(request,self.engine)
            snapshot=self.engine.registry.snapshot()
            prompt,meta=compile_prompt(snapshot,self.template)
            request_id=uuid.uuid4().hex;cancel=threading.Event()
            self.pending[request_id]=cancel
        yield {"type":"request","request_id":request_id,"registry_revision":snapshot["revision"]}
        try:
            if context["injection_flags"]:
                raw=empty_scene();raw["warnings"]=["输入包含规则覆盖或权限伪装，提案已阻断。"]
                result=self.engine.propose(raw,{**meta,"injection_flags":context["injection_flags"],"model_called":False},request_id)
                result.update(status="rejected",valid=False,savable=False,executable=False)
                result["decisions"].append({"status":"blocked","code":"injection","reason":"输入注入检测命中"})
                # Mark the stored proposal too, so later confirmation cannot bypass.
                self.engine.proposals[request_id]["status"]="rejected"
                yield {"type":"result","result":result};return
            for event in self.provider.events(prompt,json.dumps(envelope,ensure_ascii=False,separators=(",",":")),snapshot,cancel):
                if event["type"]=="understanding":yield event;continue
                if cancel.is_set():raise TimeoutError("Cancelled")
                if self.engine.registry.snapshot()["revision"]!=snapshot["revision"]:raise Conflict("Registry changed during generation")
                raw=event["raw"]
                if context["previous"]:
                    raw=revision(context["previous"]["raw"],raw,request["edit_scope"])
                # Preserve invalid references; only fill fields absent from the
                # frozen prompt's older output contract. No model score is changed.
                raw=copy.deepcopy(raw)
                raw.setdefault("relation",relation_for(raw,context["existing_scenes"]))
                raw.setdefault("state_type",context["state_type"] if raw.get("intent") in ("vague","affect") else "none")
                provenance={**meta,"source":context["source"],"model":"deepseek-v4-flash" if self.provider.mode!="fixture" else "offline_fixture","decoding":event["decoding"],"timing":event["timing"],"usage":event["usage"],"injection_flags":[],"memory_bytes":context["memory"]["utf8_bytes"],"existing_scene_ids":[s["id"] for s in context["existing_scenes"]],"contract_adapter":"derive missing relation/state_type only"}
                result=self.engine.propose(raw,provenance,request_id)
                result["trace"].insert(0,{"layer":"input","source":context["source"],"memory":context["memory"],"existing_scene_count":len(context["existing_scenes"])})
                result["trace"].insert(2,{"layer":"decoding","mode":event["decoding"],"provider_schema_enforced":event["decoding"] in ("strict_tool","responses_schema")})
                yield {"type":"result","result":result}
        except (ValueError,RuntimeError,TimeoutError,Conflict) as error:
            with self.engine.lock:
                self.engine.state["audit"].append({"operation":"generation_failed","request_id":request_id,"error_type":type(error).__name__,"source":context["source"]})
                self.engine._persist()
            yield {"type":"error","request_id":request_id,"message":str(error),"executed":False,"presentation":"silent" if context["source"] in ("state","observation") else "retry_available"}
        finally:
            cancel.set();self.pending.pop(request_id,None)


def handler_for(service,token):
    class Handler(BaseHTTPRequestHandler):
        server_version="Part1Runtime/0.2"
        def log_message(self,*args):pass
        def send_json(self,status,value):
            data=canonical(value);self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
        def authorized(self):
            return hmac.compare_digest(self.headers.get("Authorization",""),"Bearer "+token)
        def do_GET(self):
            if not self.authorized():return self.send_json(401,{"error":"Authentication required"})
            path=urlsplit(self.path).path
            if path=="/health":return self.send_json(200,{"ok":True,"simulation":True,"provider":service.provider.mode,"registry_revision":service.engine.registry.snapshot()["revision"]})
            if path=="/registry":return self.send_json(200,service.engine.registry.snapshot())
            if path=="/schema":return self.send_json(200,output_schema(service.engine.registry.snapshot()))
            if path=="/state":return self.send_json(200,{**copy.deepcopy(service.engine.state),"saved_scenes":service.engine.saved_view()})
            return self.send_json(404,{"error":"Unknown route"})
        def do_POST(self):
            if not self.authorized():return self.send_json(401,{"error":"Authentication required"})
            # Browsers use the same-origin Demo server proxy; no broad CORS bypass.
            if self.headers.get("Origin"):return self.send_json(403,{"error":"Use the authenticated server proxy"})
            try:
                length=int(self.headers.get("Content-Length","0"))
                if not 0<length<=64000:raise ValueError("Invalid body length")
                body=parse_json(self.rfile.read(length).decode("utf-8"));path=urlsplit(self.path).path
                if path=="/generate":
                    stream=service.generate(body)
                    # Validate request before SSE headers are committed.
                    first=next(stream)
                    self.send_response(200);self.send_header("Content-Type","text/event-stream; charset=utf-8");self.send_header("Cache-Control","no-store");self.end_headers()
                    try:
                        self.wfile.write(b"data: "+canonical(first)+b"\n\n");self.wfile.flush()
                        for event in stream:self.wfile.write(b"data: "+canonical(event)+b"\n\n");self.wfile.flush()
                    finally:stream.close()
                    return
                if path=="/cancel":
                    cancel=service.pending.get(body["request_id"])
                    if cancel:cancel.set()
                    result={"cancelled":bool(cancel)}
                elif path=="/confirm":result=service.engine.confirm(body["proposal_id"],body["operation"],body["registry_revision"])
                elif path=="/restore":result=service.engine.restore(body["proposal_id"])
                elif path=="/registry/toggle":result=service.engine.registry.set_enabled(body["id"],body["enabled"],body["registry_revision"])
                elif path=="/simulation/state":result=service.engine.update_vehicle(body["values"],body["driving"])
                elif path=="/demo/context":result=service.engine.demo_context(body)
                elif path=="/demo/prepare":
                    raw=body["scene"]
                    result=service.engine.propose(raw,{"source":"demo_import","simulation":True})
                elif path=="/simulation/advance":result={"events":service.engine.advance(body["seconds"])}
                elif path=="/simulation/trigger":result={"events":service.engine.trigger()}
                elif path=="/memory/confirm":result=service.engine.confirm_memory(body["proposal_id"],body["index"])
                elif path=="/memory/delete":result=service.engine.delete_memory(body["id"])
                else:return self.send_json(404,{"error":"Unknown route"})
                return self.send_json(200,result)
            except Conflict as e:return self.send_json(409,{"error":str(e)})
            except (ValueError,KeyError,TypeError,StopIteration) as e:return self.send_json(400,{"error":str(e)})
            except (BrokenPipeError,ConnectionResetError):return
    return Handler


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--port",type=int,default=8787);ap.add_argument("--env-file");ap.add_argument("--mode",choices=["json_object","strict_tool","responses_schema"],default="strict_tool");ap.add_argument("--template",default=str(PART/"delivery/prompt/system-zh.md"));ap.add_argument("--fixture");ap.add_argument("--storage",default=str(PART/"runtime-state"))
    args=ap.parse_args()
    credentials=dict(os.environ)
    if args.env_file:
        for line in Path(args.env_file).read_text(encoding="utf-8-sig").splitlines():
            k,sep,v=line.partition("=")
            if sep and k.strip() in ("DEEPSEEK_API_KEY","DEEPSEEK_OFFICIAL_API_KEY","PART1_RUNTIME_TOKEN"):credentials[k.strip()]=v.strip().strip('"').strip("'")
    token=credentials.get("PART1_RUNTIME_TOKEN")
    if not token:raise SystemExit("Set PART1_RUNTIME_TOKEN in the private environment or env file")
    reg=Registry(storage=args.storage);engine=RuntimeEngine(reg,args.storage)
    provider=Fixture(parse_json(Path(args.fixture).read_text(encoding="utf-8"))) if args.fixture else DeepSeek(credentials.get("DEEPSEEK_OFFICIAL_API_KEY") or credentials["DEEPSEEK_API_KEY"],args.mode)
    service=Service(engine,provider,args.template)
    server=ThreadingHTTPServer(("127.0.0.1",args.port),handler_for(service,token))
    print(json.dumps({"listening":"127.0.0.1:"+str(args.port),"simulation":True,"provider":provider.mode}),flush=True)
    try:server.serve_forever()
    finally:server.server_close()


if __name__=="__main__":main()
