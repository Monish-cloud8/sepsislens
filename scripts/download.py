"""Download every A/B patient from the same public S3 prefix as aws sync.
Falls back to the PhysioNet HTTPS file index if S3 is unavailable.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request, urllib.parse, xml.etree.ElementTree as ET
import re, time, json, shutil, subprocess
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"data/raw"
def get(url):
 for attempt in range(6):
  try:
   with urllib.request.urlopen(url,timeout=90) as r: return r.read()
  except Exception:
   if attempt==5: raise
   time.sleep(2**attempt)
def main():
 RAW.mkdir(parents=True,exist_ok=True)
 if shutil.which("aws"):
  subprocess.run(["aws","s3","sync","--no-sign-request","s3://physionet-open/challenge-2019/1.0.0/training/",str(RAW)],check=True)
  return
 jobs=[]
 prefix="challenge-2019/1.0.0/training/"
 try:
  token=None
  while True:
   q={"list-type":"2","prefix":prefix}
   if token:q["continuation-token"]=token
   tree=ET.fromstring(get("https://physionet-open.s3.amazonaws.com/?"+urllib.parse.urlencode(q)))
   ns={"s":"http://s3.amazonaws.com/doc/2006-03-01/"}
   for node in tree.findall("s:Contents",ns):
    key=node.find("s:Key",ns).text
    if key.endswith(".psv") and any(x in key for x in ["training_setA/","training_setB/"]):
     jobs.append(("https://physionet-open.s3.amazonaws.com/"+key,RAW/key[len(prefix):]))
   token=tree.findtext("s:NextContinuationToken",namespaces=ns)
   if not token:break
  if not jobs:raise RuntimeError("S3 prefix empty")
  source="public S3"
 except Exception as e:
  print("S3 listing unavailable; using PhysioNet HTTPS",repr(e),flush=True)
  for hospital in ["A","B"]:
   url=f"https://physionet.org/files/challenge-2019/1.0.0/training/training_set{hospital}/"
   for name in re.findall(r'href="([^"]+\.psv)"',get(url).decode()):
    jobs.append((url+name,RAW/f"training_set{hospital}"/name))
  source="PhysioNet HTTPS"
 print(f"Downloading {len(jobs)} files from {source}",flush=True)
 def one(job):
  url,path=job
  path.parent.mkdir(parents=True,exist_ok=True)
  if not path.exists():
   payload=get(url)
   if not payload.startswith(b"HR|"):raise ValueError(url)
   tmp=path.with_suffix(".partial");tmp.write_bytes(payload);tmp.replace(path)
 with ThreadPoolExecutor(max_workers=24) as pool:
  for i,_ in enumerate(pool.map(one,jobs)):
   if i%1000==0:print(f"{i}/{len(jobs)}",flush=True)
 (RAW/"manifest.json").write_text(json.dumps({"source":source,"files":len(jobs),"dataset":"https://physionet.org/content/challenge-2019/1.0.0/"},indent=2))
 print("Download complete",flush=True)
if __name__=="__main__":main()
