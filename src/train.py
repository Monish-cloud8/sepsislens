"""Only Hospital A is read for fitting, tuning, calibration, and thresholds."""
import json, joblib, numpy as np, pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import average_precision_score,roc_auc_score
from sklearn.linear_model import LogisticRegression
from lightgbm import LGBMClassifier, early_stopping
from src.features import feature_names
from src.load import ROOT
def main():
 d=pd.read_parquet(ROOT/"data/processed/features.parquet",filters=[("hospital","==","A")])
 patients=d.groupby("patient_id").SepsisLabel.max()
 train_ids,val_ids=train_test_split(patients.index,test_size=.2,random_state=42,stratify=patients)
 # Calibration uses training patients held out from the base tree fits; A validation remains for selection.
 fit_ids,cal_ids=train_test_split(train_ids,test_size=.15,random_state=43,stratify=patients.loc[train_ids])
 split={"train":list(train_ids),"fit":list(fit_ids),"calibration":list(cal_ids),"validation":list(val_ids),"seed":42}
 (ROOT/"models/split.json").write_text(json.dumps(split))
 tr=d[d.patient_id.isin(fit_ids)];cal=d[d.patient_id.isin(cal_ids)];val=d[d.patient_id.isin(val_ids)]
 metadata={"calibration":{"solver":"liblinear","C":1e6,"max_iter":1000,"tol":1e-8,"selection":"A-only calibration; solver chosen for numerical stability."}}
 for name,labs in [("vitals",False),("vitals_labs",True)]:
  cols=feature_names(labs);best=None;trials=[]
  for leaves in [15,31]:
   model=LGBMClassifier(n_estimators=350,num_leaves=leaves,learning_rate=.04,max_depth=-1,
      min_child_samples=150,reg_lambda=5,colsample_bytree=.85,subsample=.85,subsample_freq=1,
      class_weight="balanced",random_state=42,n_jobs=4,verbosity=-1)
   model.fit(tr[cols],tr.SepsisLabel,eval_set=[(val[cols],val.SepsisLabel)],
      eval_metric="average_precision",callbacks=[early_stopping(35,first_metric_only=False,verbose=False)])
   p=model.predict_proba(val[cols])[:,1];ap=average_precision_score(val.SepsisLabel,p)
   trials.append({"num_leaves":leaves,"validation_auprc":ap,"iterations":model.best_iteration_})
   print(name,trials[-1],flush=True)
   if best is None or ap>best[0]:best=(ap,model)
  model=best[1]
  # Platt scaling on patient-disjoint A calibration data corrects class-weighted risk scores.
  calibrator=LogisticRegression(C=1e6,solver="liblinear",max_iter=1000,tol=1e-8)
  raw=model.predict(cal[cols],raw_score=True)
  calibrator.fit(raw.reshape(-1,1),cal.SepsisLabel)
  bundle={"model":model,"calibrator":calibrator,"features":cols}
  joblib.dump(bundle,ROOT/f"models/{name}.joblib")
  (ROOT/f"models/{name}_features.json").write_text(json.dumps(cols,indent=2))
  metadata[name]={"trials":trials,"selected_validation_auprc":best[0],"n_features":len(cols)}
 (ROOT/"models/training.json").write_text(json.dumps(metadata,indent=2))
 print("Training complete",flush=True)
def predict(bundle,d):
 return bundle["calibrator"].predict_proba(bundle["model"].predict(d[bundle["features"]],raw_score=True).reshape(-1,1))[:,1]
if __name__=="__main__":main()
