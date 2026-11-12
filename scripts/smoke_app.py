"""Exercise Streamlit execution and widgets against the real shipped bundle."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from streamlit.testing.v1 import AppTest
at=AppTest.from_file(str(ROOT/"app/app.py"),default_timeout=120).run()
def check():
 assert not at.exception,[e.message for e in at.exception]
 assert len(at.tabs)==4
check()
at.slider[0].set_value(at.slider[0].min).run();check()
at.radio[0].set_value("First threshold alert").run();check()
at.selectbox[0].set_value(at.selectbox[0].options[1]).run();check()
at.slider[1].set_value(10.).run();check()
at.slider[1].set_value(.5).run();check()
at.selectbox[1].set_value("vitals").run();check()
result={"apptest_passed":True,"tabs":[t.label for t in at.tabs],"interactions":["hour slider","first-alert explanation","alternate patient","alarm budget extremes","model version"],"exceptions":0}
(ROOT/"reports/verification.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
