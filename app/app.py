"""SepsisLens: read-only, retrospective research dashboard. No training at startup."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np,pandas as pd,streamlit as st,plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.explain import nurse_note
from src.alarms import apply_policy,tie_keys
st.set_page_config(page_title="SepsisLens | See the warning sooner",page_icon=":material/monitor_heart:",layout="wide")
TEAL="#0d9488";NAVY="#112d4e";AMBER="#db8b25"
NAMES={"refined":"SepsisLens | selected early warning","vitals":"SepsisLens | vitals","vitals_labs":"SepsisLens | vitals + labs","NEWS2":"NEWS2-style","qSOFA":"qSOFA-style"}
@st.cache_data
def load(signature):
 return (json.loads((ROOT/"reports/metrics.json").read_text()),
 pd.read_parquet(ROOT/"demo/patients.parquet"),pd.read_parquet(ROOT/"demo/shap.parquet"),
 pd.read_parquet(ROOT/"demo/stacker.parquet") if (ROOT/"demo/stacker.parquet").exists() else None)
if not (ROOT/"reports/metrics.json").exists():
 st.error("The evaluation bundle is missing. Run ./run_all.sh to generate real results.");st.stop()
m,patients,shap_values,stack_values=load((ROOT/"reports/metrics.json").stat().st_mtime_ns)
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
@media(max-width:700px){.block-container{padding:1rem}.hero{padding:20px}.hero h1{font-size:2rem}[data-testid="stMetricValue"]{font-size:1.45rem}.stTabs [data-baseweb="tab-list"]{gap:12px;overflow:auto}}
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
 st.caption("Model scores support ranking; they are not a clinical probability of sepsis.")
cooldown=st.session_state.get("cooldown",m["selection"]["selected_cooldown"])
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
   useful=d[(d.refined>=m["selection"]["policies"]["refined"][str(cooldown)]["5.0"]["threshold"])&(d.hour>=onset_preview-12)&(d.hour<onset_preview)]
   if not useful.empty:start_hour=min(maxhour,int(useful.hour.iloc[0])+1)
  st.session_state["replay_hour"]=start_hour;st.session_state["last_patient"]=patient
 hour=st.slider("Replay hour",minhour,maxhour,key="replay_hour") if maxhour>minhour else minhour
 shown=d[d.hour<=hour];row=shown.iloc[-1];threshold=m["selection"]["policies"]["refined"][str(cooldown)]["5.0"]["threshold"]
 positive=d[d.SepsisLabel==1];censored=not positive.empty and positive.hour.iloc[0]==1
 onset=None if positive.empty or censored else int(positive.hour.iloc[0]+6)
 policy=m["selection"]["policies"]["refined"][str(cooldown)]["5.0"]
 context={"patient":np.zeros(len(d),dtype=int),"hour":d.hour.to_numpy()}
 alarm_mask=apply_policy(d.refined.to_numpy(),context,policy,tie_keys(d))
 news_policy=m["selection"]["policies"]["NEWS2"][str(cooldown)]["5.0"]
 news_mask=apply_policy(d.NEWS2.to_numpy(),context,news_policy,tie_keys(d))
 alerts=d[alarm_mask];firstalert=int(alerts.hour.iloc[0]) if not alerts.empty else None
 observed_alerts=alerts[alerts.hour<=hour]
 latest_alert=int(observed_alerts.hour.iloc[-1]) if not observed_alerts.empty else None
 with right:
  st.caption("CURRENT MODEL SCORE")
  st.metric("Early-warning model score",fmt(row.refined,3))
  st.caption(f'A-selected threshold: {threshold:.4f}')
 cols=st.columns(6)
 for col,v,unit in zip(cols,["HR","Resp","Temp","SBP","MAP","O2Sat"],["bpm","/min","C","mmHg","mmHg","%"]):
  col.metric(v,fmt(row[v],1));col.caption(unit)
 st.caption("Values shown are last-observation-carried-forward; a displayed value may not have been measured this hour.")
 if patient==default and cooldown==m["demo"]["cooldown"] and m["demo"]["comparison_available"]:
  st.success(f'This illustrative case: model warns {m["demo"]["default_model_lead"]:.0f} h before inferred onset and {m["demo"]["lead_over_NEWS2"]:.0f} h before NEWS2. Both are observed emitted alerts under the same cooldown.')
 st.caption("Onset = first SepsisLabel=1 hour + 6; inferred from shifted labels, not independently observed.")
 chart=make_subplots(specs=[[{"secondary_y":True}]])
 chart.add_trace(go.Scatter(x=shown.hour,y=shown.vitals_labs,name="SepsisLens score",line=dict(color=TEAL,width=3),fill="tozeroy",fillcolor="rgba(13,148,136,.07)"),secondary_y=False)
 chart.add_trace(go.Scatter(x=shown.hour,y=shown.NEWS2,name="NEWS2-style",line=dict(color=AMBER,width=2)),secondary_y=True)
 chart.add_hline(y=threshold,line_dash="dot",line_color=TEAL,annotation_text="A-locked model threshold")
 if firstalert is not None and firstalert<=hour:chart.add_vline(x=firstalert,line_dash="dash",line_color=TEAL,annotation_text="First emitted alert")
 if latest_alert is not None and latest_alert!=firstalert:chart.add_vline(x=latest_alert,line_dash="dash",line_color=TEAL,annotation_text="Latest emitted alert")
 news_observed=d[news_mask & (d.hour.to_numpy()<=hour)]
 if not news_observed.empty:chart.add_vline(x=int(news_observed.hour.iloc[-1]),line_dash="dot",line_color=AMBER,annotation_text="Latest NEWS2 alert")
 if onset is not None:chart.add_vline(x=onset,line_dash="dash",line_color="#c05964",annotation_text="Inferred clinical onset",annotation_position="top left")
 chart.add_vline(x=hour,line_color="#8aa2b8",line_dash="dot")
 chart.update_xaxes(title="ICU recording hour (display only; excluded from model)",range=[minhour,max(maxhour,onset or 0)+1])
 chart.update_yaxes(title="Early-warning score",secondary_y=False,range=[0,max(.15,float(d.refined.max())*1.15,threshold*1.15)])
 chart.update_yaxes(title="NEWS2-style points",secondary_y=True,rangemode="tozero")
 st.plotly_chart(style(chart,370),width="stretch")
 if censored:st.info("The first recorded label is already positive: onset is left-censored, so no exact onset or warning-time claim is made.")
 elif onset is not None and onset>maxhour:st.caption("Inferred onset falls after the available recording. It is inferred from the shifted label, not observed directly.")
 elif onset is None:st.caption("No positive sepsis label in this recording.")
 st.markdown("#### Why this score?")
 explanation_hour=st.radio("Explain",["Current hour","Latest emitted alert"],horizontal=True)
 erow=d[d.hour==latest_alert].iloc[0] if explanation_hour=="Latest emitted alert" and latest_alert is not None else row
 if explanation_hour=="Latest emitted alert" and latest_alert is None:st.caption("No threshold alert observed by the replay cursor; explaining the current hour.")
 sv=shap_values[(shap_values.patient_id==patient)&(shap_values.hour==erow.hour)].iloc[0]
 features=[x for x in sv.index if x not in ["patient_id","hour"]]
 factors=[]
 for feature in sorted(features,key=lambda x:abs(sv[x]),reverse=True)[:35]:
  v=erow[feature]
  factors.append({"feature":feature,"value":None if pd.isna(v) else float(v),"shap":float(sv[feature]),"direction":"raises risk" if sv[feature]>0 else "lowers risk"})
 note=nurse_note(factors,float(erow.refined),threshold)
 st.markdown(f'<div class="reason"><b>Model explanation | hour {int(erow.hour)}</b><br>{note}</div>',unsafe_allow_html=True)
 st.caption("SHAP describes the selected base tree in raw log-odds; it is not a causal explanation or a calibrated clinical probability.")
 if stack_values is not None:
  stack_row=stack_values[(stack_values.patient_id==patient)&(stack_values.hour==erow.hour)].drop(columns=["patient_id","hour"]).iloc[0]
  st.markdown("**Final ensemble explanation**")
  st.caption("Exact additive contributions to the final linear stacker log-odds, relative to its intercept. The SHAP card above explains only the base model.")
  st.dataframe(pd.DataFrame({"Factor":stack_row.index,"Final log-odds contribution":stack_row.values}).sort_values("Final log-odds contribution",key=abs,ascending=False),hide_index=True,width="stretch")
 with st.expander("Inspect all top 35 factors"):
  st.dataframe(pd.DataFrame(factors),hide_index=True,width="stretch")
 vit=make_subplots(rows=2,cols=2,subplot_titles=["Heart rate","Respiratory rate","Blood pressure","Temperature"])
 for v,r,c,color in [("HR",1,1,TEAL),("Resp",1,2,TEAL),("MAP",2,1,NAVY),("SBP",2,1,"#6e91b1"),("Temp",2,2,AMBER)]:
  vit.add_trace(go.Scatter(x=shown.hour,y=shown[v],name=v,line=dict(color=color,width=2)),row=r,col=c)
 vit.update_xaxes(range=[minhour,maxhour+1],title="Hour")
 for r,c,unit in [(1,1,"bpm"),(1,2,"breaths/min"),(2,1,"mmHg"),(2,2,"C")]:vit.update_yaxes(title=unit,row=r,col=c)
 st.plotly_chart(style(vit,430),width="stretch")
 st.caption(m["demo"]["selection"])
with tabs[1]:
 st.subheader("How many alarms can a team absorb?")
 st.write("Choose a target workload on Hospital A, then inspect catches and the actual alarm burden after transferring that policy to Hospital B.")
 budget=st.slider("Target A alerts per 100 patient-hours",.5,10.,5.,.5)
 cooldown=st.select_slider("Cooldown (hours)",options=m["selection"]["cooldowns"],value=m["selection"]["selected_cooldown"],key="cooldown")
 st.caption(m["protocol"]["cooldown"])
 method=st.selectbox("Model version",["refined","vitals_labs","vitals"],format_func=lambda x:NAMES[x])
 st.info(m["protocol"]["budget"])
 for name in [method,"NEWS2"]:
  op=m["B"]["methods"][name]["cooldowns"][str(cooldown)][str(float(budget))]
  st.markdown("#### "+NAMES[name])
  cols=st.columns(5)
  for col,label,key,suffix in zip(cols,["Septic patients caught","Outside-window alarms","Catches per 100 alarms","Median warning","Actual B alarms /100h"],
   ["caught_pct","false_alarms","catches_per_100_alarms","median_warning","alert_rate"],["%","",""," h"," /100h"]):
   col.metric(label,fmt(op[key],0 if key=="false_alarms" else 1,suffix))
   col.caption("95% CI: "+interval(op["ci"][key],1))
  st.caption(f'{op["caught"]} distinct patients caught; {op["alarms"]:,} hourly alarms. Eligible septic patients: {op["eligible_septic"]:,}.')
 fig=go.Figure()
 for name,color in [(method,TEAL),("NEWS2",AMBER)]:
  b=m["B"]["methods"][name]["cooldowns"][str(cooldown)]
  fig.add_trace(go.Scatter(x=[v["alert_rate"] for v in b.values()],y=[v["caught_pct"] for v in b.values()],mode="lines+markers",name=NAMES[name],line=dict(color=color,width=3)))

 fig.update_xaxes(title="Actual B emitted alerts / 100 patient-hours");fig.update_yaxes(title="Septic patients caught (%)",range=[0,100])
 st.plotly_chart(style(fig),width="stretch")
 st.caption(m["protocol"]["catch"]+" "+m["protocol"]["false_alarm"])
 with st.expander("How the alarm counts and confidence intervals work"):
  for k in ["catch","false_alarm","catches_per_100_alarms","warning","budget","ci"]:st.write(f"**{k.replace('_',' ').title()}** | {m['protocol'][k]}")
with tabs[2]:
 st.subheader("Train here. Test somewhere else.")
 st.markdown("#### Key results")
 key=m["B"]["methods"]["refined"];news=m["B"]["methods"]["NEWS2"];a_key=m["A_validation"]["methods"]["refined"]
 cols=st.columns(4)
 cols[0].metric("B hourly AUROC",fmt(key["auroc"],3))
 cols[1].metric("AUROC change B - A",fmt(key["auroc"]-a_key["auroc"],3))
 cols[2].metric("Model caught at A target 5",fmt(key["budgets"]["5.0"]["caught_pct"],1,"%"))
 cols[3].metric("NEWS2 caught at A target 5",fmt(news["budgets"]["5.0"]["caught_pct"],1,"%"))
 st.caption(f'Selected shared cooldown: {m["selection"]["selected_cooldown"]} h. Actual B alarms/100h: model {key["budgets"]["5.0"]["alert_rate"]:.2f}; NEWS2 {news["budgets"]["5.0"]["alert_rate"]:.2f}. Thresholds are frozen from A; these are not matched B alarm rates.')
 st.caption(f'A-only selected candidate: {m["selection"]["selected_candidate"]}. Selection uses {m["selection"]["A_selection_patients"]:,} patients, disjoint from {m["selection"]["A_stack_fit_patients"]:,} stack-fit patients.')
 st.markdown("#### Before vs after")
 before_rows=[]
 for name in ["vitals_labs","NEWS2","qSOFA"]:
  v=m["before"]["B"]["methods"][name]
  before_rows.append({"Version":"Before (legacy B ranking)","Method":NAMES[name],"AUROC":v["auroc"],"AUPRC":v["auprc"],"Utility":v["operating"]["utility"],**{f"Caught at {b}":v["budgets"][str(float(b))]["caught_pct"] for b in [2,5,10]}})
 for name in ["refined","NEWS2","qSOFA"]:
  v=m["B"]["methods"][name]
  before_rows.append({"Version":"After (A-locked thresholds)","Method":NAMES[name],"AUROC":v["auroc"],"AUPRC":v["auprc"],"Utility":v["operating"]["utility"],**{f"Caught at {b}":v["budgets"][str(float(b))]["caught_pct"] for b in [2,5,10]}})
 st.dataframe(pd.DataFrame(before_rows),hide_index=True,width="stretch")
 st.caption("Legacy before numbers used retrospective B ranking and no cooldown. After numbers use A-only thresholds and shared cooldown. They are different operating protocols; AUROC/AUPRC remain comparable. Download metrics for the original model under every new policy and cooldown.")
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
 st.caption(m["protocol"]["utility"])
 c1,c2=st.columns(2)
 c1.image(str(ROOT/"reports/figures/roc.png"),caption="Full Hospital B ROC",width="stretch")
 c2.image(str(ROOT/"reports/figures/calibration.png"),caption="Reliability against challenge labels; early-warning scores may use a different training target",width="stretch")
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
 st.write("Features use current and past vitals/labs, six-hour and longer trends, changes, shock index, and measurement flags. A-only experiments compare early-window objectives, patient weighting, model settings and a linear NEWS2/risk-trend ensemble. A validation selects the final policy. Hospital B is evaluated after the policy lock.")
 st.write("Admission clocks (ICULOS and HospAdmTime), patient identity, hospital identity, labels, and unit indicators are excluded from model inputs. No backward fill or future observations are used.")
 st.markdown("#### Baseline approximations")
 st.write("qSOFA-style uses respiratory rate >=22 and systolic pressure <=100; mental status is unavailable. NEWS2-style uses respiratory rate, oxygen saturation (scale 1), systolic pressure, heart rate and temperature; consciousness, supplemental oxygen and scale-2 eligibility are unavailable. Missing components contribute zero points, potentially understating severity. These partial scores are not validated clinical NEWS2 or qSOFA.")
 st.markdown("#### Open data, reproducible research")
 st.markdown(f'[PhysioNet/CinC Challenge 2019 v1.0.0]({sources["dataset"]["url"]}) | CC BY 4.0. Reyna MA et al. Early Prediction of Sepsis From Clinical Data: The PhysioNet/Computing in Cardiology Challenge 2019. Critical Care Medicine, 2020;48(2):210-217. DOI: 10.1097/CCM.0000000000004145.')
 st.write(f'The {m["demo"]["patients"]}-patient replay bundle is for demonstration. Validation and alarm-budget metrics use the full cohort and come from reports/metrics.json.')
 st.error("NOT FOR CLINICAL USE. Research prototype on retrospective deidentified data. Do not use for diagnosis, triage, treatment decisions, or live patient monitoring.")
st.caption("SepsisLens | DSH Hacks V2 | Open evaluation. Explainable alerts. Honest limitations.")
