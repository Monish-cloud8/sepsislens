"""Causal features: forward fill within patients; no bfill or admission clocks."""
import numpy as np
import pandas as pd
from src.load import ROOT
VITALS=["HR","Resp","Temp","SBP","MAP","O2Sat"]
LABS=["EtCO2","BaseExcess","HCO3","FiO2","pH","PaCO2","SaO2","AST","BUN","Alkalinephos","Calcium","Chloride","Creatinine","Bilirubin_direct","Glucose","Lactate","Magnesium","Phosphate","Potassium","Bilirubin_total","TroponinI","Hct","Hgb","PTT","WBC","Fibrinogen","Platelets"]
BASE=VITALS+["DBP","Age","Gender"]
def feature_names(labs=True):
 names=BASE+[v+"_"+stat for v in VITALS for stat in ["mean6","min6","max6","slope6","delta"]]+["shock_index"]
 if labs:names+=LABS+[v+"_measured" for v in LABS]
 return names
def slope(a):
 good=np.isfinite(a)
 if good.sum()<2:return np.nan
 x=np.arange(len(a))[good];y=a[good]
 return float(np.dot(x-x.mean(),y-y.mean())/np.dot(x-x.mean(),x-x.mean()))
def transform_patient(d):
 d=d.sort_values("hour").copy()
 measured=d[LABS].notna().astype("float32").add_suffix("_measured")
 d[BASE+LABS]=d[BASE+LABS].ffill()
 out={}
 for v in VITALS:
  r=d[v].rolling(6,min_periods=1)
  out[v+"_mean6"]=r.mean();out[v+"_min6"]=r.min();out[v+"_max6"]=r.max()
  # Slope in units/hour over actual positions, ignoring still-unobserved early values.
  out[v+"_slope6"]=r.apply(slope,raw=True)
  out[v+"_delta"]=d[v].diff()
 out["shock_index"]=d.HR/d.SBP.where(d.SBP>0)
 return pd.concat([d,measured,pd.DataFrame(out,index=d.index)],axis=1)
def main():
 raw=pd.read_parquet(ROOT/"data/processed/hourly.parquet")
 chunks=[]
 for i,(_,d) in enumerate(raw.groupby("patient_id",sort=False)):
  chunks.append(transform_patient(d))
  if i%2000==0:print("Features",i,flush=True)
 result=pd.concat(chunks,ignore_index=True)
 # Explicitly discard shortcut columns from the feature artifact.
 result=result.drop(columns=["ICULOS","HospAdmTime","Unit1","Unit2"],errors="ignore")
 result.to_parquet(ROOT/"data/processed/features.parquet",index=False)
 print("Features complete",result.shape,flush=True)
if __name__=="__main__":main()
