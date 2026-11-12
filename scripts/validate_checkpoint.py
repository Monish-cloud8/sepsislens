"""Allow a resumed pipeline to reuse a completed, matching external pass."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 m=json.loads((ROOT/"reports/metrics.json").read_text())
 lock=ROOT/"models/policy_lock.json"
 digest=hashlib.sha256((ROOT/"models/refined.joblib").read_bytes()).hexdigest()
 assert digest==m["provenance"]["model_sha256"]
 assert hashlib.sha256(lock.read_bytes()).hexdigest()==m["provenance"]["policy_lock_sha256"]
 assert m["schema_version"]==2
 assert m["bootstrap_resamples"]==500
 assert m["B"]["cohort"]["patients"]==20000
 for name in ["refined","vitals_labs","vitals","NEWS2","qSOFA"]:
  assert set(m["B"]["methods"][name]["cooldowns"])=={"0","3","6","12"}
 print("Completed external report matches the frozen model and policy; reusing it without another B pass.")
if __name__=="__main__":main()
