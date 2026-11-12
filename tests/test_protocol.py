import json
import numpy as np,pandas as pd
from src.features import transform_patient,feature_names,LABS,BASE
from src.baselines import scores
from src.evaluate import conservative_threshold,auc_bootstrap,make_context,operating
from src.load import ROOT
from vendor.official import evaluate_sepsis_score
def fixture():
 d=pd.DataFrame({c:[np.nan,10.,20.,30.,40.,50.,60.,70.] for c in set(BASE+LABS)})
 d["hour"]=range(1,9);d["patient_id"]="A_fake";d["hospital"]="A";d["SepsisLabel"]=0
 return d
def test_features_are_causal_and_clock_free():
 d=fixture();all_=transform_patient(d)
 prefix=transform_patient(d.iloc[:4])
 pd.testing.assert_frame_equal(all_.iloc[:4][feature_names()],prefix[feature_names()])
 changed=d.copy();changed.loc[4:,BASE+LABS]=9999
 pd.testing.assert_frame_equal(all_.iloc[:4][feature_names()],transform_patient(changed).iloc[:4][feature_names()])
 assert np.isnan(all_.iloc[0].HR)
 assert all_.iloc[1].Lactate_measured==1
 assert not set(feature_names())&{"ICULOS","HospAdmTime","hour","patient_id","hospital","SepsisLabel"}
def test_patient_boundaries_do_not_forward_fill():
 a=fixture();b=fixture();b.patient_id="B_fake";b.loc[:,BASE+LABS]=np.nan
 out=pd.concat([transform_patient(x) for x in [a,b]])
 assert out[out.patient_id=="B_fake"].HR.isna().all()
def test_baseline_boundaries():
 d=pd.DataFrame({"Resp":[22.,8.,25.,16.],"SBP":[100.,90.,220.,120.],"O2Sat":[98.,91.,95.,98.],"HR":[80.,40.,130.5,80.],"Temp":[37.,35.,39.1,37.]})
 q,n=scores(d)
 assert q.tolist()==[2,1,1,0]
 assert n.tolist()==[4,15,12,0]
def test_threshold_never_exceeds_budget_with_ties():
 s=np.array([0]*90+[1]*10)
 t=conservative_threshold(s,5)
 assert (s>=t).mean()<=.05
def test_splits_are_patient_disjoint():
 p=ROOT/"models/split.json"
 if not p.exists():return
 s=json.loads(p.read_text())
 assert not set(s["train"])&set(s["validation"])
 assert not set(s["fit"])&set(s["calibration"])
 assert all(x.startswith("A_") for k in ["train","validation","calibration"] for x in s[k])
def test_auc_bootstrap_matches_sklearn_for_fixed_draw():
 from sklearn.metrics import roc_auc_score,average_precision_score
 y=np.array([0,1,1,0,0,1]);s=np.array([.1,.5,.5,.8,.2,.9]);pid=np.array([0,0,1,1,2,2])
 result=auc_bootstrap(y,s,pid,np.array([[0,1,2]]))
 assert np.isclose(result["auroc"][0],roc_auc_score(y,s))
 assert np.isclose(result["auprc"][0],average_precision_score(y,s))
def test_official_utility_parity(tmp_path):
 d=pd.DataFrame({"patient_id":["a"]*20+["b"]*20,"hour":list(range(1,21))*2,
  "SepsisLabel":[0]*10+[1]*10+[0]*20})
 alarms=np.array([0]*7+[1]*6+[0]*7+[0]*20,dtype=bool)
 c=make_context(d);got=operating(d,c,alarms,utility=True)["utility"]
 labels=tmp_path/"labels";pred=tmp_path/"pred";labels.mkdir();pred.mkdir()
 for i,(pid,group) in enumerate(d.groupby("patient_id")):
  pd.DataFrame({"SepsisLabel":group.SepsisLabel}).to_csv(labels/f"{pid}.psv",sep="|",index=False)
  ar=alarms[group.index].astype(int)
  pd.DataFrame({"PredictedLabel":ar,"PredictedProbability":ar}).to_csv(pred/f"{pid}.psv",sep="|",index=False)
 expected=evaluate_sepsis_score(str(labels),str(pred))[-1]
 assert np.isclose(got,expected)
def test_left_censored_excluded_from_warning_not_hourly():
 d=pd.DataFrame({"patient_id":["a"]*5,"hour":range(1,6),"SepsisLabel":[1]*5})
 c=make_context(d)
 assert c["censored"].sum()==1
 assert c["eligible"].sum()==0

def test_cluster_bootstrap_preserves_duplicate_patient_weight():
 from sklearn.metrics import roc_auc_score,average_precision_score
 y=np.array([0,1,1,0,0,1]);s=np.array([.1,.5,.5,.8,.2,.9]);pid=np.array([0,0,1,1,2,2])
 result=auc_bootstrap(y,s,pid,np.array([[0,0,2]]))
 rows=np.array([0,1,0,1,4,5])
 assert np.isclose(result["auroc"][0],roc_auc_score(y[rows],s[rows]))
 assert np.isclose(result["auprc"][0],average_precision_score(y[rows],s[rows]))
def test_catches_are_distinct_and_hourly_alarms_repeat():
 d=pd.DataFrame({"patient_id":["a"]*20,"hour":range(1,21),"SepsisLabel":[0]*10+[1]*10})
 alarms=np.ones(20,dtype=bool);c=make_context(d)
 op=operating(d,c,alarms)
 assert op["alarms"]==20
 assert op["caught"]==1
 assert op["catches_per_100_alarms"]==5
 assert op["median_warning"]==12
 assert op["any_before_onset_pct"]==100

def test_trained_models_have_finite_monotone_calibration_and_safe_features():
 import joblib
 for name in ["vitals","vitals_labs"]:
  path=ROOT/f"models/{name}.joblib"
  if not path.exists():continue
  b=joblib.load(path)
  assert not set(b["features"])&{"hour","ICULOS","HospAdmTime","SepsisLabel","patient_id","hospital"}
  c=b["calibrator"]
  assert np.isfinite(c.coef_).all() and c.coef_[0,0]>0
  assert np.isfinite(c.intercept_).all()
  assert c.n_iter_.max()<c.max_iter
  assert np.isfinite(c.predict_proba(np.array([[-10.],[0.],[10.]]))).all()
