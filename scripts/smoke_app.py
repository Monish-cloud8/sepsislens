"""Exercise all dashboard controls without loading the training dataset."""
from pathlib import Path
import sys,json,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from streamlit.testing.v1 import AppTest
start=time.time();at=AppTest.from_file(str(ROOT/"app/app.py"),default_timeout=120).run()
def check():
 assert not at.exception,[e.message for e in at.exception]
 assert len(at.tabs)==4
def select(label):
 return next(x for x in at.selectbox if x.label==label)
def slider(label):
 return next(x for x in at.slider if x.label==label)
check()
replay=slider("Replay hour");replay.set_value(replay.min).run();check()
replay=slider("Replay hour");replay.set_value(replay.max).run();check()
for choice in ["Latest emitted alert","Current hour"]:
 at.radio[0].set_value(choice).run();check()
picker=select("Hospital B patient");picker.set_value(picker.options[1]).run();check()
for budget in [.5,2.,5.,10.]:
 slider("Target A alerts per 100 patient-hours").set_value(budget).run();check()
for cd in [0,3,6,12]:
 at.select_slider[0].set_value(cd).run();check()
for method in ["vitals","vitals_labs","refined"]:
 select("Model version").set_value(method).run();check()
for method in ["NEWS2","qSOFA","vitals","vitals_labs","refined"]:
 select("Subgroup model").set_value(method).run();check()
result={"apptest_passed":True,"tabs":[t.label for t in at.tabs],
 "interactions":["replay limits","both explanation modes","alternate patient","alarm budgets","all cooldowns","all model versions","all subgroup methods"],
 "exceptions":0,"seconds":time.time()-start}
(ROOT/"reports/verification.json").write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
