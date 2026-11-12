"""Verify a clean Python 3.11 process serves only shipped artifacts."""
from pathlib import Path
import subprocess,json,shutil,time
ROOT=Path(__file__).resolve().parents[1]
def main():
 python=ROOT/".venv311/bin/python"
 assert python.exists(),"Create the clean Python 3.11 environment first"
 version=subprocess.check_output([str(python),"-c","import platform;print(platform.python_version())"],text=True).strip()
 assert version.startswith("3.11.")
 isolate=ROOT/".demo-check-311";isolate.mkdir(exist_ok=True)
 for folder in ["app","src","demo","models","reports","vendor","scripts",".streamlit"]:
  shutil.copytree(ROOT/folder,isolate/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns("__pycache__","*.pyc","*.log"))
 assert not (isolate/"data").exists()
 subprocess.run([str(python),"scripts/smoke_app.py"],cwd=isolate,check=True)
 log=open(ROOT/"deployment_server.log","w")
 server=subprocess.Popen([str(python),"-m","streamlit","run",str(isolate/"app/app.py"),"--server.address=127.0.0.1","--server.port=8511","--server.headless=true"],cwd=isolate,stdout=log,stderr=log,start_new_session=True)
 try:
  import urllib.request
  for _ in range(40):
   try:
    health=urllib.request.urlopen("http://127.0.0.1:8511/_stcore/health",timeout=2).read().decode()
    if health=="ok":break
   except Exception:time.sleep(.5)
  else:raise AssertionError("Isolated server did not become healthy")
 finally:
  server.terminate();server.wait(timeout=15)
 docker=shutil.which("docker")
 docker_verified=False;docker_reason="Docker executable unavailable on the Mac"
 if docker:
  probe=subprocess.run([docker,"info"],capture_output=True,text=True)
  if probe.returncode==0:
   subprocess.run([docker,"build","-t","sepsislens:verified","."],cwd=ROOT,check=True)
   container=subprocess.check_output([docker,"run","-d","-p","127.0.0.1:8512:8501","sepsislens:verified"],text=True).strip()
   try:
    for _ in range(60):
     try:
      if urllib.request.urlopen("http://127.0.0.1:8512/_stcore/health",timeout=2).read()==b"ok":
       docker_verified=True;break
     except Exception:time.sleep(.5)
    assert docker_verified,"Docker container not healthy"
   finally:subprocess.run([docker,"rm","-f",container],check=True)
  else:docker_reason="Docker installed but daemon unavailable"
 result={"python":version,"python311_demo_only_passed":True,"isolated_app_health":health,
  "training_data_present":False,"docker_verified":docker_verified,"docker_status":"verified" if docker_verified else docker_reason,
  "cloud_published":False}
 (ROOT/"reports/deployment_verification.json").write_text(json.dumps(result,indent=2))
 metrics=ROOT/"reports/metrics.json";m=json.loads(metrics.read_text());m["deployment"]=result;tmp=metrics.with_suffix(".json.tmp");tmp.write_text(json.dumps(m,indent=2,allow_nan=False));tmp.replace(metrics)
 print(json.dumps(result,indent=2))
if __name__=="__main__":main()
