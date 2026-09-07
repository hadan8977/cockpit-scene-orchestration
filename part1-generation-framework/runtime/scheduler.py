"""Deterministic virtual-time scene engine for product/technical demonstrations.

No vehicle RPCs are issued. Real adapters must enforce the same deadline and
provide readback/compensation; virtual state is not a production safety system.
"""
import copy
import re
import time
import uuid

from core import Conflict, Engine, empty_scene, utc, validate

LIGHT_SOUND={"氛围灯开关","氛围灯亮度","音乐律动","音量","导航音量","语音音量","声场","一键静音","声浪","多媒体"}


def match_condition(condition,state):
    actual=state.get(condition["primary"])
    expected=condition["secondary"];op=condition["op"]
    if actual is None:return False
    if op=="==":return str(actual)==expected
    pattern=r"^(-?\d+(?:\.\d+)?)(.*)$"
    a,b=re.fullmatch(pattern,str(actual)),re.fullmatch(pattern,expected)
    if not a or not b or a[2]!=b[2]:return False
    left,right=float(a[1]),float(b[1])
    return {"<":left<right,"<=":left<=right,">":left>right,">=":left>=right}.get(op,False)


def matches(scene,state):
    values=[match_condition(c,state) for c in scene["conditions"]]
    return bool(values) and (all(values) if scene["logic"]=="AND" else any(values))


class RuntimeEngine(Engine):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for key,value in {"memories":[],"timeline":[],"virtual_seconds":0,"trigger_latches":{},"once_consumed":[],"history":{}}.items():self.state.setdefault(key,value)
        # Restarts must not silently resume an interrupted execution.
        for job in self.state["timeline"]:
            if job["status"]=="pending":job["status"]="cancelled_on_restart"

    def _event(self,operation,**data):
        event={"operation":operation,"at":utc(),"virtual_seconds":self.state["virtual_seconds"],"simulation":True,**data}
        self.state["audit"].append(event);return event

    def saved_view(self):
        snapshot=self.registry.snapshot()
        return [{**copy.deepcopy(row),"validation":validate(row["scene"],snapshot,self.context,self.state["saved"])} for row in self.state["saved"].values()]

    def _cancel_pending(self,reason):
        for job in self.state["timeline"]:
            if job["status"]=="pending":job["status"]=reason

    def _start(self,pid,scene,priority,trial):
        before=copy.deepcopy(self.state["vehicle"])
        last={"id":pid,"before":before,"after":copy.deepcopy(before),"restored":False}
        self.state["last_execution"]=last;self.state["history"][pid]=last
        elapsed=0
        for action in scene["actions"]:
            if action["primary"]=="延时":elapsed+=int(action["secondary"].removesuffix("秒"));continue
            delay=max(elapsed,3 if trial and action["primary"] not in LIGHT_SOUND else 0)
            self.state["timeline"].append({"id":uuid.uuid4().hex,"execution_id":pid,"due":self.state["virtual_seconds"]+delay,"action":copy.deepcopy(action),"scene":copy.deepcopy(scene),"priority":priority,"status":"pending","registry_revision":self.registry.snapshot()["revision"]})
        self._event("timeline_started",execution_id=pid,priority=priority,trial_seconds=3 if trial else 0)
        self.advance(0)

    def confirm(self,pid,operation,expected_revision):
        with self.lock,self.registry.lock:
            p=self.proposals.get(pid)
            if operation!="apply_once":
                if operation=="save" and p:
                    relation=p["raw"].get("relation",{})
                    if relation.get("type") in ("extend","modify"):
                        target=self.state["saved"].get(relation.get("scene_id"))
                        if not target:raise Conflict("Merge target disappeared")
                        # Merge a full proposal without changing its trigger semantics.
                        if target["scene"]["conditions"]!=p["raw"]["conditions"] or target["scene"]["logic"]!=p["raw"]["logic"]:raise ValueError("Trigger changes require a new scene")
                        merged=copy.deepcopy(target["scene"])
                        actions={a["primary"]:a for a in merged["actions"]}
                        actions.update({a["primary"]:a for a in p["raw"]["actions"]})
                        merged["actions"]=list(actions.values());merged["relation"]={"type":"new","scene_id":None}
                        if not validate(merged,self.registry.snapshot(),self.context,self.state["saved"])["savable"]:raise ValueError("Merged scene invalid")
                        event=super().confirm(pid,operation,expected_revision)
                        self.state["saved"].pop(pid);target["scene"]=merged;target["registry_revision"]=expected_revision
                        self._persist();return {**event,"scene_id":target["id"],"relation":relation}
                return super().confirm(pid,operation,expected_revision)
            if not p or p["status"] not in ("pending","saved") or self.clock()-p["created"]>300:raise Conflict("Proposal missing, handled or expired")
            if expected_revision!=p["revision"] or self.registry.snapshot()["revision"]!=p["revision"]:raise Conflict("Registry changed; regenerate")
            result=validate(p["raw"],self.registry.snapshot(),self.context,self.state["saved"])
            if not result["executable"] or p["raw"]["conditions"]:raise ValueError("Cannot immediately execute this proposal")
            # User's immediate confirmation takes precedence over scheduled work.
            self._cancel_pending("preempted_by_user")
            self._start(pid,p["raw"],priority=100,trial=p["raw"]["intent"]!="action")
            p["status"]="applied"
            event=self._event("apply_once",proposal_id=pid,executed=True,registry_revision=p["revision"])
            self._persist();return {**event,"status":"applied"}

    def update_vehicle(self,values,driving):
        if not isinstance(values,dict) or type(driving) is not bool:raise ValueError("Trusted vehicle update requires values and boolean driving")
        snapshot=self.registry.snapshot();by_name={c["zh"]:c for c in snapshot["capabilities"]}
        if any(k not in by_name or not isinstance(v,str) or len(v)>80 for k,v in values.items()):raise ValueError("Invalid simulated vehicle state")
        with self.lock:
            self.context["driving"]=driving;self.state["vehicle"].update(values)
            self._event("vehicle_update",values=values,driving=driving)
            # Pending jobs are revalidated before every segment; no automatic tick.
            self._persist();return copy.deepcopy(self.state["vehicle"])

    def trigger(self):
        """Explicitly tick conditional simulation; no autonomous real actions."""
        with self.lock,self.registry.lock:
            current=self.registry.snapshot();events=[];claimed=set()
            candidates=[]
            for sid,row in self.state["saved"].items():
                hit=matches(row["scene"],self.state["vehicle"])
                was=self.state["trigger_latches"].get(sid,False)
                self.state["trigger_latches"][sid]=hit
                if not hit or was:continue
                candidates.append((len(row["scene"]["conditions"]),sid,row))
            for _,sid,row in sorted(candidates,key=lambda x:(-x[0],x[1])):
                checked=validate(row["scene"],current,self.context,self.state["saved"])
                names={a["primary"] for a in row["scene"]["actions"] if a["primary"]!="延时"}
                if not checked["executable"]:
                    events.append(self._event("trigger_blocked",scene_id=sid,reason="latest registry or vehicle policy"));continue
                if claimed&names or any(j["status"]=="pending" and j["priority"]>=100 for j in self.state["timeline"]):
                    events.append(self._event("trigger_yielded",scene_id=sid,reason="more specific scene or current user command"));continue
                claimed|=names
                execution_id=sid+"-"+uuid.uuid4().hex[:8]
                self._start(execution_id,row["scene"],priority=10+len(row["scene"]["conditions"]),trial=True)
                events.append(self._event("condition_triggered",scene_id=sid,execution_id=execution_id))
            self._persist();return events

    def advance(self,seconds):
        if type(seconds) not in (int,float) or not 0<=seconds<=1200:raise ValueError("Advance between 0 and 1200 virtual seconds")
        with self.lock,self.registry.lock:
            self.state["virtual_seconds"]+=seconds;start=time.monotonic();events=[]
            for job in sorted(self.state["timeline"],key=lambda j:(j["due"],-j["priority"],j["id"])):
                if job["status"]!="pending" or job["due"]>self.state["virtual_seconds"]:continue
                if time.monotonic()-start>2.5:
                    self._cancel_pending("circuit_breaker");events.append(self._event("circuit_breaker",reason="dispatch exceeded 2.5 seconds"));break
                snapshot=self.registry.snapshot()
                result=validate(job["scene"],snapshot,self.context,self.state["saved"])
                if snapshot["revision"]!=job["registry_revision"] or not result["executable"]:
                    job["status"]="blocked";events.append(self._event("segment_blocked",execution_id=job["execution_id"],reason="registry or vehicle changed"));continue
                action=job["action"];self.state["vehicle"][action["primary"]]=action["secondary"];job["status"]="executed"
                history=self.state["history"][job["execution_id"]]
                history["after"]=copy.deepcopy(self.state["vehicle"])
                if self.state["last_execution"]["id"]==job["execution_id"]:self.state["last_execution"]=history
                events.append(self._event("segment_executed",execution_id=job["execution_id"],action=action))
            self._persist();return events

    def restore(self,pid):
        with self.lock:
            result=super().restore(pid)
            for job in self.state["timeline"]:
                if job["execution_id"]==pid and job["status"]=="pending":job["status"]="cancelled_by_restore"
            self._persist();return result

    def confirm_memory(self,pid,index):
        """A distinct user confirmation; generation never writes preferences."""
        with self.lock:
            p=self.proposals.get(pid)
            if not p or type(index) is not int or not 0<=index<len(p["raw"].get("memory",[])):raise ValueError("Unknown memory suggestion")
            if p["status"]=="rejected" or self.clock()-p["created"]>300:raise ValueError("Memory proposal rejected or expired")
            if not validate(p["raw"],self.registry.snapshot(),self.context,self.state["saved"])["valid"]:raise ValueError("Invalid proposal cannot become memory")
            if p["provenance"].get("injection_flags"):raise ValueError("Flagged input cannot become memory")
            m=p["raw"]["memory"][index]
            if any(x.get("proposal_id")==pid and x.get("index")==index for x in self.state["memories"]):raise Conflict("Memory already confirmed")
            record={**copy.deepcopy(m),"id":uuid.uuid4().hex,"confirmed":True,"proposal_id":pid,"index":index}
            self.state["memories"].append(record);self._event("memory_confirmed",memory_id=record["id"]);self._persist();return record

    def delete_memory(self,memory_id):
        with self.lock:
            old=len(self.state["memories"]);self.state["memories"]=[m for m in self.state["memories"] if m["id"]!=memory_id]
            if len(self.state["memories"])==old:raise ValueError("Unknown memory")
            self._event("memory_deleted",memory_id=memory_id);self._persist();return {"deleted":memory_id}

    def demo_context(self,body):
        """Authenticated product-Demo boundary; all supplied state is simulated.

        The model never calls this endpoint. A production app would use its
        authenticated state/memory services rather than a browser-owned snapshot.
        """
        with self.lock:
            self.update_vehicle(body.get("vehicle",{}),body["driving"])
            memories=body.get("memories",[]);saved=body.get("saved_scenes",[])
            if not isinstance(memories,list) or len(memories)>24 or not isinstance(saved,list) or len(saved)>60:raise ValueError("Demo context too large")
            by_name={c["zh"]:c for c in self.registry.snapshot()["capabilities"]}
            records=[];denied=[]
            for i,m in enumerate(memories):
                if not isinstance(m,dict) or m.get("type") not in ("dislike","preference","place","relationship") or not isinstance(m.get("content"),str) or len(m["content"])>200:raise ValueError("Invalid confirmed demo memory")
                records.append({"id":"demo-"+str(i),"type":m["type"],"content":m["content"],"confirmed":True})
                if m.get("type")=="dislike" and m.get("primary"):
                    name=m["primary"]
                    if name not in by_name:raise ValueError("Unknown negative preference capability")
                    denied.append({"primary":name,"secondary":m.get("value")})
            self.state["memories"]=records;self.context["denied_actions"]=denied
            for s in saved:
                if not isinstance(s,dict) or not isinstance(s.get("id"),str) or len(s["id"])>80:raise ValueError("Invalid existing scene id")
                # Invalid imported scenes remain visible, but validation gates
                # prevent scheduling them. Never drop an invalid condition.
                raw=s.get("scene")
                if not isinstance(raw,dict):raise ValueError("Invalid saved scene")
                self.state["saved"][s["id"]]={"id":s["id"],"scene":copy.deepcopy(raw),"registry_revision":self.registry.snapshot()["revision"]}
            self._persist();return {"simulation":True,"memory_count":len(records),"saved_count":len(self.state["saved"])}
