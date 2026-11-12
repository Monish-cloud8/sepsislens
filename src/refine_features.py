"""Extended features from current and past observations only."""
import numpy as np,pandas as pd
from src.features import VITALS,slope
from src.baselines import scores
KEY_LABS=["Lactate","WBC","Creatinine","Platelets","Bilirubin_total"]
def extended_names():
 return [v+"_"+stat+str(w) for v in VITALS+KEY_LABS for w in [12,24] for stat in ["mean","min","max","slope"]]+["NEWS2","NEWS2_delta3","NEWS2_delta6"]
def extend(d):
 pieces=[]
 for _,g in d.groupby("patient_id",sort=False):
  g=g.sort_values("hour").copy();out={}
  for v in VITALS+KEY_LABS:
   for w in [12,24]:
    r=g[v].rolling(w,min_periods=1)
    out[v+"_mean"+str(w)]=r.mean()
    out[v+"_min"+str(w)]=r.min()
    out[v+"_max"+str(w)]=r.max()
    out[v+"_slope"+str(w)]=r.apply(slope,raw=True)
  _,news=scores(g);out["NEWS2"]=news
  for lag in [3,6]:out["NEWS2_delta"+str(lag)]=pd.Series(news,index=g.index).diff(lag)
  pieces.append(pd.concat([g.drop(columns=["NEWS2"],errors="ignore"),pd.DataFrame(out,index=g.index)],axis=1))
 return pd.concat(pieces,ignore_index=True)
