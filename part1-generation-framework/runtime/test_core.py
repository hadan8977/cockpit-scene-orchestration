import copy
import json
import tempfile
import unittest
from pathlib import Path

from core import Registry, Engine, Conflict, PART, validate, empty_scene, output_schema, compile_prompt, revision


def scene(actions=None, conditions=None):
    return {**empty_scene(),"understanding":"调暗灯光","name":"灯光","intent":"precise" if conditions else "action","relevance":.9 if conditions else .1,"actions":actions or [{"primary":"氛围灯亮度","secondary":"20%"}],"conditions":conditions or []}


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.reg=Registry();self.snapshot=self.reg.snapshot();self.engine=Engine(self.reg)

    def test_current_registry_and_compiled_prompt_match_experiment(self):
        self.assertEqual(len(self.snapshot["capabilities"]),114)
        p=PART/"studies/round2/prompts/p14_zh.md"
        rendered,meta=compile_prompt(self.snapshot,p)
        self.assertEqual(rendered,p.read_text(encoding="utf-8"))
        self.assertEqual(meta["registry_revision"],self.snapshot["revision"])

    def test_runtime_does_not_execute_on_generation(self):
        p=self.engine.propose(scene(),{})
        self.assertFalse(p["executed"])
        self.assertEqual(self.engine.state["vehicle"],{})
        self.assertEqual(p["trace"][-1]["status"],"awaiting_user_confirmation")

    def test_illegal_condition_is_not_removed_into_an_immediate_action(self):
        raw=scene(conditions=[{"primary":"车内PM2.5","op":">","secondary":"75"}])
        result=validate(raw,self.snapshot)
        self.assertFalse(result["valid"])
        self.assertFalse(result["executable"])
        self.assertEqual(result["scene"]["conditions"],raw["conditions"])

    def test_forbidden_avas_rejected_even_when_prompt_failed(self):
        p=scene([{"primary":"低速行人警报音","secondary":"关闭"}])
        result=validate(p,self.snapshot)
        self.assertFalse(result["executable"])
        self.assertTrue(any(d.get("code")=="forbidden" for d in result["decisions"]))

    def test_step_units_and_real_calendar_dates(self):
        for primary,value in [("氛围灯亮度","25%"),("主驾温度控制","24"),("主驾温度控制","80℃")]:
            self.assertFalse(validate(scene([{"primary":primary,"secondary":value}]),self.snapshot)["valid"])
        raw=scene(conditions=[{"primary":"指定日期","op":"==","secondary":"20260230"}])
        self.assertFalse(validate(raw,self.snapshot)["valid"])

    def test_registry_update_changes_all_three_artifacts_and_rejects_stale_proposal(self):
        raw=scene([{"primary":"香氛开关","secondary":"开启"}])
        p=self.engine.propose(raw,{})
        new=self.reg.set_enabled("fragrance.power",False,self.snapshot["revision"])
        rendered,_=compile_prompt(new,PART/"studies/round2/prompts/p14_zh.md")
        # Instructions can mention fragrance, but it must be absent from generated dictionaries.
        self.assertNotIn("香氛开关",rendered.split("[conditions: primary")[1])
        self.assertNotIn('"const": "香氛开关"',json.dumps(output_schema(new),ensure_ascii=False))
        self.assertFalse(validate(raw,new)["valid"])
        with self.assertRaises(Conflict):self.engine.confirm(p["proposal_id"],"apply_once",self.snapshot["revision"])
        restored=self.reg.set_enabled("fragrance.power",True,new["revision"])
        self.assertNotEqual(restored["revision"],self.snapshot["revision"])

    def test_state_change_between_generation_and_confirmation_is_rechecked(self):
        p=self.engine.propose(scene([{"primary":"主驾车窗","secondary":"100%"}]),{})
        self.assertTrue(p["executable"])
        self.engine.context["driving"]=True
        with self.assertRaises(ValueError):self.engine.confirm(p["proposal_id"],"apply_once",p["registry_revision"])
        self.assertEqual(self.engine.state["vehicle"],{})

    def test_unreleased_is_visible_but_never_executed(self):
        raw=scene([{"primary":"音乐播放","secondary":"放松"}])
        result=validate(raw,self.snapshot)
        self.assertTrue(result["savable"])
        self.assertFalse(result["executable"])
        self.assertTrue(any(d["status"]=="planned" for d in result["decisions"]))

    def test_fake_scene_reference_rejected(self):
        raw={**scene(),"relation":{"type":"extend","scene_id":"someone-elses-scene"}}
        result=validate(raw,self.snapshot,existing_ids=["my-scene"])
        self.assertFalse(result["valid"])
        self.assertTrue(any(d.get("code")=="unknown_scene_reference" for d in result["decisions"]))

    def test_actions_cannot_hide_in_none_or_unknown_fields(self):
        for raw in ({**scene(),"intent":"none"},{**scene(),"execute":True},{**scene(),"memory":[{"type":"preference","content":"x","confidence":float("inf")}]}):
            self.assertFalse(validate(raw,self.snapshot)["valid"])

    def test_save_apply_restore_are_separate_and_idempotency_is_enforced(self):
        saved=self.engine.propose(scene(),{})
        self.engine.confirm(saved["proposal_id"],"save",saved["registry_revision"])
        self.assertEqual(self.engine.state["vehicle"],{})
        applied=self.engine.propose(scene(),{})
        self.engine.confirm(applied["proposal_id"],"apply_once",applied["registry_revision"])
        self.assertEqual(self.engine.state["vehicle"],{"氛围灯亮度":"20%"})
        with self.assertRaises(Conflict):self.engine.confirm(applied["proposal_id"],"apply_once",applied["registry_revision"])
        self.engine.restore(applied["proposal_id"])
        self.assertEqual(self.engine.state["vehicle"],{})
        with self.assertRaises(Conflict):self.engine.restore(applied["proposal_id"])

    def test_conditions_never_applied_immediately_and_timers_require_scheduler(self):
        for raw in (scene(conditions=[{"primary":"电量","op":"<","secondary":"20%"}]),scene([{"primary":"延时","secondary":"2秒"},{"primary":"氛围灯亮度","secondary":"20%"}])):
            p=self.engine.propose(raw,{})
            with self.assertRaises(ValueError):self.engine.confirm(p["proposal_id"],"apply_once",p["registry_revision"])

    def test_revision_preserves_every_unrelated_field(self):
        previous=scene([{"primary":"氛围灯亮度","secondary":"40%"},{"primary":"主驾温度控制","secondary":"24℃"}])
        delta=scene([{"primary":"氛围灯亮度","secondary":"20%"}])
        expected=copy.deepcopy(previous);expected["actions"][0]["secondary"]="20%"
        self.assertEqual(revision(previous,delta,["氛围灯亮度"]),expected)
        with self.assertRaises(ValueError):revision(previous,scene([{"primary":"主驾温度控制","secondary":"20℃"}]),["氛围灯亮度"])

    def test_persistence_and_optimistic_registry_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg=Registry(storage=tmp);engine=Engine(reg,tmp)
            p=engine.propose(scene(),{});engine.confirm(p["proposal_id"],"save",p["registry_revision"])
            self.assertIn(p["proposal_id"],Engine(Registry(storage=tmp),tmp).state["saved"])
            reg.set_enabled("fragrance.power",False,reg.snapshot()["revision"])
            self.assertEqual(next(c for c in Registry(storage=tmp).snapshot()["capabilities"] if c["id"]=="fragrance.power")["status"],"disabled")
            with self.assertRaises(Conflict):reg.set_enabled("fragrance.power",True,p["registry_revision"])


if __name__=="__main__":unittest.main()
