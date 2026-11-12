"""Causal alert policy. Policy fitting is permitted on Hospital A only."""
import numpy as np
import pandas as pd
from numba import njit

@njit(cache=True)
def _suppress(candidate,patient,hour,cooldown):
 out=np.zeros(len(candidate),np.bool_)
 last=np.full(int(patient.max())+1,-1e12)
 for i in range(len(candidate)):
  p=patient[i]
  if candidate[i] and hour[i]-last[p]>cooldown:
   out[i]=True
   last[p]=hour[i]
 return out

def suppress(candidate,patient,hour,cooldown):
 """An alert at t suppresses t+1,...,t+N; t+N+1 is eligible again."""
 if cooldown<0:raise ValueError("Cooldown must be nonnegative")
 candidate=np.asarray(candidate,dtype=bool)
 if not len(candidate):return candidate.copy()
 return _suppress(candidate,np.asarray(patient,dtype=np.int64),np.asarray(hour,dtype=float),int(cooldown))

def tie_keys(d):
 return pd.util.hash_pandas_object(d.patient_id.astype(str)+":"+d.hour.astype(str),index=False).to_numpy(dtype=np.uint64).astype(float)/float(2**64)

def priority(score,ties):
 # Integer baselines use a fixed fractional tie-break. Continuous scores use the
 # same tiny deterministic perturbation. Neither labels nor future values enter.
 return np.asarray(score,dtype=float)+1e-7*np.asarray(ties)

def apply_policy(score,c,policy,ties):
 return suppress(priority(score,ties)>=policy["threshold"],c["patient"],c["hour"],policy["cooldown"])

def fit_policy(d,score,c,budget,cooldown):
 if not (d.hospital=="A").all():raise ValueError("Policies must be fitted on Hospital A only")
 ties=tie_keys(d);s=priority(score,ties)
 # Cooldown may make the count nonmonotonic in threshold for arbitrary scores.
 # Search a fixed A quantile grid, then choose the fullest rule below capacity.
 fractions=np.unique(np.r_[0,np.geomspace(.0001,.3,100),np.linspace(.3,1,40)])
 thresholds=np.unique(np.r_[np.nextafter(s.max(),np.inf),np.quantile(s,1-fractions)])
 best=None
 target=int(len(d)*budget/100)
 for threshold in thresholds:
  alarms=suppress(s>=threshold,c["patient"],c["hour"],cooldown)
  count=int(alarms.sum())
  if count<=target and (best is None or count>best[0]):best=(count,float(threshold))
 return {"threshold":best[1],"cooldown":int(cooldown),"target_budget":float(budget),"A_alert_rate":100*best[0]/len(d)}

def causal_changes(d,values,lag):
 series=pd.Series(np.asarray(values),index=d.index)
 return series-series.groupby(d.patient_id,sort=False).shift(lag)

def onset_arrays(d):
 onset=d.groupby("patient_id").apply(lambda x:np.nan if not (x.SepsisLabel==1).any() or x.SepsisLabel.iloc[0]==1 else float(x.loc[x.SepsisLabel==1,"hour"].iloc[0]+6),include_groups=False)
 return d.patient_id.map(onset).to_numpy()
