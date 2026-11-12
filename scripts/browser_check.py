"""Live Chromium QA of all tabs, controls, downloads and mobile layout."""
from pathlib import Path
import json,time
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/screenshots";OUT.mkdir(parents=True,exist_ok=True)
def main():
 start=time.time()
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  page=browser.new_page(viewport={"width":1440,"height":1100},device_scale_factor=1)
  errors=[];page.on("pageerror",lambda error:errors.append(str(error)))
  page.goto("http://127.0.0.1:8501",wait_until="domcontentloaded",timeout=120000)
  page.get_by_text("Why this score?",exact=True).wait_for(timeout=120000)
  def check():
   page.wait_for_timeout(350)
   assert page.locator('[data-testid="stException"]').count()==0
  def tab(name):
   page.get_by_role("tab",name=name,exact=True).click();check()
  def visible(role):
   return [x for x in page.get_by_role(role).all() if x.is_visible()]
  def choose(index):
   visible("combobox")[0].click()
   page.get_by_role("option").nth(index).click();check()
  def key_slider(index,key):
   visible("slider")[index].focus();page.keyboard.press(key);check()
  # Replay limits and alternate patient. Slider is supported even without autoplay.
  tab("Patient Replay");key_slider(0,"Home");key_slider(0,"End")
  choose(1);key_slider(0,"Home")
  page.get_by_text("Latest emitted alert",exact=True).click();check()
  page.get_by_text("Current hour",exact=True).click();check()
  choose(0)
  # Verify both capacity and suppression controls in a real browser.
  tab("Alarm Budget")
  for key in ["Home","End"]:key_slider(0,key)
  for key in ["Home","ArrowRight","End"]:key_slider(1,key)
  choose(1);choose(2);choose(0)
  tab("Trust & Validation")
  for index in [1,4,0]:choose(index)
  with page.expect_download() as download_info:
   page.get_by_text("Download complete metrics",exact=True).click()
  payload=json.loads(Path(download_info.value.path()).read_text())
  assert payload["schema_version"]==2
  tab("About")
  # Fresh context returns to the deliberate default example and default policy.
  page.close();page=browser.new_page(viewport={"width":1440,"height":1100})
  page.on("pageerror",lambda error:errors.append(str(error)))
  page.goto("http://127.0.0.1:8501",wait_until="domcontentloaded")
  page.get_by_text("Why this score?",exact=True).wait_for(timeout=120000)
  for name,file in [("Patient Replay","patient_replay"),("Alarm Budget","alarm_budget"),("Trust & Validation","trust_validation"),("About","about")]:
   tab(name);page.screenshot(path=str(OUT/f"{file}.png"),full_page=True)
  tab("Patient Replay")
  page.get_by_text("Why this score?",exact=True).scroll_into_view_if_needed()
  page.screenshot(path=str(OUT/"explanation.png"),full_page=True)
  page.set_viewport_size({"width":390,"height":844})
  page.locator('[data-testid="stMain"]').evaluate("(element)=>element.scrollTop=0")
  check();page.screenshot(path=str(OUT/"mobile.png"),full_page=True)
  assert not errors,errors
  result={"browser":"Chromium","tabs":["Patient Replay","Alarm Budget","Trust & Validation","About"],
   "controls":["patient picker","replay limits","explanation modes","budget limits","cooldown options","model versions","subgroup methods","metrics download"],
   "screenshots":True,"mobile_viewport":True,"page_errors":errors,"seconds":time.time()-start}
  (ROOT/"reports/browser_verification.json").write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));browser.close()
if __name__=="__main__":main()
