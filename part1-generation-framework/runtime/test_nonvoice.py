import copy
import unittest
from core import Registry, validate
from scheduler import RuntimeEngine
from test_core import scene


def phased():
    return {**scene([
        {"primary":"前排风量调节","secondary":"3挡"},
        {"primary":"主驾座椅通风","secondary":"2挡"},
        {"primary":"延时","secondary":"300秒"},
        {"primary":"前排风量调节","secondary":"2挡"},
        {"primary":"主驾座椅通风","secondary":"1挡"},
    ]),"intent":"observation","relevance":.9}


class NonVoiceTests(unittest.TestCase):
    def setUp(self):
        self.registry=Registry();self.engine=RuntimeEngine(self.registry)
        self.engine.update_vehicle({"前排风量调节":"1挡","主驾座椅通风":"关闭"},False)

    def start(self,raw=None):
        p=self.engine.propose(raw or phased(),{})
        self.assertTrue(p["executable"],p["decisions"])
        self.engine.confirm(p["proposal_id"],"apply_once",p["registry_revision"],trial=False)
        return p

    def test_cross_phase_changes_are_valid_and_immediate_confirm_has_no_trial_delay(self):
        p=self.start()
        self.assertEqual(self.engine.state["vehicle"]["前排风量调节"],"3挡")
        self.engine.advance(299)
        self.assertEqual(self.engine.state["vehicle"]["前排风量调节"],"3挡")
        self.engine.advance(1)
        self.assertEqual(self.engine.state["vehicle"]["前排风量调节"],"2挡")
        self.assertEqual(self.engine.state["vehicle"]["主驾座椅通风"],"1挡")
        self.engine.restore(p["proposal_id"])
        self.assertEqual(self.engine.state["vehicle"],{"前排风量调节":"1挡","主驾座椅通风":"关闭"})

    def test_same_phase_duplicate_and_illegal_delay_are_rejected(self):
        raw=phased();raw["actions"].pop(2)
        self.assertFalse(validate(raw,self.registry.snapshot())["valid"])
        raw=phased();raw["actions"][2]["secondary"]="-1秒"
        self.assertFalse(validate(raw,self.registry.snapshot())["valid"])

    def test_manual_override_cancels_only_its_pending_device_and_survives_restore(self):
        p=self.start();self.engine.manual_override({"前排风量调节":"4挡"},False)
        self.engine.advance(300)
        self.assertEqual(self.engine.state["vehicle"]["前排风量调节"],"4挡")
        self.assertEqual(self.engine.state["vehicle"]["主驾座椅通风"],"1挡")
        self.engine.restore(p["proposal_id"])
        self.assertEqual(self.engine.state["vehicle"]["前排风量调节"],"4挡")
        self.assertEqual(self.engine.state["vehicle"]["主驾座椅通风"],"关闭")

    def test_restore_cancels_future_segments(self):
        p=self.start();self.engine.restore(p["proposal_id"]);self.engine.advance(300)
        self.assertEqual(self.engine.state["vehicle"]["前排风量调节"],"1挡")
        self.assertFalse(any(j["status"]=="pending" for j in self.engine.state["timeline"]))

    def test_full_timed_modify_retains_stages(self):
        raw=phased();p=self.engine.propose(raw,{})
        self.engine.confirm(p["proposal_id"],"save",p["registry_revision"])
        revised=copy.deepcopy(raw);revised["actions"][3]["secondary"]="1挡"
        revised["relation"]={"type":"modify","scene_id":p["proposal_id"]}
        q=self.engine.propose(revised,{})
        self.engine.confirm(q["proposal_id"],"save",q["registry_revision"])
        self.assertEqual(self.engine.state["saved"][p["proposal_id"]]["scene"]["actions"],revised["actions"])

    def test_next_trip_rearms_but_continuously_true_does_not_repeat(self):
        raw=scene(conditions=[{"primary":"挡位","secondary":"挡位P","op":"=="}])
        p=self.engine.propose(raw,{})
        self.engine.confirm(p["proposal_id"],"save",p["registry_revision"])
        self.engine.update_vehicle({"挡位":"挡位P"},False)
        self.assertEqual(len(self.engine.trigger(trial=False)),1)
        self.assertEqual(self.engine.trigger(trial=False),[])
        self.assertEqual(len(self.engine.trigger(trial=False,new_trip=True)),1)


if __name__=="__main__":unittest.main()
