from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
files=[p for folder in ["app","src","demo","models","reports","vendor",".streamlit"] for p in (ROOT/folder).rglob("*") if p.is_file() and "__pycache__" not in str(p)]
size=sum(p.stat().st_size for p in files)
assert size<100_000_000,f"Bundle too large: {size}"
m=json.loads((ROOT/"reports/metrics.json").read_text())
assert m["bootstrap_resamples"]==500
assert m["B"]["cohort"]["patients"]==20000
print(json.dumps({"serving_bundle_bytes":size,"files":len(files),"under_100MB":True},indent=2))
