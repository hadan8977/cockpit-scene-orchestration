import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import run_eval as R
import safe_eval as S
from output_contract import driving_reason, schema_errors
from validator import validate_scene

def empty():
    return dict(understanding="", relevance=0, intent="none", name="", logic="AND", conditions=[], actions=[], say="", offer={"type":"none"}, memory=[], unsupported=[], warnings=[], clarify=None)

class Repairs(unittest.TestCase):
    def setUp(self): R.apply_style("p3")
    def test_time(self):
        for x,n in [("07:00",700),("23:59",2359),("00:00",0)]:
            self.assertEqual(R.value_ok("conditions","生效时间",x),(True,n))
        for x in ["25:00","07:60","700时","7bananas"]:
            self.assertFalse(R.value_ok("conditions","生效时间",x)[0])
    def test_units_steps(self):
        self.assertTrue(R.value_ok("actions","主驾温度控制","24℃")[0])
        for x in ["24.5℃","24bananas", "24", "33℃"]:
            self.assertFalse(R.value_ok("actions","主驾温度控制",x)[0])
        self.assertFalse(R.value_ok("actions","氛围灯亮度","20bananas")[0])
    def test_required_and_types(self):
        self.assertFalse(schema_errors(empty()))
        for obj in [{},[],dict(empty(),relevance=True),dict(empty(),actions="bad"),dict(empty(),memory=[{"confidence":"high"}])]:
            self.assertTrue(R.parse_output(obj)["schema_errors"])
    def test_driving(self):
        for p,v in [("氛围灯亮度","100%"),("音乐律动","模式2"),("左前门","开启"),("导航目的地","家"),("主驾车窗","30%"),("腾讯视频","打开")]:
            self.assertIsNotNone(driving_reason(p,v))
            obj=dict(empty(),intent="action",name="测试",actions=[{"primary":p,"secondary":v}])
            ok,scene,_,_=validate_scene(obj,driving=True)
            self.assertFalse(ok); self.assertFalse(scene["actions"])
        for p,v in [("氛围灯亮度","50%"),("音乐律动","关闭"),("主驾车窗","20%"),("腾讯视频","退出")]:
            self.assertIsNone(driving_reason(p,v))
    def test_invalid_condition_cannot_become_unconditional(self):
        obj=dict(empty(),intent="precise",name="测试",conditions=[{"primary":"生效时间","op":"==","secondary":"25:00"}],actions=[{"primary":"空调总开关","secondary":"开启"}])
        ok,scene,_,_=validate_scene(obj)
        self.assertFalse(ok); self.assertEqual(scene["actions"],[])
    def test_bad_memory_no_crash(self):
        validate_scene(dict(empty(),memory=[{"type":"place","content":"x","confidence":"bad"}]))
    def test_strict_json(self):
        for s in ['```json\n{}\n```','{"x":NaN}','{"x":1,"x":2}']:
            with self.assertRaises(ValueError): S.strict_json(s)
    def test_proxy_blocked_before_network(self):
        with patch("requests.post",side_effect=AssertionError("network")):
            with self.assertRaisesRegex(RuntimeError,"disabled"):
                R._call_model_once({"base_url":"https://chatapi.weixin.qq.com/openai/v1"},"","")
    def test_journal_survives_exception(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"raw.jsonl"
            try:
                S.append(p,{"id":"one"}); raise KeyboardInterrupt
            except KeyboardInterrupt: pass
            self.assertEqual(S.read_rows(p),[{"id":"one"}])
    def test_budget_counts_before_call_and_stops(self):
        with tempfile.TemporaryDirectory() as d, patch("safe_eval.balance",return_value=10):
            b=S.Budget(Path(d)/"budget.json","fake",max_attempts=1)
            b.start("r",["x"],"s","u",100)
            with self.assertRaisesRegex(RuntimeError,"attempt budget"):
                b.start("r",["y"],"s","u",100)
            b2=S.Budget(Path(d)/"budget.json","fake",max_attempts=1)
            self.assertEqual(len(b2.data["attempts"]),1)
    def test_balance_reserve(self):
        with tempfile.TemporaryDirectory() as d, patch("safe_eval.balance",return_value=3.001):
            b=S.Budget(Path(d)/"budget.json","fake")
            with self.assertRaisesRegex(RuntimeError,"reserve"):
                b.start("r",["x"],"s","u",1000)

if __name__ == "__main__": unittest.main(verbosity=2)
