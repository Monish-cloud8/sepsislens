"""SepsisLens: read-only, retrospective research dashboard. No training at startup."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np,pandas as pd,streamlit as st,plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.explain import nurse_note
st.set_page_config(page_title="SepsisLens | See the warning sooner",page_icon=":material/monitor_heart:",layout="wide")
TEAL="#0d9488";NAVY="#112d4e";AMBER="#db8b25"
NAMES={"vitals":"SepsisLens | vitals","vitals_labs":"SepsisLens | vitals + labs","NEWS2":"NEWS2-style","qSOFA":"qSOFA-style"}
@st.cache_data
def load(signature):
 return (json.loads((ROOT/"reports/metrics.json").read_text()),
 pd.read_parquet(ROOT/"demo/patients.parquet"),pd.read_parquet(ROOT/"demo/shap.parquet"))
if not (ROOT/"reports/metrics.json").exists():
 st.error("The evaluation bundle is missing. Run ./run_all.sh to generate real results.");st.stop()
m,patients,shap_values=load((ROOT/"reports/metrics.json").stat().st_mtime_ns)
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
html,body,[class*="css"] {font-family:'DM Sans',sans-serif}
.block-container{padding-top:1.8rem;max-width:1450px}
h1,h2,h3{color:#112d4e;letter-spacing:-.035em}
[data-testid="stMetric"]{background:white;border:1px solid #dce8ed;border-radius:12px;padding:16px}
[data-testid="stMetricLabel"]{color:#587087;font-size:.82rem}
[data-testid="stMetricValue"]{color:#112d4e;font-size:1.8rem}
.stTabs [data-baseweb="tab-list"]{gap:22px;border-bottom:1px solid #dce8ed}
.stTabs [data-baseweb="tab"]{padding:16px 4px;font-weight:600}
.eyebrow{font-size:.76rem;font-weight:700;letter-spacing:.16em;color:#0d9488}
.hero{background:#112d4e;border-radius:16px;padding:30px 34px;margin:12px 0 24px;color:white}
.hero h1{color:white;font-size:2.5rem;margin:0}
.hero p{color:#c3d6e6;margin:6px 0 0;max-width:850px}
.reason{background:#ecf9f6;border-left:4px solid #0d9488;border-radius:8px;padding:20px 24px;color:#163e47}
.small{font-size:.84rem;color:#61788a}
</style>""",unsafe_allow_html=True)
st.warning("RESEARCH PROTOTYPE | Retrospective public ICU data. NOT FOR CLINICAL USE. No diagnosis, treatment, or live patient monitoring.")
st.markdown('<div class="eyebrow">DSH HACKS V2 / AI x HEALTHCARE</div><div class="hero"><h1>SepsisLens</h1><p>See the warning sooner. Understand every alert.<br>An open cross-hospital study of early warning and the cost of alarm fatigue.</p></div>',unsafe_allow_html=True)
with st.sidebar:
 st.markdown("### SepsisLens")
 st.caption("A research lens on early warning")
 st.markdown("---")
 st.markdown("**Training: Hospital A**")
 st.markdown("**External test: Hospital B**")
 st.metric("External test patients",f'{m["B"]["cohort"]["patients"]:,}')
 st.metric("External patient-hours",f'{m["B"]["cohort"]["hours"]:,}')
 st.caption(f'Dashboard replay: {m["demo"]["patients"]} B patients. All validation metrics use the full held-out cohort.')
 st.markdown("---")
 st.caption("Causal hourly features | Patient-separated evaluation | A-only calibration")
 st.caption("Scores estimate the early-warning label; they are not a clinical probability of sepsis.")
tabs=st.tabs(["Patient Replay","Alarm Budget","Trust & Validation","About"])
def fmt(x,d=1,suffix=""):
 return "N/A" if x is None else f"{x:,.{d}f}{suffix}"
def interval(ci,d=3):
 return "unavailable" if not ci or ci[0] is None else f"{ci[0]:.{d}f} to {ci[1]:.{d}f}"
def style(fig,height=340):
 fig.update_layout(template="plotly_white",height=height,margin=dict(l=15,r=15,t=35,b=30),
 font=dict(family="Arial",color=NAVY),legend=dict(orientation="h",y=1.18),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="white")
 fig.update_xaxes(showgrid=False);fig.update_yaxes(gridcolor="#e9f0f3")
 return fig
with tabs[0]:
 left,right=st.columns([3,1])
 with left:
  st.subheader("The hours before the label")
  st.caption("A retrospective replay. Move the cursor to reveal only measurements and predictions available by that hour.")
 ids=patients.patient_id.unique().tolist();default=m["demo"]["default_patient"]
 ids=[default]+sorted(x for x in ids if x!=default)
 patient=st.selectbox("Hospital B patient",ids)
 d=patients[patients.patient_id==patient].sort_values("hour").reset_index(drop=True)
 maxhour=int(d.hour.max());minhour=int(d.hour.min())
 if st.session_state.get("last_patient")!=patient:
  start_hour=min(maxhour,minhour+18)
  pos=d[d.SepsisLabel==1]
  if not pos.empty and pos.hour.iloc[0]>1:
   onset_preview=int(pos.hour.iloc[0]+6)
   useful=d[(d.vitals_labs>=m["thresholds"]["vitals_labs"])&(d.hour>=onset_preview-12)&(d.hour<onset_preview)]
   if not useful.empty:start_hour=min(maxhour,int(useful.hour.iloc[0])+1)
  st.session_state["replay_hour"]=start_hour;st.session_state["last_patient"]=patient
 hour=st.slider("Replay hour",minhour,maxhour,key="replay_hour") if maxhour>minhour else minhour
 shown=d[d.hour<=hour];row=shown.iloc[-1];threshold=m["thresholds"]["vitals_labs"]
 positive=d[d.SepsisLabel==1];censored=not positive.empty and positive.hour.iloc[0]==1
 onset=None if positive.empty or censored else int(positive.hour.iloc[0]+6)
 alerts=d[d.vitals_labs>=threshold];firstalert=int(alerts.hour.iloc[0]) if not alerts.empty else None
 with right:
  st.caption("CURRENT MODEL SCORE")
  st.metric("Calibrated early-warning score",fmt(row.vitals_labs*100,1,"%"))
  st.caption(f'A-selected threshold: {threshold:.4f}')
 cols=st.columns(6)
 for col,v,unit in zip(cols,["HR","Resp","Temp","SBP","MAP","O2Sat"],["bpm","/min","C","mmHg","mmHg","%"]):
  col.metric(v,fmt(row[v],1));col.caption(unit)
 st.caption("Values shown are last-observation-carried-forward; a displayed value may not have been measured this hour.")
 chart=make_subplots(specs=[[{"secondary_y":True}]])
 chart.add_trace(go.Scatter(x=shown.hour,y=shown.vitals_labs,name="SepsisLens score",line=dict(color=TEAL,width=3),fill="tozeroy",fillcolor="rgba(13,148,136,.07)"),secondary_y=False)
 chart.add_trace(go.Scatter(x=shown.hour,y=shown.NEWS2,name="NEWS2-style",line=dict(color=AMBER,width=2)),secondary_y=True)
 chart.add_hline(y=threshold,line_dash="dot",line_color=TEAL,annotation_text="A-locked model threshold")
 if firstalert is not None and firstalert<=hour:chart.add_vline(x=firstalert,line_dash="dash",line_color=TEAL,annotation_text="First threshold alert")
 if onset is not None:chart.add_vline(x=onset,line_dash="dash",line_color="#c05964",annotation_text="Inferred clinical onset",annotation_position="top left")
 chart.add_vline(x=hour,line_color="#8aa2b8",line_dash="dot")
 chart.update_xaxes(title="ICU recording hour (display only; excluded from model)",range=[minhour,max(maxhour,onset or 0)+1])
 chart.update_yaxes(title="Early-warning score",secondary_y=False,range=[0,max(.15,float(d.vitals_labs.max())*1.15,threshold*1.15)])
 chart.update_yaxes(title="NEWS2-style points",secondary_y=True,rangemode="tozero")
 st.plotly_chart(style(chart,370),width="stretch")
 if censored:st.info("The first recorded label is already positive: onset is left-censored, so no exact onset or warning-time claim is made.")
 elif onset is not None and onset>maxhour:st.caption("Inferred onset falls after the available recording. It is inferred from the shifted label, not observed directly.")
 elif onset is None:st.caption("No positive sepsis label in this recording.")
 st.markdown("#### Why this score?")
 explanation_hour=st.radio("Explain",["Current hour","First threshold alert"],horizontal=True)
 erow=d[d.hour==firstalert].iloc[0] if explanation_hour=="First threshold alert" and firstalert is not None and firstalert<=hour else row
 if explanation_hour=="First threshold alert" and (firstalert is None or firstalert>hour):st.caption("No threshold alert observed by the replay cursor; explaining the current hour.")
 sv=shap_values[(shap_values.patient_id==patient)&(shap_values.hour==erow.hour)].iloc[0]
 features=[x for x in sv.index if x not in ["patient_id","hour"]]
 factors=[]
 for feature in sorted(features,key=lambda x:abs(sv[x]),reverse=True)[:35]:
  v=erow[feature]
  factors.append({"feature":feature,"value":None if pd.isna(v) else float(v),"shap":float(sv[feature]),"direction":"raises risk" if sv[feature]>0 else "lowers risk"})
 note=nurse_note(factors,float(erow.vitals_labs),threshold)
 st.markdown(f'<div class="reason"><b>Model explanation | hour {int(erow.hour)}</b><br>{note}</div>',unsafe_allow_html=True)
 st.caption("SHAP contributions are in the base tree's log-odds before A-only probability calibration; they are not causal effects.")
 with st.expander("Inspect all top 35 factors"):
  st.dataframe(pd.DataFrame(factors),hide_index=True,width="stretch")
 vit=make_subplots(rows=2,cols=2,subplot_titles=["Heart rate","Respiratory rate","Blood pressure","Temperature"])
 for v,r,c,color in [("HR",1,1,TEAL),("Resp",1,2,TEAL),("MAP",2,1,NAVY),("SBP",2,1,"#6e91b1"),("Temp",2,2,AMBER)]:
  vit.add_trace(go.Scatter(x=shown.hour,y=shown[v],name=v,line=dict(color=color,width=2)),row=r,col=c)
 vit.update_xaxes(range=[minhour,maxhour+1],title="Hour")
 st.plotly_chart(style(vit,430),width="stretch")
 st.caption(m["demo"]["selection"])
with tabs[1]:
 st.subheader("How many alarms can a team absorb?")
 st.write("Set an hourly alarm budget and compare catches with the NEWS2-style score at the same rate.")
 budget=st.slider("Hourly alerts per 100 patient-hours",.5,10.,5.,.5)
 method=st.selectbox("Model version",["vitals_labs","vitals"],format_func=lambda x:NAMES[x])
 st.info("Retrospective capacity comparison: rank Hospital B scores without labels, then take the budgeted number of patient-hours. Ties use a deterministic patient-hour hash. These are not B-tuned clinical thresholds.")
 for name in [method,"NEWS2"]:
  op=m["B"]["methods"][name]["budgets"][str(float(budget))]
  st.markdown("#### "+NAMES[name])
  cols=st.columns(5)
  for col,label,key,suffix in zip(cols,["Septic patients caught","False alarms (hourly)","Catches per 100 alarms","Median warning","Actual hourly alarm rate"],
   ["caught_pct","false_alarms","catches_per_100_alarms","median_warning","alert_rate"],["%","",""," h"," /100h"]):
   col.metric(label,fmt(op[key],0 if key=="false_alarms" else 1,suffix))
   col.caption("95% CI: "+interval(op["ci"][key],1))
  st.caption(f'{op["caught"]} distinct patients caught; {op["alarms"]:,} hourly alarms. Eligible septic patients: {op["eligible_septic"]:,}.')
 fig=go.Figure()
 for name,color in [(method,TEAL),("NEWS2",AMBER)]:
  b=m["B"]["methods"][name]["budgets"]
  fig.add_trace(go.Scatter(x=[float(k) for k in b],y=[v["caught_pct"] for v in b.values()],mode="lines+markers",name=NAMES[name],line=dict(color=color,width=3)))
 fig.add_vline(x=budget,line_dash="dot",line_color=NAVY)
 fig.update_xaxes(title="Hourly alerts / 100 patient-hours");fig.update_yaxes(title="Septic patients caught (%)",range=[0,100])
 st.plotly_chart(style(fig),width="stretch")
 st.caption("A catch requires an alert within the 12 hours before inferred onset. Each threshold-positive hour counts as an alarm, with no cooldown. Repeated alarms and alerts outside that window consume budget. False alarms here means outside the evaluable warning window, including cases with unassessable onset; these are not clinically adjudicated false positives. Warning times are conditional on a catch.")
 with st.expander("How the alarm counts and confidence intervals work"):
  for k in ["catch","false_alarm","catches_per_100_alarms","warning","budget","ci"]:st.write(f"**{k.replace('_',' ').title()}** | {m['protocol'][k]}")
with tabs[2]:
 st.subheader("Train here. Test somewhere else.")
 st.write("Hospital B is held out from fitting, hyperparameter selection, probability calibration, and operational threshold selection.")
 rows=[]
 for name in NAMES:
  a=m["A_validation"]["methods"][name];b=m["B"]["methods"][name]
  rows.append({"Method":NAMES[name],"A validation AUROC":a["auroc"],"B AUROC":b["auroc"],"B AUROC 95% CI":interval(b["ci"]["auroc"]),
   "A validation AUPRC":a["auprc"],"B AUPRC":b["auprc"],"B AUPRC 95% CI":interval(b["ci"]["auprc"]),
   "AUROC change (B - A)":b["auroc"]-a["auroc"]})
 st.dataframe(pd.DataFrame(rows),hide_index=True,width="stretch")
 st.markdown("#### A-locked operational thresholds")
 st.caption(m["protocol"]["thresholds"])
 rows=[]
 for name in NAMES:
  b=m["B"]["methods"][name];op=b["operating"]
  rows.append({"Method":NAMES[name],"Threshold":b["threshold"],"B alarms /100h":op["alert_rate"],
   "B utility":op["utility"],"Utility 95% CI":interval(op["ci"]["utility"]),"Caught %":op["caught_pct"],
   "Caught % 95% CI":interval(op["ci"]["caught_pct"],1),"Median warning (h)":op["median_warning"],
   "Warning 95% CI":interval(op["ci"]["median_warning"],1)})
 st.dataframe(pd.DataFrame(rows),hide_index=True,width="stretch")
 st.caption("Official PhysioNet 2019 normalized time-dependent utility, using the unmodified reference implementation. Baseline thresholds may underfill the A budget because complete score ties are retained or excluded together.")
 c1,c2=st.columns(2)
 c1.image(str(ROOT/"reports/figures/roc.png"),caption="Full Hospital B ROC",width="stretch")
 c2.image(str(ROOT/"reports/figures/calibration.png"),caption="Calibration after A-only Platt scaling",width="stretch")
 st.markdown("#### Subgroup audit | Hospital B")
 audit=st.selectbox("Subgroup model",list(NAMES),format_func=lambda x:NAMES[x])
 sg=pd.DataFrame(m["B"]["methods"][audit]["subgroups"]).T.reset_index(names="Subgroup")
 if "auroc_ci" in sg.columns:sg["auroc_ci"]=sg["auroc_ci"].map(interval)
 st.dataframe(sg,hide_index=True,width="stretch")
 st.caption("Recorded binary sex is the dataset's Gender field; it does not describe gender identity. Small groups and positive-label counts limit interpretation.")
 st.markdown("#### Scope and limitations")
 st.write("Retrospective ICU data cannot establish clinical benefit. A/B recordings represent different hospital systems, not a prospective deployment. Missingness and test-ordering can reflect local workflow. Forward-filled values may be stale. Partial NEWS2 and qSOFA omit unavailable clinical assessments. Model calibration can drift across sites.")
 st.write(f'Onset is inferred from shifted labels. First-hour-positive cases excluded from onset-based metrics: {m["B"]["onset_left_censored"]:,} on B; hourly discrimination and official utility retain them.')
 st.write(m["protocol"]["ci"])
 st.write("A validation participates in tuning and threshold selection, so its reported performance may be optimistic. External B results are the principal check. No prospective safety, fairness, or mortality claims are made.")
 st.download_button("Download complete metrics",json.dumps(m,indent=2),file_name="sepsislens_metrics.json",mime="application/json")
with tabs[3]:
 st.subheader("Early warning needs evidence, not just a score.")
 sources=m["citations"]
 cols=st.columns(3)
 cols[0].metric("US adults affected each year",f'{sources["CDC"]["adults_yearly"]/1e6:.1f}M')
 cols[1].metric("Deaths or hospice discharges",f'{sources["CDC"]["deaths_or_hospice"]/1000:.0f}K+')
 cols[2].metric("Cases missed in Epic study",f'{sources["Wong"]["missed_pct"]}%')
 st.markdown(f'[CDC: US annual sepsis burden]({sources["CDC"]["url"]})')
 st.markdown(f'{sources["Wong"]["context"]} [Wong et al., JAMA Internal Medicine (2021)]({sources["Wong"]["url"]})')
 st.markdown(f'TREWS: **{sources["TREWS"]["relative_reduction_pct"]}% adjusted relative mortality reduction**. {sources["TREWS"]["context"]} [Adams et al., Nature Medicine (2022)]({sources["TREWS"]["url"]})')
 st.markdown("#### How SepsisLens works")
 st.write("Hourly vitals and labs become past-and-present features: last observed values, six-hour trends, hourly changes, shock index, and lab measurement flags. Two class-weighted LightGBM models learn on Hospital A. A separate slice of A training patients calibrates scores; A validation selects model settings and operational thresholds. Hospital B provides the external test.")
 st.write("Admission clocks (ICULOS and HospAdmTime), patient identity, hospital identity, labels, and unit indicators are excluded from model inputs. No backward fill or future observations are used.")
 st.markdown("#### Baseline approximations")
 st.write("qSOFA-style uses respiratory rate >=22 and systolic pressure <=100; mental status is unavailable. NEWS2-style uses respiratory rate, oxygen saturation (scale 1), systolic pressure, heart rate and temperature; consciousness, supplemental oxygen and scale-2 eligibility are unavailable. Missing components contribute zero points, potentially understating severity. These partial scores are not validated clinical NEWS2 or qSOFA.")
 st.markdown("#### Open data, reproducible research")
 st.markdown(f'[PhysioNet/CinC Challenge 2019 v1.0.0]({sources["dataset"]["url"]}) | CC BY 4.0. Reyna MA et al. Early Prediction of Sepsis From Clinical Data: The PhysioNet/Computing in Cardiology Challenge 2019. Critical Care Medicine, 2020;48(2):210-217. DOI: 10.1097/CCM.0000000000004145.')
 st.write("The 300-patient replay bundle is for demonstration. All displayed validation and alarm-budget results come from the full evaluation run saved in reports/metrics.json.")
 st.error("NOT FOR CLINICAL USE. Research prototype on retrospective deidentified data. Do not use for diagnosis, triage, treatment decisions, or live patient monitoring.")
st.caption("SepsisLens | DSH Hacks V2 | Open evaluation. Explainable alerts. Honest limitations.")
