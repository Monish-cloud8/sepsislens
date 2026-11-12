"""A-only experiments. B cannot be read by this module.
Selection: mean patient catch at A-locked 2/5/10 budgets; candidates must not
regress at any budget versus the incumbent at the same cooldown.
"""
import json,joblib,hashlib,time
import numpy as np,pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from lightgbm import LGBMClassifier,early_stopping
from src.load import ROOT
from src.features import feature_names
from src.refine_features import extend,extended_names
from src.train import predict
from src.baselines import scores
from src.alarms import fit_policy,apply_policy,tie_keys,onset_arrays,causal_changes
from src.evaluate import make_context,operating,clean
BUDGETS=[2.,5.,10.]
COOLDOWNS=[0,3,6,12]
def stack_inputs(d,risk):
 _,news=scores(d)
 return np.column_stack([np.log(np.clip(risk,1e-6,1-1e-6)/(1-np.clip(risk,1e-6,1-1e-6))),
  news,causal_changes(d,risk,3).fillna(0),causal_changes(d,risk,6).fillna(0),
  causal_changes(d,news,3).fillna(0),causal_changes(d,news,6).fillna(0)])
def score_bundle(bundle,d):
 from src.train import predict
 raw=predict(bundle,d)
 if "stacker" in bundle:return bundle["stacker"].predict_proba(stack_inputs(d,raw))[:,1]
 return raw
def main():
 start=time.time()
 split=json.loads((ROOT/"models/split.json").read_text())
 d=pd.read_parquet(ROOT/"data/processed/features.parquet",filters=[("hospital","==","A")])
 assert (d.hospital=="A").all()
 print("Extending A causal features",flush=True);d=extend(d)
 d.to_parquet(ROOT/"data/processed/refine_A.parquet",index=False)
 pats=d[d.patient_id.isin(split["validation"])].groupby("patient_id").SepsisLabel.max()
 meta_ids,select_ids=train_test_split(pats.index,test_size=.6,random_state=2026,stratify=pats)
 selection_split={"stack_fit":list(meta_ids),"selection":list(select_ids),"seed":2026}
 (ROOT/"models/refinement_split.json").write_text(json.dumps(selection_split,indent=2))
 tr=d[d.patient_id.isin(split["fit"])].copy().reset_index(drop=True)
 cal=d[d.patient_id.isin(split["calibration"])].copy().reset_index(drop=True)
 val=d[d.patient_id.isin(select_ids)].copy().reset_index(drop=True)
 meta=d[d.patient_id.isin(meta_ids)].copy().reset_index(drop=True)
 c=make_context(val);ties=tie_keys(val)
 onset={name:onset_arrays(df) for name,df in [("tr",tr),("cal",cal)]}
 candidates={}
 def assess(name,bundle):
  s=score_bundle(bundle,val);policies={};counts={}
  for cooldown in COOLDOWNS:
   policies[str(cooldown)]={};counts[str(cooldown)]={}
   for budget in BUDGETS:
    policy=fit_policy(val,s,c,budget,cooldown)
    op=operating(val,c,apply_policy(s,c,policy,ties))
    policies[str(cooldown)][str(budget)]=policy
    counts[str(cooldown)][str(budget)]=op["caught_pct"]
  entry={"candidate":name,"catches":counts,"policies":policies,"training_parameters":bundle.get("parameters",{}),"objective_label":bundle.get("objective_label","hourly"),"stacked":"stacker" in bundle}
  candidates[name]=entry
  joblib.dump(bundle,ROOT/f"models/candidate_{name}.joblib")
  print(name,json.dumps(counts),flush=True)
  (ROOT/"reports/experiments_A.json").write_text(json.dumps(clean({"hospital":"A","selection_split":selection_split,"candidates":candidates}),indent=2))
 baseline=joblib.load(ROOT/"models/before/vitals_labs.joblib");assess("original",baseline)
 configs=[
  ("early6_12",False,"early",31,120,.04,.85),
  ("early6_12_long",True,"early",31,120,.04,.85),
  ("early6_12_smooth",True,"early",15,250,.025,.75),
  ("preonset12_long",True,"preonset",31,120,.04,.85),
  ("preonset12_flexible",True,"preonset",63,80,.03,.95),
  ("hourly_long",True,"hourly",31,150,.04,.85)]
 for name,long,target,leaves,minchild,lr,fraction in configs:
  cols=feature_names()+ (extended_names() if long else [])
  train_y=tr.SepsisLabel.to_numpy().copy();cal_y=cal.SepsisLabel.to_numpy().copy()
  valid=np.ones(len(tr),bool);cal_valid=np.ones(len(cal),bool)
  if target!="hourly":
   for df,key in [(tr,"tr"),(cal,"cal")]:
    lead=onset[key]-df.hour.to_numpy()
    yy=((lead>=6)&(lead<=12)) if target=="early" else ((lead>0)&(lead<=12))
    septic=df.groupby("patient_id").SepsisLabel.transform("max").to_numpy()>0
    use=(~septic)|(np.isfinite(lead)&(lead>0))
    if key=="tr":train_y=yy.astype(int);valid=use
    else:cal_y=yy.astype(int);cal_valid=use
  # Equal total weight per patient prevents long stays from dominating.
  weights=1/tr.groupby("patient_id").hour.transform("count").to_numpy()
  weights=weights/weights.mean()
  model=LGBMClassifier(n_estimators=500,num_leaves=leaves,min_child_samples=minchild,learning_rate=lr,
   colsample_bytree=fraction,subsample=.85,subsample_freq=1,reg_lambda=8,class_weight="balanced",
   n_jobs=4,random_state=42,verbosity=-1,metric="average_precision")
  model.fit(tr.loc[valid,cols],train_y[valid],sample_weight=weights[valid],
    eval_set=[(cal.loc[cal_valid,cols],cal_y[cal_valid])],eval_metric="average_precision",
    callbacks=[early_stopping(40,first_metric_only=True,verbose=False)])
  raw=model.predict(cal.loc[cal_valid,cols],raw_score=True)
  calibrator=LogisticRegression(C=1e6,solver="liblinear",max_iter=1000,tol=1e-8).fit(raw.reshape(-1,1),cal_y[cal_valid])
  bundle={"model":model,"calibrator":calibrator,"features":cols,"objective_label":target,
   "parameters":{"leaves":leaves,"min_child_samples":minchild,"learning_rate":lr,"feature_fraction":fraction,"iterations":model.best_iteration_}}
  assess(name,bundle)
 # Train a simple meta-classifier on a patient-separated slice of A validation.
 # Its assessment uses the other slice only. No in-sample stacking assessment.
 for base in ["original","early6_12_long","preonset12_long","hourly_long"]:
  bundle=joblib.load(ROOT/f"models/candidate_{base}.joblib")
  risk=predict(bundle,meta);mo=onset_arrays(meta);lead=mo-meta.hour.to_numpy()
  septic=meta.groupby("patient_id").SepsisLabel.transform("max").to_numpy()>0
  use=(~septic)|(np.isfinite(lead)&(lead>0))
  target=((lead>0)&(lead<=12)).astype(int)
  stacker=make_pipeline(StandardScaler(),LogisticRegression(C=.1,solver="liblinear",class_weight="balanced",max_iter=1000))
  stacker.fit(stack_inputs(meta,risk)[use],target[use])
  bundle["stacker"]=stacker;bundle["explanation"]="Base-tree SHAP plus exact linear stacker contributions; no causal interpretation."
  assess(base+"_stack",bundle)
 # First select a shared cooldown using original model only on A selection.
 original=candidates["original"]["catches"]
 chosen_cd=max(COOLDOWNS,key=lambda n:(np.mean(list(original[str(n)].values())),-n))
 ref=original[str(chosen_cd)]
 eligible=[name for name,v in candidates.items() if all(v["catches"][str(chosen_cd)][str(b)]>=ref[str(b)]-1e-9 for b in BUDGETS)]
 chosen=max(eligible,key=lambda name:np.mean(list(candidates[name]["catches"][str(chosen_cd)].values())))
 bundle=joblib.load(ROOT/f"models/candidate_{chosen}.joblib")
 joblib.dump(bundle,ROOT/"models/refined.joblib")
 # Fit final thresholds on all A validation (without fitting/choosing on B).
 full=d[d.patient_id.isin(split["validation"])].copy().reset_index(drop=True)
 full.to_parquet(ROOT/"data/processed/refine_A_validation.parquet",index=False)
 fc=make_context(full);q,news=scores(full)
 all_policies={}
 for method,score in [("refined",score_bundle(bundle,full)),("vitals",predict(joblib.load(ROOT/"models/before/vitals.joblib"),full)),
  ("vitals_labs",predict(baseline,full)),("NEWS2",news),("qSOFA",q)]:
  all_policies[method]={str(cd):{str(float(b)):fit_policy(full,score,fc,float(b),cd) for b in [.5,1,1.5,2,2.5,3,3.5,4,4.5,5,5.5,6,6.5,7,7.5,8,8.5,9,9.5,10]} for cd in COOLDOWNS}
 lock={"selected_candidate":chosen,"selected_cooldown":chosen_cd,"selection_rule":"Choose cooldown on original A-selection catches; then choose candidate with highest mean catch@2/5/10, requiring no regression at any budget vs original at that cooldown.",
  "A_selection_reference":ref,"A_selection_selected":candidates[chosen]["catches"][str(chosen_cd)],
  "policies":all_policies,"budgets":[float(x)/2 for x in range(1,21)],"cooldowns":COOLDOWNS,
  "feature_extension":any(x in bundle["features"] for x in extended_names()),"stacked":"stacker" in bundle,
  "A_selection_patients":len(select_ids),"A_stack_fit_patients":len(meta_ids),"runtime_seconds":time.time()-start,
  "refined_model_sha256":hashlib.sha256((ROOT/"models/refined.joblib").read_bytes()).hexdigest()}
 (ROOT/"models/policy_lock.json").write_text(json.dumps(clean(lock),indent=2))
 print("LOCKED",chosen,"cooldown",chosen_cd,"A selection",lock["A_selection_selected"],flush=True)
if __name__=="__main__":main()
