"""Headless browser QA of the live Mac Streamlit server and all tabs."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/screenshots";OUT.mkdir(exist_ok=True,parents=True)
def main():
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  page=browser.new_page(viewport={"width":1440,"height":1100},device_scale_factor=1)
  errors=[];page.on("pageerror",lambda error:errors.append(str(error)))
  page.goto("http://127.0.0.1:8501",wait_until="domcontentloaded",timeout=120000)
  page.get_by_role("tab",name="Patient Replay",exact=True).wait_for(timeout=120000)
  page.get_by_text("Why this score?",exact=True).wait_for(timeout=120000)
  page.wait_for_timeout(1500)
  for name,file in [("Patient Replay","patient_replay"),("Alarm Budget","alarm_budget"),("Trust & Validation","trust_validation"),("About","about")]:
   page.get_by_role("tab",name=name,exact=True).click()
   page.wait_for_timeout(700)
   assert page.locator('[data-testid="stException"]').count()==0
   page.screenshot(path=str(OUT/f"{file}.png"),full_page=True)
  page.get_by_role("tab",name="Alarm Budget",exact=True).click()
  # Keyboard exercises the live budget slider, updating cohort metrics.
  sliders=page.locator('[role="slider"]')
  visible=[s for s in sliders.all() if s.is_visible()]
  if visible:
   visible[-1].focus();page.keyboard.press("End");page.wait_for_timeout(1000)
   assert page.locator('[data-testid="stException"]').count()==0
  # Narrow-screen layout check.
  page.set_viewport_size({"width":390,"height":844})
  page.get_by_role("tab",name="Patient Replay",exact=True).click()
  page.wait_for_timeout(700)
  page.screenshot(path=str(OUT/"mobile.png"),full_page=True)
  assert not errors,errors
  result={"browser":"Chromium","tabs":["Patient Replay","Alarm Budget","Trust & Validation","About"],"screenshots":True,"mobile_viewport":True,"page_errors":errors}
  (ROOT/"reports/browser_verification.json").write_text(json.dumps(result,indent=2))
  print(json.dumps(result,indent=2));browser.close()
if __name__=="__main__":main()
