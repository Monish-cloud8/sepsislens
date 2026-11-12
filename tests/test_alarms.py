"""Policy tests use small independent examples with known expected answers."""
import numpy as np,pandas as pd,pytest
from src.alarms import suppress,fit_policy,apply_policy,tie_keys,causal_changes
from src.evaluate import make_context,operating
from src.refine_features import extend
from tests.test_protocol import fixture

def test_cooldown_boundary_and_reset_per_patient():
 candidate=np.ones(12,dtype=bool)
 patient=np.repeat([0,1],6);hours=np.tile(np.arange(1,7),2)
 result=suppress(candidate,patient,hours,2)
 assert np.flatnonzero(result).tolist()==[0,3,6,9]
 assert suppress(candidate,patient,hours,0).all()
 with pytest.raises(ValueError):suppress(candidate,patient,hours,-1)

def test_cooldown_uses_elapsed_hours_and_is_causal():
 p=np.zeros(5,dtype=int);h=np.array([1,2,5,6,9])
 out=suppress(np.ones(5,dtype=bool),p,h,3)
 assert out.tolist()==[True,False,True,False,True]
 assert np.array_equal(out[:3],suppress(np.ones(3,dtype=bool),p[:3],h[:3],3))

def test_policy_cannot_be_fitted_on_external_hospital():
 d=pd.DataFrame({"patient_id":["B_x"]*10,"hospital":"B","hour":range(1,11),"SepsisLabel":0})
 with pytest.raises(ValueError):fit_policy(d,np.arange(10),make_context(d),5,3)

def test_budget_is_capacity_not_number_of_patients_and_no_B_refit():
 d=pd.DataFrame({"patient_id":["A_x"]*20,"hospital":"A","hour":range(1,21),"SepsisLabel":[0]*10+[1]*10})
 c=make_context(d);s=np.arange(20)/20
 policy=fit_policy(d,s,c,10,0)
 alarms=apply_policy(s,c,policy,tie_keys(d))
 assert alarms.sum()<=2
 op=operating(d,c,alarms)
 assert op["alert_rate"]==100*alarms.sum()/20
 assert op["catches_per_100_alarms"]==100*op["caught"]/max(1,op["alarms"])
 # Applying the same saved threshold at a shifted hospital changes realized rate.
 external=d.copy();external["patient_id"]="B_x";external["hospital"]="B"
 saved=policy.copy()
 shifted=apply_policy(s+1,c,policy,tie_keys(external))
 assert shifted.sum()>alarms.sum()
 assert policy==saved

def test_no_cooldown_matches_threshold_and_with_cooldown_reduces_burden():
 d=pd.DataFrame({"patient_id":["A_x"]*20,"hospital":"A","hour":range(1,21),"SepsisLabel":[0]*10+[1]*10})
 c=make_context(d);s=np.ones(20);ties=tie_keys(d)
 dense=apply_policy(s,c,{"threshold":.5,"cooldown":0},ties)
 sparse=apply_policy(s,c,{"threshold":.5,"cooldown":3},ties)
 assert dense.sum()==20 and sparse.sum()==5
 assert operating(d,c,sparse,utility=True)["utility"]<=operating(d,c,dense,utility=True)["utility"]

def test_risk_trend_does_not_cross_patient_boundaries():
 d=pd.DataFrame({"patient_id":["a"]*4+["b"]*4})
 trend=causal_changes(d,np.array([1,2,3,4,100,101,102,103]),3)
 assert trend.isna().sum()==6
 assert trend.iloc[3]==3 and trend.iloc[7]==3

def test_longer_windows_are_prefix_invariant():
 d=fixture();full=extend(d);prefix=extend(d.iloc[:4])
 cols=[c for c in full if c.endswith(("12","24","delta3","delta6"))]
 pd.testing.assert_frame_equal(full[cols].iloc[:4],prefix[cols])

def test_emitted_alert_utility_matches_official_reference(tmp_path):
 from vendor.official import evaluate_sepsis_score
 d=pd.DataFrame({"patient_id":["a"]*24+["b"]*24,"hour":list(range(1,25))*2,"SepsisLabel":[0]*12+[1]*12+[0]*24})
 c=make_context(d)
 alerts=suppress(np.ones(48,dtype=bool),c["patient"],c["hour"],3)
 labels=tmp_path/"labels";predictions=tmp_path/"predictions";labels.mkdir();predictions.mkdir()
 for pid,g in d.groupby("patient_id"):
  g[["SepsisLabel"]].to_csv(labels/f"{pid}.psv",sep="|",index=False)
  emitted=alerts[g.index].astype(int)
  pd.DataFrame({"PredictedLabel":emitted,"PredictedProbability":emitted}).to_csv(predictions/f"{pid}.psv",sep="|",index=False)
 expected=evaluate_sepsis_score(str(labels),str(predictions))[-1]
 assert np.isclose(operating(d,c,alerts,utility=True)["utility"],expected)

def test_frozen_report_and_policy_integrity():
 import json,hashlib
 from src.load import ROOT
 if not (ROOT/"models/policy_lock.json").exists():return
 lock=json.loads((ROOT/"models/policy_lock.json").read_text())
 assert hashlib.sha256((ROOT/"models/refined.joblib").read_bytes()).hexdigest()==lock["refined_model_sha256"]
 for method,policies in lock["policies"].items():
  for cooldown,budgets in policies.items():
   for budget,policy in budgets.items():
    assert policy["cooldown"]==int(cooldown)
    assert policy["A_alert_rate"]<=float(budget)+1e-10
