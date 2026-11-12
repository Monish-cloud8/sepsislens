"""One external pass after model/policy lock. No B-derived thresholds."""
import json,joblib,hashlib,time,datetime,platform
import numpy as np,pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score,average_precision_score,roc_curve,brier_score_loss
from sklearn.calibration import calibration_curve
from src.load import ROOT
from src.evaluate import make_context,operating,auc_bootstrap,summary,clean
from src.refine import score_bundle,stack_inputs
from src.refine_features import extend
from src.train import predict
from src.baselines import scores
from src.alarms import apply_policy,tie_keys
METHODS=["refined","vitals_labs","vitals","NEWS2","qSOFA"]
N_BOOT=500

def evaluate(d,lock,seed):
 c=make_context(d);ties=tie_keys(d)
 draws=np.random.default_rng(seed).integers(0,len(c["groups"]),size=(N_BOOT,len(c["groups"])),dtype=np.int32)
 result={"cohort":summary(d),"onset_left_censored":int(c["censored"].sum()),"methods":{}}
 for method in METHODS:
  print("Evaluate",seed,method,flush=True);s=d[method].to_numpy()
  entry={"auroc":roc_auc_score(c["y"],s),"auprc":average_precision_score(c["y"],s),
   "ci":auc_bootstrap(c["y"],s,c["patient"],draws),"cooldowns":{},"subgroups":{}}
  for cd in lock["cooldowns"]:
   cb={}
   for budget in lock["budgets"]:
    policy=lock["policies"][method][str(cd)][str(budget)]
    alarms=apply_policy(s,c,policy,ties)
    op=operating(d,c,alarms,draws,utility=budget in [2.,5.,10.])
    op["policy"]=policy;cb[str(budget)]=op
   entry["cooldowns"][str(cd)]=cb
  cd=str(lock["selected_cooldown"]);entry["budgets"]=entry["cooldowns"][cd]
  entry["operating"]=entry["budgets"]["5.0"]
  entry["threshold"]=entry["operating"]["policy"]["threshold"]
  for label,mask in {"Age <50":d.Age<50,"Age 50-64":d.Age.between(50,64.999),"Age 65-79":d.Age.between(65,79.999),
   "Age 80+":d.Age>=80,"Female (0)":d.Gender==0,"Male (1)":d.Gender==1}.items():
   yy=c["y"][mask];ss=s[mask]
   sg={"hours":int(mask.sum()),"patients":int(d.loc[mask,"patient_id"].nunique()),"positive_hours":int(yy.sum()),
    "auroc":roc_auc_score(yy,ss) if len(np.unique(yy))==2 else np.nan}
   if len(np.unique(yy))==2:sg["auroc_ci"]=auc_bootstrap(yy,ss,c["patient"][mask],draws)["auroc"]
   entry["subgroups"][label]=sg
  result["methods"][method]=entry
 return result

def plot_figures(a,b,report):
 colors={"refined":"#0d9488","vitals_labs":"#5285bd","vitals":"#8aa2b8","NEWS2":"#db8b25","qSOFA":"#8b79a9"}
 fig,ax=plt.subplots(figsize=(7,5))
 for name in METHODS:
  f,t,_=roc_curve(b.SepsisLabel,b[name]);ax.plot(f,t,label=f"{name} ({report['B']['methods'][name]['auroc']:.3f})",color=colors[name])
 ax.plot([0,1],[0,1],"--",color="#abbccc");ax.set(xlabel="False positive rate",ylabel="Sensitivity",title="Hospital B | hourly challenge-label discrimination");ax.legend();fig.tight_layout();fig.savefig(ROOT/"reports/figures/roc.png",dpi=170);plt.close(fig)
 fig,ax=plt.subplots(figsize=(7,5));extent=.1
 for label,d in [("A validation",a),("B external",b)]:
  observed,expected=calibration_curve(d.SepsisLabel,d.refined,n_bins=10,strategy="quantile")
  ax.plot(expected,observed,"o-",label=label);extent=max(extent,float(max(observed.max(),expected.max()))*1.1)
 ax.plot([0,1],[0,1],"--",color="#abbccc")
 ax.set(xlim=(0,min(1,extent)),ylim=(0,min(1,extent)),xlabel="Mean model score",ylabel="Observed challenge-label fraction",title="Reliability audit | targets may differ");ax.legend();fig.tight_layout();fig.savefig(ROOT/"reports/figures/calibration.png",dpi=170);plt.close(fig)
 fig,ax=plt.subplots(figsize=(7,5))
 for name in ["refined","NEWS2","qSOFA"]:
  vals=report["B"]["methods"][name]["budgets"]
  ax.plot([x["alert_rate"] for x in vals.values()],[x["caught_pct"] for x in vals.values()],"o-",label=name,color=colors[name])
 ax.set(xlabel="Realized B alerts /100 patient-hours",ylabel="Eligible septic patients caught (%)",title="A-locked thresholds | common cooldown");ax.legend();fig.tight_layout();fig.savefig(ROOT/"reports/figures/alarm_budget.png",dpi=170);plt.close(fig)

def make_demo(b,report,bundle,lock):
 c=make_context(b);ties=tie_keys(b);cd=str(lock["selected_cooldown"])
 masks={n:apply_policy(b[n].to_numpy(),c,lock["policies"][n][cd]["5.0"],ties) for n in ["refined","NEWS2"]}
 b=b.copy();b["refined_alert"]=masks["refined"];b["NEWS2_alert"]=masks["NEWS2"]
 examples=[]
 for pid,idx in zip(c["pids"],c["groups"]):
  p=int(c["patient"][idx[0]]);onset=c["onset"][p]
  if not np.isfinite(onset):continue
  first={}
  for name in masks:
   hours=b.hour.to_numpy()[idx][masks[name][idx]&c["useful"][idx]]
   first[name]=int(hours[0]) if len(hours) else None
  if first["refined"] is not None and first["NEWS2"] is not None and first["refined"]<first["NEWS2"]:
   examples.append((first["NEWS2"]-first["refined"],onset-first["refined"],pid,first["refined"],first["NEWS2"],onset))
 # Prefer a real observed later NEWS2 alert; never invent a late alert time.
 examples.sort(reverse=True)
 if examples:
  lead,warning,default,model_hour,news_hour,onset=examples[0]
 else:
  # Honest fallback if no such example exists for the locked policy.
  default=c["pids"][0];lead=warning=model_hour=news_hour=onset=None
 rng=np.random.default_rng(42);others=b.patient_id.unique();others=others[others!=default]
 ids=[default]+rng.choice(others,size=min(299,len(others)),replace=False).tolist()
 sample=b[b.patient_id.isin(ids)].copy()
 sample.to_parquet(ROOT/"demo/patients.parquet",index=False)
 sample[bundle["features"]+["patient_id","hour"]].to_parquet(ROOT/"demo/features.parquet",index=False)
 import shap
 sv=shap.TreeExplainer(bundle["model"]).shap_values(sample[bundle["features"]])
 if isinstance(sv,list):sv=sv[1]
 sv=np.asarray(sv)
 if sv.ndim==3:sv=sv[:,:,1]
 sf=pd.DataFrame(sv,columns=bundle["features"]);sf["patient_id"]=sample.patient_id.to_numpy();sf["hour"]=sample.hour.to_numpy()
 sf.to_parquet(ROOT/"demo/shap.parquet",index=False)
 if "stacker" in bundle:
  # Exact additive final logistic contributions; the base SHAP remains separate.
  raw=predict(bundle,sample);x=stack_inputs(sample,raw)
  scaler,linear=bundle["stacker"].steps[0][1],bundle["stacker"].steps[1][1]
  contrib=scaler.transform(x)*linear.coef_[0]
  names=["base_model_logit","NEWS2","risk_change3","risk_change6","NEWS2_change3","NEWS2_change6"]
  z=pd.DataFrame(contrib,columns=names);z["patient_id"]=sample.patient_id.to_numpy();z["hour"]=sample.hour.to_numpy()
  z.to_parquet(ROOT/"demo/stacker.parquet",index=False)
 elif (ROOT/"demo/stacker.parquet").exists():(ROOT/"demo/stacker.parquet").unlink()
 report["demo"]={"default_patient":default,"patients":len(ids),"default_model_lead":warning,"lead_over_NEWS2":lead,
  "model_alert_hour":model_hour,"NEWS2_alert_hour":news_hour,"inferred_onset":onset,
  "selection":"Automatically selected illustrative B case where both policies alert and the model alerts earlier; not an unbiased performance example. Remaining patients are seeded random draws.",
  "comparison_available":bool(examples),"cooldown":lock["selected_cooldown"]}

def main():
 start=time.time()
 lock=json.loads((ROOT/"models/policy_lock.json").read_text())
 digest=hashlib.sha256((ROOT/"models/refined.joblib").read_bytes()).hexdigest()
 assert digest==lock["refined_model_sha256"],"Model changed after policy lock"
 before=json.loads((ROOT/"reports/before/metrics.json").read_text())
 print("Policy locked; beginning single external evaluation",digest,flush=True)
 a=pd.read_parquet(ROOT/"data/processed/refine_A_validation.parquet")
 # This is the first B access in the refinement pipeline.
 b=pd.read_parquet(ROOT/"data/processed/features.parquet",filters=[("hospital","==","B")])
 if lock["feature_extension"]:b=extend(b)
 bundle=joblib.load(ROOT/"models/refined.joblib")
 for d in [a,b]:
  d["refined"]=score_bundle(bundle,d)
  for name in ["vitals","vitals_labs"]:d[name]=predict(joblib.load(ROOT/f"models/before/{name}.joblib"),d)
  d["qSOFA"],d["NEWS2"]=scores(d)
 b=b.reset_index(drop=True);a=a.reset_index(drop=True)
 report={"schema_version":2,"seed":42,"bootstrap_resamples":N_BOOT,"citations":before["citations"],"selection":lock,
  "thresholds":{n:lock["policies"][n][str(lock["selected_cooldown"])]["5.0"]["threshold"] for n in METHODS},
  "before":before,"training":json.loads((ROOT/"reports/experiments_A.json").read_text()),
  "protocol":{
   "thresholds":"For each target budget and cooldown, fit a label-free threshold grid on A validation only; apply the saved rule unchanged to B. Actual B alert rates may differ. No B quantiles or B threshold search.",
   "budget":"Budget slider specifies an A-validation capacity target, not an exact external B alarm rate. Actual B rates are shown; compare methods using both catches and actual burden.",
   "cooldown":"An alert at hour t suppresses the next N hours for that patient. Earliest repeat is t+N+1. Same selected N applies to every method. No future data is used.",
   "catch":"At least one emitted alert in [inferred onset-12h, inferred onset); first-hour-positive cases excluded from onset metrics.",
   "false_alarm":"An emitted alert outside the evaluable useful pre-onset window, including undefined/left-censored onset. Research workload proxy, not clinically adjudicated false positives.",
   "catches_per_100_alarms":"Distinct caught patients / all emitted alarms x100.",
   "warning":"Median onset minus first useful emitted alert, conditional on a catch.",
   "onset":"First SepsisLabel=1 recording hour + 6. Labels were shifted six hours early. Inferred, not independently observed; first-hour-positive cases are left-censored.",
   "ci":"500 percentile bootstrap resamples of whole patients; frozen model, A-thresholds and causal cooldown sequences. Excludes model-selection/training uncertainty.",
   "utility":"Unmodified official PhysioNet 2019 normalized utility applied to emitted sparse alerts; this score penalizes suppressed hourly positives and is not optimized for episodic alert workflows.",
   "auprc":"Average precision against the original hourly challenge labels, even for models trained on pre-onset targets.",
   "calibration":"Base models use A-only Platt scaling for their training target. A stacked policy score is not a calibrated probability of the challenge label; reliability plots audit that mismatch."}}
 report["A_validation"]=evaluate(a,lock,44);report["B"]=evaluate(b,lock,45)
 # A-compatible before/after comparison in addition to the legacy retrospective table.
 report["comparison"]={}
 for name in ["refined","vitals_labs","NEWS2","qSOFA"]:
  method=report["B"]["methods"][name]
  report["comparison"][name]={"auroc":method["auroc"],"auprc":method["auprc"],"utility":method["operating"]["utility"],
   "catch_at_A_target":{str(b):method["budgets"][str(b)]["caught_pct"] for b in [2.,5.,10.]},
   "actual_B_rates":{str(b):method["budgets"][str(b)]["alert_rate"] for b in [2.,5.,10.]}}
 b.to_parquet(ROOT/"data/processed/refined_predictions_B.parquet",index=False)
 a.to_parquet(ROOT/"data/processed/refined_predictions_A.parquet",index=False)
 make_demo(b,report,bundle,lock);plot_figures(a,b,report)
 report["provenance"]={"evaluated_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"python":platform.python_version(),
  "model_sha256":digest,"policy_lock_sha256":hashlib.sha256((ROOT/"models/policy_lock.json").read_bytes()).hexdigest(),
  "external_model_selection_permitted":False,"runtime_seconds":time.time()-start}
 report=clean(report)
 target=ROOT/"reports/metrics.json";tmp=target.with_suffix(".json.tmp")
 tmp.write_text(json.dumps(report,indent=2,allow_nan=False));tmp.replace(target)
 rows=[]
 for name,entry in report["comparison"].items():
  row={"method":name,"AUROC":entry["auroc"],"AUPRC":entry["auprc"],"utility":entry["utility"]}
  row.update({f"catch_at_{k}":v for k,v in entry["catch_at_A_target"].items()});rows.append(row)
 table=pd.DataFrame(rows);table.to_csv(ROOT/"reports/results.csv",index=False);print(table.to_string(index=False),flush=True)
 print("FINAL EVALUATION COMPLETE",time.time()-start,flush=True)
if __name__=="__main__":main()
