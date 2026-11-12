"""SHAP explains the tree's log-odds, not causation or calibrated probability."""
import numpy as np, pandas as pd
UNITS={"HR":"bpm","Resp":"/min","Temp":"C","SBP":"mmHg","MAP":"mmHg","O2Sat":"%","Lactate":"mmol/L"}
def explain(bundle,row,n=35):
 import shap
 x=pd.DataFrame([row])[bundle["features"]]
 values=shap.TreeExplainer(bundle["model"]).shap_values(x)
 if isinstance(values,list):values=values[1]
 values=np.asarray(values).reshape(-1)
 factors=[]
 for i in np.argsort(np.abs(values))[::-1][:n]:
  feature=bundle["features"][i];v=x.iloc[0,i]
  factors.append({"feature":feature,"value":None if pd.isna(v) else float(v),
   "shap":float(values[i]),"direction":"raises risk" if values[i]>0 else "lowers risk"})
 return factors
def nurse_note(factors,risk,threshold):
 pieces=[]
 for f in factors[:5]:
  name=f["feature"];value=f["value"]
  if value is None:detail="not yet observed"
  elif name.endswith("_measured"):detail="measured this hour" if value else "not measured this hour"
  elif name.endswith("_slope6"):detail=f"{value:+.2f} per hour over the last six hours"
  elif name.endswith("_delta"):detail=f"{value:+.1f} since the previous hour"
  else:detail=f"{value:.2f} {UNITS.get(name,'')}".strip()
  names={"HR":"heart rate","Resp":"respiratory rate","MAP":"mean arterial pressure","SBP":"systolic pressure","DBP":"diastolic pressure","O2Sat":"oxygen saturation","Temp":"temperature","Lactate":"lactate","Age":"age","Gender":"recorded sex","shock_index":"shock index"}
  base=name.split("_")[0];label=names.get(name,names.get(base,base))
  for suffix,text in [("_mean6"," six-hour mean"),("_min6"," six-hour minimum"),("_max6"," six-hour maximum"),("_slope6"," six-hour trend"),("_delta"," hourly change"),("_measured"," measurement flag")]:
   if name.endswith(suffix):label+=text
  pieces.append(f"{label}: {detail} ({f['direction']})")
 status="Threshold crossed" if risk>=threshold else "Below the selected threshold"
 return status+". Main model factors: "+"; ".join(pieces)+". Contributions explain the model, not a diagnosis. Carried-forward values may be stale."
