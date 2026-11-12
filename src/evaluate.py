"""Locked external evaluation and patient-cluster bootstrap; no fitting on B."""
import json,joblib,hashlib,time
import numpy as np,pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score,average_precision_score,roc_curve,brier_score_loss
from sklearn.calibration import calibration_curve
from src.load import ROOT
from src.train import predict
from src.baselines import scores
from vendor.official import compute_prediction_utility
METHODS=["vitals","vitals_labs","NEWS2","qSOFA"]
BUDGETS=[float(v)/2 for v in range(1,21)]
N_BOOT=500
def clean(x):
 if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
 if isinstance(x,list):return [clean(v) for v in x]
 if isinstance(x,(np.integer,)):return int(x)
 if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
 return x
def ci(a):
 a=np.asarray(a);a=a[np.isfinite(a)]
 return np.percentile(a,[2.5,97.5]).tolist() if len(a) else [None,None]
def summary(d):
 return {"patients":d.patient_id.nunique(),"hours":len(d),"septic_patients":int(d.groupby("patient_id").SepsisLabel.max().sum()),"positive_hours":int(d.SepsisLabel.sum())}
def conservative_threshold(score,budget):
 # Include complete score ties only if they fit the A validation budget.
 values,counts=np.unique(score,return_counts=True);order=np.argsort(values)[::-1]
 cumulative=np.cumsum(counts[order]);ok=cumulative<=int(len(score)*budget/100)
 return float(values[order][ok][-1]) if ok.any() else float(np.max(score)+1)
def make_context(d):
 groups=list(d.groupby("patient_id",sort=False).indices.values())
 pids=d.patient_id.drop_duplicates().tolist()
 patient=np.empty(len(d),dtype=int)
 y=d.SepsisLabel.to_numpy().astype(int);hour=d.hour.to_numpy()
 onset=np.full(len(groups),np.nan);septic=np.zeros(len(groups),bool);censored=np.zeros(len(groups),bool)
 best=np.zeros(len(groups));inaction=best.copy()
 for i,idx in enumerate(groups):
  patient[idx]=i;lab=y[idx];pos=np.flatnonzero(lab)
  septic[i]=bool(len(pos));censored[i]=bool(len(pos) and pos[0]==0)
  if len(pos) and pos[0]>0:onset[i]=hour[idx[pos[0]]]+6
  opt=np.zeros(len(idx))
  if len(pos):
   t=pos[0]+6;opt[max(0,t-12):min(t+4,len(idx))]=1
  best[i]=compute_prediction_utility(lab,opt,check_errors=False)
  inaction[i]=compute_prediction_utility(lab,np.zeros(len(idx)),check_errors=False)
 eligible=septic&~censored
 useful=np.isfinite(onset[patient])&(hour>=onset[patient]-12)&(hour<onset[patient])
 return dict(groups=groups,patient=patient,pids=pids,y=y,hour=hour,onset=onset,septic=septic,censored=censored,
   eligible=eligible,useful=useful,best=best,inaction=inaction)
def operating(d,c,alarms,draws=None,utility=False):
 n=len(c["groups"]);pid=c["patient"];hours=c["hour"];lengths=np.asarray([len(g) for g in c["groups"]])
 totals=np.bincount(pid,weights=alarms,minlength=n)
 false=np.bincount(pid,weights=alarms&~c["useful"],minlength=n)
 first=np.full(n,np.inf);np.minimum.at(first,pid[alarms&c["useful"]],hours[alarms&c["useful"]])
 warning=c["onset"]-first;caught=np.isfinite(warning)&c["eligible"]
 anyfirst=np.full(n,np.inf);np.minimum.at(anyfirst,pid[alarms],hours[alarms])
 anycaught=(anyfirst<c["onset"])&c["eligible"]
 result={"alert_rate":100*alarms.mean(),"alarms":int(alarms.sum()),"false_alarms":int(false.sum()),
   "caught":int(caught.sum()),"eligible_septic":int(c["eligible"].sum()),
   "caught_pct":100*caught.sum()/max(1,c["eligible"].sum()),
   "any_before_onset_pct":100*anycaught.sum()/max(1,c["eligible"].sum()),
   "catches_per_100_alarms":100*caught.sum()/max(1,alarms.sum()),
   "median_warning":float(np.median(warning[caught])) if caught.any() else np.nan}
 observed=None
 if utility:
  observed=np.array([compute_prediction_utility(c["y"][idx],alarms[idx].astype(int),check_errors=False) for idx in c["groups"]])
  denom=(c["best"]-c["inaction"]).sum()
  result["utility"]=(observed-c["inaction"]).sum()/denom if denom else np.nan
 if draws is not None:
  stats={k:[] for k in ["caught_pct","catches_per_100_alarms","median_warning","false_alarms","alert_rate","any_before_onset_pct"]}
  if utility:stats["utility"]=[]
  for ix in draws:
   denom=c["eligible"][ix].sum();count=caught[ix].sum();alarmcount=totals[ix].sum()
   stats["caught_pct"].append(100*count/denom if denom else np.nan)
   stats["any_before_onset_pct"].append(100*anycaught[ix].sum()/denom if denom else np.nan)
   stats["catches_per_100_alarms"].append(100*count/alarmcount if alarmcount else np.nan)
   w=warning[ix][caught[ix]]
   stats["median_warning"].append(np.median(w) if len(w) else np.nan)
   stats["false_alarms"].append(false[ix].sum())
   stats["alert_rate"].append(100*alarmcount/lengths[ix].sum())
   if utility:
    den=(c["best"][ix]-c["inaction"][ix]).sum()
    stats["utility"].append((observed[ix]-c["inaction"][ix]).sum()/den if den else np.nan)
  result["ci"]={k:ci(v) for k,v in stats.items()}
 return result
def auc_bootstrap(y,s,pid,draws):
 # Sort once. Each replicate assigns multiplicity to every row of each sampled patient.
 order=np.argsort(s,kind="stable")[::-1];ys=y[order];ps=pid[order]
 ends=np.r_[np.flatnonzero(np.diff(s[order])!=0),len(s)-1]
 out={"auroc":[],"auprc":[]}
 n=int(pid.max())+1
 for ix in draws:
  weights=np.bincount(ix,minlength=n)[ps]
  tp=np.cumsum(weights*ys)[ends];fp=np.cumsum(weights*(1-ys))[ends]
  if tp[-1]==0 or fp[-1]==0:continue
  recall=np.r_[0,tp/tp[-1]];fpr=np.r_[0,fp/fp[-1]]
  precision=tp/np.maximum(tp+fp,1)
  out["auroc"].append(np.trapezoid(recall,fpr))
  out["auprc"].append(np.sum(np.diff(recall)*precision))
 return {k:ci(v) for k,v in out.items()}
def evaluate_cohort(d,thresholds,seed):
 c=make_context(d);rng=np.random.default_rng(seed)
 draws=rng.integers(0,len(c["groups"]),size=(N_BOOT,len(c["groups"])),dtype=np.int32)
 result={"cohort":summary(d),"onset_left_censored":int(c["censored"].sum()),"methods":{}}
 # Hash tie-break has no dependence on labels, time, or hospital outcomes.
 keys=(d.patient_id.astype(str)+":"+d.hour.astype(str)).map(lambda s:int(hashlib.sha256(s.encode()).hexdigest()[:12],16)).to_numpy()
 for name in METHODS:
  print("Evaluate",seed,name,flush=True);s=d[name].to_numpy()
  metric={"auroc":roc_auc_score(c["y"],s),"auprc":average_precision_score(c["y"],s),
   "ci":auc_bootstrap(c["y"],s,c["patient"],draws),"threshold":thresholds[name],
   "operating":operating(d,c,s>=thresholds[name],draws,utility=True),"budgets":{},"subgroups":{}}
  ranking=np.lexsort((keys,-s))
  for budget in BUDGETS:
   alarm=np.zeros(len(d),bool);alarm[ranking[:int(len(d)*budget/100)]]=True
   metric["budgets"][str(budget)]=operating(d,c,alarm,draws)
  for label,mask in {"Age <50":d.Age<50,"Age 50-64":d.Age.between(50,64.999),
    "Age 65-79":d.Age.between(65,79.999),"Age 80+":d.Age>=80,
    "Female (0)":d.Gender==0,"Male (1)":d.Gender==1}.items():
   yy=c["y"][mask];ss=s[mask];metric["subgroups"][label]={"hours":int(mask.sum()),"patients":int(d.loc[mask,"patient_id"].nunique()),
    "positive_hours":int(yy.sum()),"auroc":roc_auc_score(yy,ss) if len(np.unique(yy))==2 else np.nan}
   if len(np.unique(yy))==2:
    metric["subgroups"][label]["auroc_ci"]=auc_bootstrap(yy,ss,c["patient"][mask],draws)["auroc"]
  if name.startswith("vitals"):metric["brier"]=brier_score_loss(c["y"],s)
  result["methods"][name]=metric
 return result
def figures(a,b,report):
 colors={"vitals":"#5285bd","vitals_labs":"#0d9488","NEWS2":"#e9983f","qSOFA":"#8b79a9"}
 plt.rcParams.update({"axes.spines.top":False,"axes.spines.right":False,"font.size":11})
 fig,ax=plt.subplots(figsize=(7,5))
 for name in METHODS:
  f,t,_=roc_curve(b.SepsisLabel,b[name]);ax.plot(f,t,label=f"{name} ({report['B']['methods'][name]['auroc']:.3f})",c=colors[name])
 ax.plot([0,1],[0,1],"--",c="#aab7c4");ax.set(xlabel="False positive rate",ylabel="Sensitivity",title="Hospital B | external discrimination");ax.legend()
 fig.tight_layout();fig.savefig(ROOT/"reports/figures/roc.png",dpi=170);plt.close(fig)
 fig,ax=plt.subplots(figsize=(7,5))
 ax.plot([0,1],[0,1],"--",c="#aab7c4")
 extent=.1
 for cohort,d in [("A validation",a),("B external",b)]:
  obs,pred=calibration_curve(d.SepsisLabel,d.vitals_labs,n_bins=10,strategy="quantile")
  ax.plot(pred,obs,"o-",label=cohort)
  extent=max(extent,float(max(np.max(pred),np.max(obs)))*1.12)
 ax.set(xlabel="Mean calibrated model score",ylabel="Observed positive-label fraction",title="Calibration | A-only Platt scaling");ax.set_xlim(0,min(1,extent));ax.set_ylim(0,min(1,extent));ax.legend()
 fig.tight_layout();fig.savefig(ROOT/"reports/figures/calibration.png",dpi=170);plt.close(fig)
 fig,ax=plt.subplots(figsize=(7,5))
 for name in METHODS:
  budgets=report["B"]["methods"][name]["budgets"]
  ax.plot(BUDGETS,[budgets[str(x)]["caught_pct"] for x in BUDGETS],label=name,c=colors[name])
 ax.set(xlabel="Hourly alerts per 100 patient-hours",ylabel="Septic patients caught (%)",title="Hospital B | retrospective matched alarm rates");ax.legend()
 fig.tight_layout();fig.savefig(ROOT/"reports/figures/alarm_budget.png",dpi=170);plt.close(fig)
def demo(b,report):
 from src.explain import explain,nurse_note
 c=make_context(b);threshold=report["thresholds"]["vitals_labs"];news_th=report["thresholds"]["NEWS2"]
 candidates=[]
 for pid,d in b.groupby("patient_id",sort=False):
  pos=d[d.SepsisLabel==1]
  if pos.empty or pos.hour.iloc[0]==1:continue
  onset=int(pos.hour.iloc[0]+6)
  m=d[(d.vitals_labs>=threshold)&(d.hour>=onset-12)&(d.hour<onset)]
  n=d[(d.NEWS2>=news_th)&(d.hour>=onset-12)&(d.hour<onset)]
  if not m.empty:
   first=int(m.hour.iloc[0]);nf=int(n.hour.iloc[0]) if not n.empty else onset+1
   candidates.append((nf-first,onset-first,pid))
 candidates.sort(reverse=True)
 default=candidates[0][2] if candidates else b.patient_id.iloc[0]
 rng=np.random.default_rng(42);others=b.patient_id.unique();others=others[others!=default]
 ids=[default]+rng.choice(others,size=min(299,len(others)),replace=False).tolist()
 bundle=joblib.load(ROOT/"models/vitals_labs.joblib")
 sample=b[b.patient_id.isin(ids)].copy()
 sample.to_parquet(ROOT/"demo/patients.parquet",index=False)
 sample[bundle["features"]+["patient_id","hour"]].to_parquet(ROOT/"demo/features.parquet",index=False)
 # Cache all per-hour SHAP values for the shipped replay patients, in batches.
 import shap
 vals=shap.TreeExplainer(bundle["model"]).shap_values(sample[bundle["features"]])
 if isinstance(vals,list):vals=vals[1]
 vals=np.asarray(vals)
 if vals.ndim==3:vals=vals[:,:,1]
 sf=pd.DataFrame(vals,columns=bundle["features"]);sf["patient_id"]=sample.patient_id.to_numpy();sf["hour"]=sample.hour.to_numpy()
 sf.to_parquet(ROOT/"demo/shap.parquet",index=False)
 report["demo"]={"default_patient":default,"patients":len(ids),"selection":"Default is a deliberately selected illustrative early-warning case; remaining patients are a seeded random sample. Not an evaluation cohort.","default_model_lead":candidates[0][1] if candidates else None}
 return report
def main():
 start=time.time();d=pd.read_parquet(ROOT/"data/processed/features.parquet")
 split=json.loads((ROOT/"models/split.json").read_text())
 a=d[(d.hospital=="A")&d.patient_id.isin(split["validation"])].copy().reset_index(drop=True)
 b=d[d.hospital=="B"].copy().reset_index(drop=True)
 del d
 for name in ["vitals","vitals_labs"]:
  bundle=joblib.load(ROOT/f"models/{name}.joblib")
  a[name]=predict(bundle,a);b[name]=predict(bundle,b)
 for df in [a,b]:
  df["qSOFA"],df["NEWS2"]=scores(df)
 thresholds={n:conservative_threshold(a[n].to_numpy(),5) for n in METHODS}
 print("A-locked thresholds",thresholds,flush=True)
 report={"schema_version":1,"seed":42,"bootstrap_resamples":N_BOOT,
   "thresholds":thresholds,"training":json.loads((ROOT/"models/training.json").read_text()),
   "protocol":{"thresholds":"Conservative 5 hourly alerts/100 hours on A validation; unchanged on B.",
    "budget":"Retrospective label-free within-cohort score ranking, SHA256 patient-hour tie-break; not a prospectively deployable threshold or tuning on B outcomes.",
    "catch":"At least one hourly alert in [inferred onset-12h, inferred onset); first-label-positive patients excluded because onset is left-censored.",
    "false_alarm":"An hourly alert outside the useful pre-onset window, including repeated late/post-onset alerts.",
    "catches_per_100_alarms":"Distinct caught patients / all hourly alerts x100; not hourly PPV.",
    "warning":"Median onset minus first useful alarm, conditional on a catch.",
    "onset":"First positive SepsisLabel hour + 6; inferred, not independently observed. First-hour positives are left-censored.",
    "ci":"500 percentile bootstrap replicates resampling whole patients, fixed model/threshold/ranking; excludes model-training and threshold-selection uncertainty.",
    "auprc":"Average precision (step-function PR area).",
    "calibration":"Platt scaling fitted on held-out A training patients; not refitted on B."}}
 report["A_validation"]=evaluate_cohort(a,thresholds,44)
 report["B"]=evaluate_cohort(b,thresholds,45)
 figures(a,b,report)
 b.to_parquet(ROOT/"data/processed/predictions_B.parquet",index=False)
 # Auditable full-cohort patient-level outcomes, separate from the compact replay bundle.
 patient_results=[]
 for patient_id,group in b.groupby("patient_id",sort=False):
  positive=group[group.SepsisLabel==1]
  censored=not positive.empty and positive.hour.iloc[0]==1
  onset=None if positive.empty or censored else int(positive.hour.iloc[0]+6)
  for method in METHODS:
   alarm=group[group[method]>=thresholds[method]]
   first=None if alarm.empty else int(alarm.hour.iloc[0])
   useful=alarm.iloc[0:0] if onset is None else alarm[(alarm.hour>=onset-12)&(alarm.hour<onset)]
   patient_results.append({"patient_id":patient_id,"method":method,"septic":not positive.empty,
    "left_censored":censored,"inferred_onset":onset,"first_alert":first,
    "any_before_onset":None if onset is None else first is not None and first<onset,
    "caught_in_useful_window":None if onset is None else not useful.empty,
    "warning_hours":None if useful.empty else onset-int(useful.hour.iloc[0])})
 pd.DataFrame(patient_results).to_parquet(ROOT/"data/processed/patient_outcomes_B.parquet",index=False)
 a.to_parquet(ROOT/"data/processed/predictions_A_validation.parquet",index=False)
 report=demo(b,report)
 report["runtime_seconds"]=time.time()-start
 import platform,datetime,importlib.metadata
 report["provenance"]={"evaluated_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "python":platform.python_version(),
  "packages":{k:importlib.metadata.version(k) for k in ["lightgbm","numpy","pandas","scikit-learn","shap"]},
  "model_sha256":{k:hashlib.sha256((ROOT/f"models/{k}.joblib").read_bytes()).hexdigest() for k in ["vitals","vitals_labs"]},
  "raw_manifest":json.loads((ROOT/"data/raw/manifest.json").read_text()) if (ROOT/"data/raw/manifest.json").exists() else None}

 report["citations"]={
  "CDC":{"url":"https://www.cdc.gov/sepsis/about/","adults_yearly":1700000,"deaths_or_hospice":350000},
  "Wong":{"url":"https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/2781307","missed_pct":67,"context":"At the studied threshold, Epic's model missed 67% of sepsis cases; this is a separate study, not a head-to-head comparison."},
  "TREWS":{"url":"https://www.nature.com/articles/s41591-022-01894-0","relative_reduction_pct":18.7,"context":"Provider confirmation within three hours was associated with lower adjusted mortality in an observational cohort; not a randomized causal estimate."},
  "dataset":{"url":"https://physionet.org/content/challenge-2019/1.0.0/","license":"CC BY 4.0"}}
 report=clean(report);(ROOT/"reports/metrics.json").write_text(json.dumps(report,indent=2,allow_nan=False))
 rows=[]
 for name,m in report["B"]["methods"].items():
  rows.append({"method":name,"AUROC":m["auroc"],"AUPRC":m["auprc"],"utility":m["operating"]["utility"],"caught_pct":m["operating"]["caught_pct"],"warning_h":m["operating"]["median_warning"]})
 table=pd.DataFrame(rows)
 table.to_csv(ROOT/"reports/results.csv",index=False)
 print(table.to_string(index=False),flush=True);print("Evaluation seconds",time.time()-start,flush=True)
if __name__=="__main__":main()
