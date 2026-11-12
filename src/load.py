"""Load real hourly patient recordings; hour is metadata, never a model feature."""
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def main():
 frames=[]
 for hospital in ["A","B"]:
  paths=sorted((ROOT/"data/raw"/f"training_set{hospital}").glob("*.psv"))
  if not paths:raise RuntimeError(f"No Hospital {hospital} files; run scripts/download.py")
  for path in paths:
   d=pd.read_csv(path,sep="|",dtype="float32")
   if not d.SepsisLabel.isin([0,1]).all():raise ValueError(f"Invalid labels in {path}")
   d["patient_id"]=hospital+"_"+path.stem
   d["hospital"]=hospital
   d["hour"]=range(1,len(d)+1)
   frames.append(d)
  print(hospital,len(paths),"patients",flush=True)
 d=pd.concat(frames,ignore_index=True)
 d.to_parquet(ROOT/"data/processed/hourly.parquet",index=False)
 print("Hourly rows",len(d),flush=True)
if __name__=="__main__":main()
