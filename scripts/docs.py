"""Generate documentation from the evaluated report; no performance constants."""
import json
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def f(value,d=3):
 return "N/A" if value is None else f"{value:.{d}f}"
def comparison(m,legacy=True):
 rows=[]
 if legacy:
  for name in ["vitals_labs","NEWS2","qSOFA"]:
   v=m["before"]["B"]["methods"][name]
   rows.append(["Before: legacy B ranking",name,v["auroc"],v["auprc"],v["operating"]["utility"]]+[v["budgets"][str(b)]["caught_pct"] for b in [2.,5.,10.]])
 else:
  for name in ["vitals_labs","NEWS2","qSOFA"]:
   v=m["B"]["methods"][name];ops=v["cooldowns"]["0"]
   rows.append(["Before: A-locked, no cooldown",name,v["auroc"],v["auprc"],ops["5.0"]["utility"]]+[ops[str(b)]["caught_pct"] for b in [2.,5.,10.]])
 for name in ["refined","NEWS2","qSOFA"]:
  v=m["B"]["methods"][name]
  rows.append(["After: A-locked, shared cooldown",name,v["auroc"],v["auprc"],v["operating"]["utility"]]+[v["budgets"][str(b)]["caught_pct"] for b in [2.,5.,10.]])
 table="| Version | Method | AUROC | AUPRC | Official utility | Caught at 2 (%) | At 5 (%) | At 10 (%) |\n|---|---|---|---|---|---|---|---|\n"
 for version,name,roc,pr,utility,*catch in rows:
  table+="| "+" | ".join([version,name,f(roc),f(pr,4),f(utility,4)]+[f(x,1) for x in catch])+" |\n"
 return table
def main():
 m=json.loads((ROOT/"reports/metrics.json").read_text());sel=m["selection"];model=m["B"]["methods"]["refined"]
 legacy=comparison(m,True);fair=comparison(m,False)
 rates="| Method | A target | Actual B alarms/100h | Caught (%) | Catches/100 alarms | Median warning h |\n|---|---|---|---|---|---|\n"
 for name in ["refined","NEWS2","qSOFA"]:
  for budget in [2.,5.,10.]:
   op=m["B"]["methods"][name]["budgets"][str(budget)]
   rates+="| "+" | ".join([name,f(budget,0),f(op["alert_rate"],2),f(op["caught_pct"],1),f(op["catches_per_100_alarms"],2),f(op["median_warning"],1)])+" |\n"
 experiment="| Candidate | A caught at 2 (%) | At 5 (%) | At 10 (%) | Retained |\n|---|---|---|---|---|\n"
 for name,candidate in m["training"]["candidates"].items():
  vals=candidate["catches"][str(sel["selected_cooldown"])]
  experiment+="| "+" | ".join([name]+[f(vals[str(b)],1) for b in [2.,5.,10.]]+["yes" if name==sel["selected_candidate"] else "no"])+" |\n"
 subgroup="| Group | Patients | Positive hours | AUROC (95% CI) |\n|---|---|---|---|\n"
 for group,v in model["subgroups"].items():
  ci=v.get("auroc_ci",[None,None])
  subgroup+=f'| {group} | {v["patients"]} | {v["positive_hours"]} | {f(v["auroc"])} ({f(ci[0])} - {f(ci[1])}) |\n'
 protocol="\n".join("- **"+k.replace("_"," ").title()+"**: "+v for k,v in m["protocol"].items())
 limitations="""This is retrospective methodological research, not evidence of clinical benefit. **Not for clinical use.** Missingness/test ordering and carried-forward measurements can reflect local workflow. First-hour-positive recordings have left-censored onset: they remain in hourly discrimination/utility but are excluded from onset-based catches and warning-time denominators. Some inferred onsets fall beyond the recording.
The original B evaluation has already been seen. This refinement is A-only development followed by another external check on the same B cohort, not a new untouched confirmatory study. Do not claim B is a pristine final holdout for future iterations. No B threshold quantiles or B model selection are used in this run.
A validation is used for development, so its performance is optimistic. Stacker fitting uses a separate patient slice from candidate assessment. Bootstrap intervals freeze the selected model, thresholds and alert sequences; they omit training/selection uncertainty.
Cooldown lowers repeated burden but also limits maximum attainable alarm rate. A target may be unattainable; B rates can drift in either direction. Read actual B rates beside catches. The official hourly utility penalizes suppressed positive hours and is not an episodic-alert utility. It is reported without changing the reference scoring logic.
Outside-window alarms are not adjudicated clinical false positives. They include records with undefined/left-censored onset. NEWS2-style omits consciousness, supplemental oxygen and scale-2 eligibility; qSOFA-style omits mental status. Missing components contribute zero. These partial scores are not validated clinical NEWS2/qSOFA.
Binary recorded sex and age bands are incomplete fairness audits. The default replay is automatically chosen to illustrate an early model alert; it is deliberately selected, not representative performance evidence.
"""
 citations="""Dataset: Reyna MA et al. Early Prediction of Sepsis From Clinical Data: The PhysioNet/Computing in Cardiology Challenge 2019. Critical Care Medicine. 2020;48(2):210-217. [DOI](https://doi.org/10.1097/CCM.0000000000004145). [PhysioNet v1.0.0](https://physionet.org/content/challenge-2019/1.0.0/), CC BY 4.0. Demo patient values/derived records retain this attribution.
The unmodified [official PhysioNet 2019 evaluator](https://github.com/physionetchallenges/evaluation-2019) is in vendor/official.py with its BSD license. Project code uses MIT; data licensing remains separate.
"""
 r5,n5,r2,n2=[m["B"]["methods"][a]["budgets"][b] for a,b in [("refined","5.0"),("NEWS2","5.0"),("refined","2.0"),("NEWS2","2.0")]]
 fa_cut=100*(1-r5["false_alarms"]/n5["false_alarms"])
 headline=f"""## Headline (Hospital B, never used for training)
At a nominal budget of 5 alerts per 100 patient-hours with a {sel["selected_cooldown"]}-hour cooldown, SepsisLens caught **{r5["caught_pct"]:.1f}%** of eligible septic patients ({r5["caught"]}/{r5["eligible_septic"]}) versus **{n5["caught_pct"]:.1f}%** for a NEWS2-style score ({n5["caught"]}/{n5["eligible_septic"]}), with **{fa_cut:.1f}% fewer outside-window alarms** ({r5["false_alarms"]:,} vs {n5["false_alarms"]:,}). Median warning: {r5["median_warning"]:.0f} h vs {n5["median_warning"]:.0f} h. Hourly AUROC {model["auroc"]:.3f} vs {m["B"]["methods"]["NEWS2"]["auroc"]:.3f}.
**Honest limits of that claim:**
- The 5-per-100h figure is the *target* thresholds were fit to on Hospital A. Realized Hospital B rates were {r5["alert_rate"]:.2f} (model) and {n5["alert_rate"]:.2f} (NEWS2) alerts per 100 patient-hours, so the model also fired fewer alarms.
- The catch-rate gap is small: 95% patient-bootstrap intervals overlap ({r5["ci"]["caught_pct"][0]:.1f}-{r5["ci"]["caught_pct"][1]:.1f}% vs {n5["ci"]["caught_pct"][0]:.1f}-{n5["ci"]["caught_pct"][1]:.1f}%); a separate paired bootstrap on the saved predictions gave a +2.0 pp difference with a 95% interval of about -1.6 to +5.6 pp, so we do not claim a statistically significant catch gain. The clearer advantage is fewer alarms per catch.
- **At a 2-per-100h budget NEWS2 catches slightly more** ({n2["caught_pct"]:.1f}% vs {r2["caught_pct"]:.1f}%), but its realized rate is about twice as high ({n2["alert_rate"]:.2f} vs {r2["alert_rate"]:.2f} per 100 h). At 10 per 100 h both methods tie ({r5 and m["B"]["methods"]["refined"]["budgets"]["10.0"]["caught_pct"]:.1f}%).
- **At equal realized alarm burden the gap is larger** (read from the budget curves by linear interpolation, point estimates without intervals): {np.interp(n5["alert_rate"],[v["alert_rate"] for v in m["B"]["methods"]["refined"]["cooldowns"][str(sel["selected_cooldown"])].values()],[v["caught_pct"] for v in m["B"]["methods"]["refined"]["cooldowns"][str(sel["selected_cooldown"])].values()]):.1f}% (model) vs {n5["caught_pct"]:.1f}% (NEWS2) at NEWS2's {n5["alert_rate"]:.2f} alerts per 100 h.
- Part of the improvement comes from the shared alert cooldown policy, not only the model.
- The default replay patient was chosen to illustrate an early alert; it is not representative. In the 300-patient replay sample (25 evaluable septic patients) the model alerts in the warning window for 19 and NEWS2-style for 16; where both alert the model is earlier in 5 cases and NEWS2-style in 8. The app lets you open a missed case.
- Hospital B had been evaluated before this refinement, so it is an external check, not a pristine holdout.

"""
 deploy=m.get("deployment",{})
 status="Clean Python 3.11 and demo-only execution: "+("passed" if deploy.get("python311_demo_only_passed") else "verification pending")+". Docker build/run: "+("passed" if deploy.get("docker_verified") else "untested; Docker unavailable on the Mac")+". No account creation or remote push."
 readme=f"""---
title: SepsisLens
emoji: 🩺
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8501
---
# SepsisLens
**Explainable sepsis early-warning research | DSH Hacks V2 | AI x Healthcare**

> **Research prototype, NOT FOR CLINICAL USE.** Retrospective public ICU recordings. No diagnosis, treatment, triage or live patient monitoring.

{headline}
## Key results
Full Hospital B evaluation: {m["B"]["cohort"]["patients"]:,} patients, {m["B"]["cohort"]["hours"]:,} hours.
A-only selected candidate: **{sel["selected_candidate"]}**; shared alert cooldown: **{sel["selected_cooldown"]} hours**.
The original model is retained if no candidate improves A-selection catches at every target budget. Stronger hourly AUROC does not guarantee better patient catches.

{legacy}
**Historical-protocol caveat:** legacy before figures use retrospective B ranking with no cooldown. After figures use A-only thresholds with cooldown. They are different operating protocols; catch gains are not evidence of better discrimination or a matched B alarm rate.

For a consistent A-only threshold methodology, the same run also computes the original model and baselines without suppression:
{fair}
{rates}
AUROC/AUPRC use original challenge hourly labels before suppression. Utility uses emitted alerts under each operating rule. All values are generated from reports/metrics.json. The report contains {m["bootstrap_resamples"]} patient-bootstrap intervals, all cooldowns, subgroup results and A-versus-B metrics.

## What changed and what did not help
Trials covered six-to-twelve-hour early labels, pre-onset labels with post-onset rows dropped, equal-patient weighting, longer vital/lab windows, NEWS2 changes, LightGBM settings, and logistic NEWS2/risk-trend stacking.
Stackers fit on {sel["A_stack_fit_patients"]:,} A-validation patients; model/policy comparison uses {sel["A_selection_patients"]:,} different A-validation patients. Existing tree fits use A training patients; early stopping/calibration stay in A.
Cooldown is chosen using the original model's A-selection catch average. Candidates can replace it only if they do not regress at any of the target budgets and improve the mean. Full A validation then supplies final thresholds. A model SHA and policy lock are recorded before B is accessed.
{experiment}
Unselected model binaries are excluded from the serving bundle. Full experiment parameters and outcomes remain in reports/experiments_A.json.

## Problem and cited context
CDC estimates about {m["citations"]["CDC"]["adults_yearly"]:,} US adults develop sepsis yearly, with at least {m["citations"]["CDC"]["deaths_or_hospice"]:,} hospital deaths or hospice discharges. [CDC]({m["citations"]["CDC"]["url"]})
Wong et al. reported {m["citations"]["Wong"]["missed_pct"]}% of cases missed by Epic's model at the studied threshold. This is not a head-to-head comparison. [JAMA Internal Medicine]({m["citations"]["Wong"]["url"]})
TREWS provider confirmation within three hours was associated with a {m["citations"]["TREWS"]["relative_reduction_pct"]}% adjusted relative mortality reduction in an observational study; no causal mortality claim is made here. [Nature Medicine]({m["citations"]["TREWS"]["url"]})

## Run the app
Python 3.11 is verified for deployment; the existing Mac environment also runs Python 3.12.
The app reads the demo bundle and metrics only. It never retrains or reads data/raw at startup.

    cd sepsislens
    .venv/bin/streamlit run app/app.py --server.address=0.0.0.0

Clean setup:

    python3.11 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt   # app only; use requirements-dev.txt for tests/pipeline
    streamlit run app/app.py

macOS requires OpenMP: brew install libomp. Linux packages.txt installs libgomp1.

## Reproduce the pipeline
Full rebuild, including A-only experiments and the locked external evaluation:

    bash run_all.sh

Resume with verified existing original features and the completed A policy lock; a matching completed external report is reused without another B pass:

    bash run_all.sh --resume

The downloader resumes the public PhysioNet S3 files, with HTTPS fallback. Patient splits, seeds, candidate results, selected policy and model hashes are saved. Re-running the full pipeline repeats the external check; it does not create an additional untouched test cohort.
To rerun only the A-development stage:

    .venv/bin/python -m src.refine

## Onset and alert definitions
**Inferred onset = first SepsisLabel=1 recording hour + 6.** Challenge labels were shifted six hours early. This is not independently observed clinical onset. First-hour-positive recordings are left-censored; do not infer an exact warning time for them.
Every feature uses current/past information only. ICULOS, HospAdmTime, recording hour, patient/hospital identity and unit indicators are excluded from predictors.
{protocol}

## Dashboard and screenshots
Patient Replay has causal vitals/model/NEWS2 plots, emitted-alert markers, inferred onset, a replay slider, explicit lead time, and cached model explanations. Alarm Budget shows A-target capacity, actual B burden and adjustable shared cooldown. Trust & Validation starts with key results and before/after tables. About cites the data and studies.
![Patient Replay](reports/screenshots/patient_replay.png)
![Alarm Budget](reports/screenshots/alarm_budget.png)
![Trust and Validation](reports/screenshots/trust_validation.png)

## Deploy to Streamlit Community Cloud
{status}

1. Use this sepsislens directory as the repository root. Include app/, src/, demo/, models/, reports/, vendor/, requirements.txt, packages.txt and .streamlit/. Exclude data/, environments and logs. requirements.txt holds only the runtime packages the app imports (training and test tools are in requirements-dev.txt).
2. In your own GitHub account, create/select a repository and push the prepared project yourself. No push or account creation is performed by this task.
3. Open Streamlit Community Cloud, choose Create app, select that repository and branch, and set the main file path to app/app.py.
4. Under Advanced settings, select Python 3.11. No secrets or dataset download are required.
5. Deploy and verify the four tabs. The app loads the shipped demo bundle; requirements.txt is pinned and packages.txt supplies Linux OpenMP.
If nested in a repository, set the entry point and dependency discovery paths accordingly; using this folder as the root is recommended.

## Hugging Face / Docker
Create a Docker Space yourself and upload this directory. Dockerfile serves port 8501 and README metadata sets app_port. No training occurs during image build or startup.

    docker build -t sepsislens .
    docker run --rm -p 8501:8501 sepsislens

Docker status is stated above; configuration is not claimed verified when Docker is absent.

## Checks

    .venv/bin/python -m pytest -q
    .venv/bin/python scripts/smoke_app.py
    .venv/bin/python scripts/verify_bundle.py
    .venv/bin/python scripts/browser_check.py

Browser checks require Playwright Chromium and a running app. Deployment-isolation checks use scripts/check_deployment.py. Results and screenshots live in reports/.

## Limitations
{limitations}
## Data and attribution
{citations}
"""
 (ROOT/"README.md").write_text(readme)
 (ROOT/"MODEL_CARD.md").write_text(f"""# SepsisLens model card
**Research prototype. NOT FOR CLINICAL USE.** Retrospective evaluation and hackathon education only.

## Intended use and exclusions
Research into cross-hospital warning, workload and explainability. No prospective diagnosis, triage, treatment decisions or live monitoring. Data are historical deidentified ICU recordings from PhysioNet/CinC Challenge 2019.

## Development and selection
Selected candidate: {sel["selected_candidate"]}. Shared cooldown: {sel["selected_cooldown"]} hours. All fitting, feature trials, calibration, model selection, cooldown selection and thresholds use Hospital A. Stacker training and assessment use different A-validation patients. No B threshold fitting or score quantiles.
Original models use patient-disjoint A training/calibration/validation splits. Longer windows and early targets are retained only if selected; failed experiments remain documented.
## Inferred onset
First SepsisLabel=1 recording hour + 6. Labels are shifted six hours early. Onset is inferred, not independently observed. First-hour-positive records are left-censored; {m["B"]["onset_left_censored"]:,} B recordings are excluded from onset-based catch denominators while remaining in hourly metrics and official utility.

## External results and operating protocols
{legacy}
Legacy before and A-locked after are different workload protocols. A-consistent comparison:
{fair}
{rates}
## A-only experiment outcomes
{experiment}
## Subgroup audit for the selected model
{subgroup}
## Definitions and uncertainty
{protocol}
## Limitations
{limitations}
## Explanation contract
Cached SHAP explains the selected base tree's raw log-odds. If a stacker is selected, its exact additive linear contributions are separately displayed; base-tree SHAP alone does not explain the final ensemble. Contributions are not causal effects.
## Licensing and attribution
{citations}
""")
 print("Generated refinement README and MODEL_CARD from metrics.json")
if __name__=="__main__":main()
