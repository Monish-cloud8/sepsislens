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
TEAL="#0d9488";NAVY="#112d4e";AMBER="#db8b25";RED="#c0435a";MUTED="#61788a"
NAMES={"refined":"SepsisLens | selected early warning","vitals":"SepsisLens | vitals","vitals_labs":"SepsisLens | vitals + labs","NEWS2":"NEWS2-style","qSOFA":"qSOFA-style"}
SHORT={"refined":"SepsisLens","vitals":"SepsisLens (vitals)","vitals_labs":"SepsisLens (vitals + labs)","NEWS2":"NEWS2-style","qSOFA":"qSOFA-style"}
LABELS={"HR":"Heart rate","Resp":"Respiratory rate","MAP":"Mean arterial pressure","SBP":"Systolic pressure","DBP":"Diastolic pressure","O2Sat":"Oxygen saturation","Temp":"Temperature",
 "FiO2":"Inspired oxygen (FiO2)","BUN":"BUN (kidney)","Lactate":"Lactate","WBC":"White cell count","Creatinine":"Creatinine","Platelets":"Platelets","Age":"Age","Gender":"Recorded sex",
 "shock_index":"Shock index","Alkalinephos":"Alkaline phosphatase","Bilirubin_total":"Total bilirubin","Bilirubin_direct":"Direct bilirubin","TroponinI":"Troponin I","Hgb":"Hemoglobin","Hct":"Hematocrit",
 "PaCO2":"PaCO2","SaO2":"SaO2","EtCO2":"End-tidal CO2","HCO3":"Bicarbonate","BaseExcess":"Base excess","PTT":"PTT"}
SUFFIX=[("_mean6"," (6 h mean)"),("_min6"," (6 h min)"),("_max6"," (6 h max)"),("_slope6"," (6 h trend)"),("_delta"," (hourly change)"),("_measured"," measured?")]
def pretty(name):
 for s,t in SUFFIX:
  if name.endswith(s):base=name[:-len(s)];return LABELS.get(base,base)+t
 return LABELS.get(name,name)
@st.cache_data
def load(signature):
 return (json.loads((ROOT/"reports/metrics.json").read_text()),
 pd.read_parquet(ROOT/"demo/patients.parquet"),pd.read_parquet(ROOT/"demo/shap.parquet"),
 pd.read_parquet(ROOT/"demo/stacker.parquet") if (ROOT/"demo/stacker.parquet").exists() else None)
if not (ROOT/"reports/metrics.json").exists():
 st.error("The evaluation bundle is missing. Run ./run_all.sh to generate real results.");st.stop()
m,patients,shap_values,stack_values=load((ROOT/"reports/metrics.json").stat().st_mtime_ns)
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Instrument+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap');
:root{--ink:#0c2238;--ink2:#3d556b;--line:#dbe4ea;--paper:#fff6f5;--gridm:#f6d3d4;--gridM:#ecb3b7;--sig:#d12f4c;--teal:#0d9488;--amber:#db8b25}
html,body,[class*="css"]{font-family:'Instrument Sans',sans-serif}
.stApp{background:#f5f8fa}
.block-container{padding-top:3.2rem;max-width:1360px}
h1,h2,h3,h4{font-family:'Bricolage Grotesque',sans-serif;color:var(--ink);letter-spacing:-.02em}
h4{font-weight:700}
[data-testid="stMetric"]{background:white;border:1px solid var(--line);border-left:4px solid var(--ink);border-radius:10px;padding:12px 16px;transition:box-shadow .2s,transform .2s}
[data-testid="stMetric"]:hover{box-shadow:0 6px 18px rgba(12,34,56,.08);transform:translateY(-1px)}
[data-testid="stMetricLabel"]{color:var(--ink2);font-size:.8rem;text-transform:uppercase;letter-spacing:.06em;font-weight:600}
[data-testid="stMetricValue"]{font-family:'IBM Plex Mono',monospace;color:var(--ink);font-size:1.55rem;font-weight:600}
[data-testid="stSidebar"] [data-testid="stMetricLabel"] *{white-space:normal!important;overflow:visible!important;text-overflow:clip!important}
.stTabs [data-baseweb="tab-list"]{gap:6px;background:#e9eff3;border-radius:12px;padding:5px;border:0}
.stTabs [data-baseweb="tab"]{padding:10px 18px;font-weight:600;font-size:.98rem;border-radius:9px;color:var(--ink2);height:auto}
.stTabs [aria-selected="true"]{background:white;color:var(--ink);box-shadow:0 1px 4px rgba(12,34,56,.12)}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{display:none}
.stButton>button{border-radius:10px;border:1px solid var(--line);font-weight:600;transition:all .15s;min-height:44px}
.stButton>button:hover{border-color:var(--ink);color:var(--ink);transform:translateY(-1px);box-shadow:0 4px 12px rgba(12,34,56,.1)}
:focus-visible{outline:3px solid #0d9488!important;outline-offset:2px}
.banner{background:#fff7e0;border:1px solid #f1dc9c;color:#6b5200;border-radius:10px;padding:8px 14px;font-size:.86rem;margin-bottom:12px}
.hero{position:relative;overflow:hidden;border:1px solid var(--gridM);border-radius:20px;margin:4px 0 20px;padding:30px 34px 0;color:var(--ink);
 background-color:var(--paper);
 background-image:linear-gradient(var(--gridM) 1px,transparent 1px),linear-gradient(90deg,var(--gridM) 1px,transparent 1px),linear-gradient(var(--gridm) 1px,transparent 1px),linear-gradient(90deg,var(--gridm) 1px,transparent 1px);
 background-size:48px 48px,48px 48px,12px 12px,12px 12px;animation:rise .6s ease-out both}
.hero:before{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(255,246,245,.96) 0%,rgba(255,246,245,.9) 42%,rgba(255,246,245,.0) 78%);pointer-events:none}
.hero>*{position:relative}
.hero .eyebrow{color:var(--sig)}
.hero h1{font-size:3.3rem;font-weight:800;margin:4px 0 0;padding:0;line-height:1}
.hero p.lede{color:var(--ink);margin:12px 0 0;max-width:560px;font-size:1.12rem;line-height:1.5}
.hero svg{display:block;width:100%;height:auto;margin-top:6px}
.trace{stroke-dasharray:1600;stroke-dashoffset:1600;animation:draw 2.2s .3s ease-out forwards}
.readouts{display:grid;grid-template-columns:repeat(4,1fr);margin:0 -34px;background:var(--ink);color:white}
.ro{padding:14px 22px;border-right:1px solid rgba(255,255,255,.14)}
.ro:last-child{border-right:0}
.ro b{display:block;font-family:'IBM Plex Mono',monospace;font-size:1.2rem;font-weight:600;color:#fff}
.ro span{font-size:.8rem;color:#b9cddc;line-height:1.35;display:block;margin-top:2px}
@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
@keyframes draw{to{stroke-dashoffset:0}}
@media(prefers-reduced-motion:reduce){.hero,.trace{animation:none}.trace{stroke-dashoffset:0}.stButton>button,[data-testid="stMetric"]{transition:none}}
.eyebrow{font-size:.74rem;font-weight:700;letter-spacing:.16em;color:var(--teal);text-transform:uppercase}
.reason{background:#ecf9f6;border-left:4px solid var(--teal);border-radius:8px;padding:16px 20px;color:#163e47;line-height:1.55}
.pill{display:inline-block;border-radius:999px;padding:4px 12px;font-weight:700;font-size:.82rem;letter-spacing:.02em}
.pill.alert{background:#fde8ec;color:#a3243f;border:1px solid #f4b9c6}
.pill.ok{background:#e7f6f3;color:#0b6f66;border:1px solid #b5e3db}
.timeline{display:flex;flex-wrap:wrap;gap:10px;margin:6px 0 4px}
.tl{flex:1;min-width:150px;background:white;border:1px solid var(--line);border-radius:10px;padding:10px 14px}
.tl small{display:block;color:#566e82;font-size:.74rem;text-transform:uppercase;letter-spacing:.08em;font-weight:600}
.tl b{font-family:'IBM Plex Mono',monospace;font-size:1.15rem;color:var(--ink)}
.tl.model{border-top:4px solid #0d9488}.tl.news{border-top:4px solid #db8b25}.tl.onset{border-top:4px solid #c0435a}.tl.lead{border-top:4px solid #0c2238}
.card{background:white;border:1px solid var(--line);border-radius:14px;padding:18px 22px;margin:4px 0 12px}
.card h4{margin:0 0 6px}
.card ul{margin:4px 0 0 0;padding-left:18px}.card li{margin:4px 0}
.limits{background:#fff9ec;border:1px solid #f1dc9c;border-radius:14px;padding:18px 22px;margin:4px 0 14px}
.small{font-size:.84rem;color:#566e82}
@media(max-width:900px){.readouts{grid-template-columns:1fr 1fr}.ro:nth-child(2){border-right:0}.ro:nth-child(-n+2){border-bottom:1px solid rgba(255,255,255,.14)}.hero h1{font-size:2.4rem}}
@media(max-width:700px){.hero svg text{display:none}.block-container{padding:1rem}.hero{padding:20px 18px 0}.readouts{margin:0 -18px}.ro{padding:12px 14px}.ro b{font-size:1.15rem}[data-testid="stMetricValue"]{font-size:1.3rem}.stTabs [data-baseweb="tab-list"]{overflow:auto}.stTabs [data-baseweb="tab"]{padding:8px 12px}}
</style>""",unsafe_allow_html=True)
sel=m["selection"];CD=sel["selected_cooldown"]
H5=m["B"]["methods"]["refined"]["budgets"]["5.0"];N5=m["B"]["methods"]["NEWS2"]["budgets"]["5.0"]
FA_CUT=100*(1-H5["false_alarms"]/N5["false_alarms"])
st.markdown('<div class="banner"><b>Research prototype. Not for clinical use.</b> Retrospective, de-identified public ICU data. No diagnosis, treatment, triage or live patient monitoring.</div>',unsafe_allow_html=True)
dm=m["demo"];_x=lambda h:60+(h-150)*(780/36)
_xm,_xn,_xo=_x(dm["model_alert_hour"]),_x(dm["NEWS2_alert_hour"]),_x(dm["inferred_onset"])
_trace="M0,120 L60,118 L90,121 L120,117 L150,119 L180,115 L210,118 L240,112 L270,116 L300,109 L330,113 L360,104 L390,108 L420,100 L450,104 L480,95 L510,99 L540,92 L570,96 L600,86 L630,92 L660,80 L690,88 L720,66 L750,78 L780,50 L810,30 L840,10 L870,58 L900,40"
st.markdown(f'''<div class="hero"><div class="eyebrow">DSH Hacks V2 / AI x Healthcare</div><h1>SepsisLens</h1>
<p class="lede">See the warning sooner. Understand every alert. An explainable sepsis early-warning model, tested on a hospital it never trained on, at the same alarm budget as NEWS2.</p>
<svg viewBox="0 0 900 190" role="img" aria-label="Schematic of the featured case: the model alerts at hour {dm["model_alert_hour"]}, the NEWS2-style score at hour {dm["NEWS2_alert_hour"]}, inferred onset at hour {int(dm["inferred_onset"])}">
<path class="trace" d="{_trace}" fill="none" stroke="#0c2238" stroke-width="2.4" stroke-linejoin="round"/>
<line x1="{_xm}" y1="28" x2="{_xm}" y2="160" stroke="#0d9488" stroke-width="2"/><circle cx="{_xm}" cy="{104}" r="6" fill="#0d9488"/>
<line x1="{_xn}" y1="28" x2="{_xn}" y2="160" stroke="#db8b25" stroke-width="2"/><circle cx="{_xn}" cy="{90}" r="6" fill="#db8b25"/>
<line x1="{_xo}" y1="28" x2="{_xo}" y2="160" stroke="#d12f4c" stroke-width="2" stroke-dasharray="4 4"/>
<rect x="{_xm}" y="162" width="{_xo-_xm}" height="6" rx="3" fill="#0d9488" opacity=".35"/>
<g font-family="IBM Plex Mono,monospace" font-size="12" font-weight="600">
<text x="{_xm-6}" y="20" text-anchor="end" fill="#0b6f66">MODEL ALERT h{dm["model_alert_hour"]}</text>
<text x="{_xn+6}" y="20" fill="#a2600f">NEWS2 h{dm["NEWS2_alert_hour"]}</text>
<text x="{_xo+6}" y="140" fill="#a3243f">ONSET h{int(dm["inferred_onset"])}</text>
<text x="898" y="184" text-anchor="end" font-size="10" font-weight="500" fill="#566e82">featured case, schematic trace</text>
<text x="{_xm+4}" y="184" fill="#0c2238">{int(dm["default_model_lead"])} h lead</text></g></svg>
<div class="readouts">
<div class="ro"><b>{FA_CUT:.0f}% fewer alarms</b><span>outside-window: {H5["false_alarms"]:,} vs {N5["false_alarms"]:,} for NEWS2-style</span></div>
<div class="ro"><b>{H5["caught_pct"]:.1f}% vs {N5["caught_pct"]:.1f}%</b><span>septic patients caught: similar (intervals overlap)</span></div>
<div class="ro"><b>{m["B"]["cohort"]["patients"]:,}</b><span>unseen Hospital B patients in the external test</span></div>
<div class="ro"><b>Every alert explained</b><span>SHAP reasons, replayed hour by hour</span></div>
</div></div>''',unsafe_allow_html=True)
with st.sidebar:
 st.markdown("### SepsisLens")
 st.caption("A research lens on early warning")
 st.markdown("**60-second tour**")
 st.markdown("1. **Patient Replay**: press *Jump to model alert*, then *Jump to NEWS2 alert*.\n2. Scroll to the **explanation** to see why the alert fired.\n3. **Alarm Budget**: slide the workload and compare with NEWS2.\n4. **Trust & Validation**: the honest limits and full tables.")
 st.markdown("---")
 st.markdown("**Training:** Hospital A  \n**External test:** Hospital B")
 st.metric("External test patients",f'{m["B"]["cohort"]["patients"]:,}')
 st.metric("External patient-hours",f'{m["B"]["cohort"]["hours"]:,}')
 st.caption(f'Dashboard replay: {m["demo"]["patients"]} B patients. All validation metrics use the full held-out cohort.')
 st.markdown("---")
 st.caption("Causal hourly features | Patient-separated evaluation | A-only calibration")
 st.caption("Model scores support ranking; they are not a clinical probability of sepsis.")
cooldown=st.session_state.get("cooldown",CD)
tabs=st.tabs(["Patient Replay","Alarm Budget","Trust & Validation","About"])
def fmt(x,d=1,suffix=""):
 return "N/A" if x is None or (isinstance(x,float) and np.isnan(x)) else f"{x:,.{d}f}{suffix}"
def interval(ci,d=3):
 return "unavailable" if not ci or ci[0] is None else f"{ci[0]:.{d}f} to {ci[1]:.{d}f}"
def style(fig,height=340):
 fig.update_layout(template="plotly_white",height=height,margin=dict(l=10,r=10,t=40,b=30),hovermode="x unified",
 font=dict(family="Instrument Sans, Arial",color=NAVY,size=13),legend=dict(orientation="h",y=1.14,x=0),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="white")
 fig.update_xaxes(showgrid=False,linecolor="#dce8ed");fig.update_yaxes(gridcolor="#e9f0f3",zeroline=False)
 return fig
def set_hour(h):st.session_state["replay_hour"]=int(h)
def set_patient(p):st.session_state["patient"]=p
@st.cache_data
def sample_cases(cd,signature):
 pol=sel["policies"]["refined"][str(cd)]["5.0"];npol=sel["policies"]["NEWS2"][str(cd)]["5.0"];rows=[]
 for pid,g in patients.groupby("patient_id"):
  g=g.sort_values("hour").reset_index(drop=True);pos=g[g.SepsisLabel==1]
  if pos.empty or pos.hour.iloc[0]==1:continue
  on=int(pos.hour.iloc[0]+6);ctx={"patient":np.zeros(len(g),dtype=int),"hour":g.hour.to_numpy()}
  def first(score,pl):
   a=g[apply_policy(g[score].to_numpy(),ctx,pl,tie_keys(g))];u=a[(a.hour>=on-12)&(a.hour<on)]
   return int(u.hour.iloc[0]) if len(u) else None
  rows.append({"patient":pid,"model":first("refined",pol),"news":first("NEWS2",npol)})
 return pd.DataFrame(rows)
def interp_catch(name,cd,rate):
 c=m["B"]["methods"][name]["cooldowns"][str(cd)];xs=[v["alert_rate"] for v in c.values()];ys=[v["caught_pct"] for v in c.values()]
 return float(np.interp(rate,xs,ys)) if xs[0]<=rate<=xs[-1] else None
with tabs[0]:
 st.markdown("#### The hours before the label")
 st.caption("A retrospective replay. Move the cursor, or use the jump buttons, to reveal only measurements and predictions available by that hour.")
 ids=patients.patient_id.unique().tolist();default=m["demo"]["default_patient"]
 ids=[default]+sorted(x for x in ids if x!=default)
 cases=sample_cases(cooldown,(ROOT/"demo/patients.parquet").stat().st_mtime_ns)
 missed=cases[cases.model.isna()&cases.news.notna()].patient.tolist() or cases[cases.model.isna()].patient.tolist()
 later=cases[cases.model.notna()&cases.news.notna()&(cases.model>cases.news)].patient.tolist()
 rng=np.random.default_rng(7);rand_pick=str(rng.choice(sorted(patients.patient_id.unique())))
 cb=st.columns(4)
 cb[0].button("Featured case (best-case)",on_click=set_patient,args=(default,),width="stretch")
 cb[1].button("A case the model missed",on_click=set_patient,args=(missed[0],),width="stretch",disabled=not missed)
 cb[2].button("A case NEWS2 caught sooner",on_click=set_patient,args=(later[0],),width="stretch",disabled=not later)
 cb[3].button("A random patient",on_click=set_patient,args=(rand_pick,),width="stretch")
 patient=st.selectbox("Hospital B patient",ids,key="patient",format_func=lambda x:f"{x}  (featured example)" if x==default else x)
 d=patients[patients.patient_id==patient].sort_values("hour").reset_index(drop=True)
 maxhour=int(d.hour.max());minhour=int(d.hour.min())
 policy=sel["policies"]["refined"][str(cooldown)]["5.0"];threshold=policy["threshold"]
 news_policy=sel["policies"]["NEWS2"][str(cooldown)]["5.0"]
 context={"patient":np.zeros(len(d),dtype=int),"hour":d.hour.to_numpy()}
 alarm_mask=apply_policy(d.refined.to_numpy(),context,policy,tie_keys(d))
 news_mask=apply_policy(d.NEWS2.to_numpy(),context,news_policy,tie_keys(d))
 positive=d[d.SepsisLabel==1];censored=not positive.empty and positive.hour.iloc[0]==1
 onset=None if positive.empty or censored else int(positive.hour.iloc[0]+6)
 alerts=d[alarm_mask];news_alerts=d[news_mask]
 def first_useful(a):
  if onset is None:return int(a.hour.iloc[0]) if not a.empty else None
  u=a[(a.hour>=onset-12)&(a.hour<onset)]
  return int(u.hour.iloc[0]) if not u.empty else None
 model_hit=first_useful(alerts);news_hit=first_useful(news_alerts)
 if st.session_state.get("last_patient")!=patient:
  start_hour=min(maxhour,minhour+18)
  if onset is not None and model_hit is not None:start_hour=min(maxhour,model_hit+1)
  st.session_state["replay_hour"]=start_hour;st.session_state["last_patient"]=patient
 b=st.columns(4)
 b[0].button("Jump to start",on_click=set_hour,args=(minhour,),width="stretch",disabled=maxhour<=minhour)
 b[1].button(f"Jump to model alert{f' (h {model_hit})' if model_hit is not None else ''}",on_click=set_hour,args=(model_hit or minhour,),width="stretch",disabled=model_hit is None or maxhour<=minhour,type="primary")
 b[2].button(f"Jump to NEWS2 alert{f' (h {news_hit})' if news_hit is not None else ''}",on_click=set_hour,args=(news_hit or minhour,),width="stretch",disabled=news_hit is None or maxhour<=minhour)
 b[3].button("Jump to end",on_click=set_hour,args=(maxhour,),width="stretch",disabled=maxhour<=minhour)
 hour=st.slider("Replay hour",minhour,maxhour,key="replay_hour") if maxhour>minhour else minhour
 shown=d[d.hour<=hour];row=shown.iloc[-1]
 observed_alerts=alerts[alerts.hour<=hour];firstalert=int(alerts.hour.iloc[0]) if not alerts.empty else None
 latest_alert=int(observed_alerts.hour.iloc[-1]) if not observed_alerts.empty else None
 def tl(cls,label,value):return f'<div class="tl {cls}"><small>{label}</small><b>{value}</b></div>'
 lead=f"{news_hit-model_hit} h earlier" if model_hit is not None and news_hit is not None and news_hit>model_hit else ("same hour" if model_hit is not None and model_hit==news_hit else "n/a")
 onset_txt="left-censored" if censored else ("no sepsis label" if onset is None else f"hour {onset}"+(" (after recording)" if onset>maxhour else ""))
 st.markdown('<div class="timeline">'+tl("model","SepsisLens alert in warning window","n/a" if model_hit is None else f"hour {model_hit}")+tl("news","NEWS2-style alert in warning window","n/a" if news_hit is None else f"hour {news_hit}")+tl("onset","Inferred onset",onset_txt)+tl("lead","SepsisLens lead over NEWS2",lead)+'</div>',unsafe_allow_html=True)
 if patient==default and cooldown==m["demo"]["cooldown"] and m["demo"]["comparison_available"]:
  st.success(f'This illustrative case: model warns {m["demo"]["default_model_lead"]:.0f} h before inferred onset and {m["demo"]["lead_over_NEWS2"]:.0f} h before NEWS2. Both are observed emitted alerts under the same cooldown. It was selected to illustrate an early alert, so it is not typical performance.')
 both=cases[cases.model.notna()&cases.news.notna()]
 st.markdown(f'<div class="limits"><b>Is the featured case typical? No, and here is the evidence.</b> In this {m["demo"]["patients"]}-patient replay sample, {len(cases)} patients have an evaluable onset. The model alerts inside the 12 h window for {int(cases.model.notna().sum())} of them and NEWS2-style for {int(cases.news.notna().sum())}. Where both alert, the model is earlier in {int((both.model<both.news).sum())} cases and NEWS2-style is earlier in {int((both.model>both.news).sum())} (ties: {int((both.model==both.news).sum())}). The sample is tiny, so treat these as illustration; the full-cohort numbers are in Alarm Budget and Trust &amp; Validation. Use the buttons above to inspect a miss.</div>',unsafe_allow_html=True)
 st.caption(f"Warning window = the 12 h before inferred onset (first SepsisLabel=1 hour + 6; inferred from shifted labels, not independently observed). Alerts use the 5 alerts/100 h policy with a {cooldown} h cooldown.")
 left,right=st.columns([3,1])
 with right:
  firing=row.refined>=threshold
  st.markdown(f'<span class="pill {"alert" if firing else "ok"}">{"ABOVE ALERT THRESHOLD" if firing else "Below alert threshold"}</span>',unsafe_allow_html=True)
  prev=d[d.hour<=hour-1]
  st.metric(f"SepsisLens score, hour {hour}",fmt(row.refined,3),delta=None if prev.empty else f"{row.refined-prev.refined.iloc[-1]:+.3f} vs previous hour",delta_color="inverse")
  st.caption(f'A-selected threshold: {threshold:.4f}')
  st.metric("NEWS2-style points",fmt(row.NEWS2,0))
  st.caption(f'Model alerts so far: {len(observed_alerts)} | NEWS2 alerts so far: {int((news_mask&(d.hour.to_numpy()<=hour)).sum())}')
 with left:
  chart=make_subplots(specs=[[{"secondary_y":True}]])
  if onset is not None:chart.add_vrect(x0=onset-12,x1=onset,fillcolor="rgba(192,67,90,.07)",line_width=0,annotation_text="12 h warning window",annotation_position="top left",annotation_font_color=RED,annotation_font_size=11)
  chart.add_trace(go.Scatter(x=shown.hour,y=shown.refined,name="SepsisLens score",line=dict(color=TEAL,width=3),fill="tozeroy",fillcolor="rgba(13,148,136,.07)"),secondary_y=False)
  chart.add_trace(go.Scatter(x=shown.hour,y=shown.NEWS2,name="NEWS2-style points",line=dict(color=AMBER,width=1.2,shape="hv"),opacity=.45),secondary_y=True)
  oa=observed_alerts;na=news_alerts[news_alerts.hour<=hour]
  if not oa.empty:chart.add_trace(go.Scatter(x=oa.hour,y=oa.refined,mode="markers",name="SepsisLens alert",marker=dict(symbol="triangle-up",size=14,color=TEAL,line=dict(color="white",width=1.5))),secondary_y=False)
  if not na.empty:chart.add_trace(go.Scatter(x=na.hour,y=na.NEWS2,mode="markers",name="NEWS2 alert",marker=dict(symbol="diamond",size=12,color=AMBER,line=dict(color="white",width=1.5))),secondary_y=True)
  chart.add_hline(y=threshold,line_dash="dot",line_color=TEAL,annotation_text="A-locked threshold",annotation_position="top left",annotation_font_color=TEAL)
  if onset is not None:chart.add_vline(x=onset,line_dash="dash",line_color=RED,annotation_text="Inferred onset",annotation_position="bottom left",annotation_font_color=RED)
  chart.add_vline(x=hour,line_color="#8aa2b8",line_dash="dot")
  chart.update_xaxes(title="ICU recording hour (display only; excluded from model)",range=[minhour,max(maxhour,onset or 0)+1])
  chart.update_yaxes(title="Early-warning score",secondary_y=False,range=[0,max(.15,float(d.refined.max())*1.15,threshold*1.15)])
  chart.update_yaxes(title="NEWS2-style points",secondary_y=True,rangemode="tozero",showgrid=False)
  st.plotly_chart(style(chart,380),width="stretch")
 if censored:st.info("The first recorded label is already positive: onset is left-censored, so no exact onset or warning-time claim is made.")
 elif onset is not None and onset>maxhour:st.caption("Inferred onset falls after the available recording. It is inferred from the shifted label, not observed directly.")
 elif onset is None:st.caption("No positive sepsis label in this recording.")
 cols=st.columns(6)
 before=d[d.hour<=hour-6]
 for col,v,unit in zip(cols,["HR","Resp","Temp","SBP","MAP","O2Sat"],["bpm","/min","C","mmHg","mmHg","%"]):
  dv=None if before.empty or pd.isna(row[v]) or pd.isna(before[v].iloc[-1]) else f"{row[v]-before[v].iloc[-1]:+.1f} vs 6 h ago"
  col.metric(f"{v} ({unit})",fmt(row[v],1),delta=dv,delta_color="off")
 st.caption("Values shown are last-observation-carried-forward; a displayed value may not have been measured this hour.")
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
 ex_l,ex_r=st.columns([1.15,1])
 with ex_l:
  top=factors[:8][::-1]
  bar=go.Figure(go.Bar(x=[f["shap"] for f in top],y=[pretty(f["feature"])+" = "+("not observed" if f["value"] is None else f'{f["value"]:.2f}') for f in top],orientation="h",
   marker_color=[RED if f["shap"]>0 else TEAL for f in top],
   hovertemplate="%{y}<br>contribution %{x:+.3f} log-odds<extra></extra>"))
  bar.add_vline(x=0,line_color="#9fb3c4")
  bar.update_layout(title=dict(text=f"Top factors at hour {int(erow.hour)}  (red raises risk, teal lowers)",font=dict(size=14)),showlegend=False)
  bar.update_xaxes(title="Contribution to model log-odds (SHAP)")
  st.plotly_chart(style(bar,360),width="stretch")
 with ex_r:
  note=nurse_note(factors,float(erow.refined),threshold)
  st.markdown(f'<div class="reason"><b>Model explanation | hour {int(erow.hour)}</b><br>{note}</div>',unsafe_allow_html=True)
  st.caption("SHAP describes the selected base tree in raw log-odds; it is not a causal explanation or a calibrated clinical probability. Each label shows the feature value the model saw.")
 if stack_values is not None:
  stack_row=stack_values[(stack_values.patient_id==patient)&(stack_values.hour==erow.hour)].drop(columns=["patient_id","hour"]).iloc[0]
  st.markdown("**Final ensemble explanation**")
  st.caption("Exact additive contributions to the final linear stacker log-odds, relative to its intercept. The SHAP card above explains only the base model.")
  st.dataframe(pd.DataFrame({"Factor":stack_row.index,"Final log-odds contribution":stack_row.values}).sort_values("Final log-odds contribution",key=abs,ascending=False),hide_index=True,width="stretch")
 with st.expander("Inspect all top 35 factors"):
  st.dataframe(pd.DataFrame([{"Factor":pretty(f["feature"]),"Feature":f["feature"],"Value":f["value"],"SHAP (log-odds)":f["shap"],"Direction":f["direction"]} for f in factors]),hide_index=True,width="stretch",
   column_config={"Value":st.column_config.NumberColumn(format="%.2f"),"SHAP (log-odds)":st.column_config.NumberColumn(format="%+.3f")})
 st.markdown("#### Vital-sign trends")
 st.caption("Blood pressure: MAP in dark blue, systolic in light blue.")
 vit=make_subplots(rows=2,cols=2,subplot_titles=["Heart rate","Respiratory rate","Blood pressure","Temperature"])
 for v,r,c,color in [("HR",1,1,TEAL),("Resp",1,2,TEAL),("MAP",2,1,NAVY),("SBP",2,1,"#6e91b1"),("Temp",2,2,AMBER)]:
  vit.add_trace(go.Scatter(x=shown.hour,y=shown[v],name=v,line=dict(color=color,width=2)),row=r,col=c)
 vit.update_xaxes(range=[minhour,maxhour+1],title="Hour")
 for r,c,unit in [(1,1,"bpm"),(1,2,"breaths/min"),(2,1,"mmHg"),(2,2,"C")]:vit.update_yaxes(title=unit,row=r,col=c)
 st.plotly_chart(style(vit,430).update_layout(showlegend=False,hovermode="x"),width="stretch")
 st.caption(m["demo"]["selection"])
with tabs[1]:
 st.markdown("#### How many alarms can a team absorb?")
 st.write("Pick a workload target (thresholds are fit on Hospital A), then see how many septic patients each method catches on Hospital B, and at what real alarm burden.")
 c1,c2,c3=st.columns([1.3,1,1.2])
 with c1:budget=st.slider("Target A alerts per 100 patient-hours",.5,10.,5.,.5)
 with c2:cooldown=st.select_slider("Cooldown (hours)",options=sel["cooldowns"],value=CD,key="cooldown")
 with c3:method=st.selectbox("Model version",["refined","vitals_labs","vitals"],format_func=lambda x:NAMES[x])
 st.caption(m["protocol"]["cooldown"])
 ops={name:m["B"]["methods"][name]["cooldowns"][str(cooldown)][str(float(budget))] for name in [method,"NEWS2"]}
 mo,no=ops[method],ops["NEWS2"]
 spec=[("Septic patients caught","caught_pct",1,"%","normal"),("Outside-window alarms","false_alarms",0,"","inverse"),("Catches per 100 alarms","catches_per_100_alarms",1,"","normal"),("Median warning","median_warning",1," h","normal"),("Actual B alarms /100h","alert_rate",1," /100h","inverse")]
 for name,op in [(method,mo),("NEWS2",no)]:
  st.markdown(f"##### {NAMES[name]}")
  cols=st.columns(5)
  for col,(label,key,dd,suffix,dc) in zip(cols,spec):
   delta=None
   if name==method and op[key] is not None and no[key] is not None:
    diff=op[key]-no[key];delta=f"{diff:+,.{dd}f}{' pp' if suffix=='%' else suffix.replace(' /100h','')} vs NEWS2"
   col.metric(label,fmt(op[key],dd,suffix),delta=delta,delta_color=dc)
   col.caption("95% CI: "+interval(op["ci"][key],0 if key=="false_alarms" else 1))
  st.caption(f'{op["caught"]} distinct patients caught; {op["alarms"]:,} hourly alarms. Eligible septic patients: {op["eligible_septic"]:,}.')
 if mo["caught_pct"] is not None and no["caught_pct"] is not None:
  ci_m,ci_n=mo["ci"]["caught_pct"],no["ci"]["caught_pct"]
  overlap=ci_m[0] is not None and ci_n[0] is not None and ci_m[0]<=ci_n[1] and ci_n[0]<=ci_m[1]
  more="SepsisLens" if mo["caught_pct"]>no["caught_pct"] else ("NEWS2-style" if no["caught_pct"]>mo["caught_pct"] else "Neither")
  fewer="SepsisLens" if mo["alarms"]<no["alarms"] else ("NEWS2-style" if no["alarms"]<mo["alarms"] else "Neither")
  st.info(f"**At this setting:** {more} catches more patients ({mo['caught_pct']:.1f}% vs {no['caught_pct']:.1f}%) and {fewer} fires fewer alarms ({mo['alarms']:,} vs {no['alarms']:,})."+(" The catch-rate 95% intervals overlap, so treat the catch difference as uncertain." if overlap else ""))
 mm=interp_catch(method,cooldown,no["alert_rate"]);nm=interp_catch("NEWS2",cooldown,mo["alert_rate"])
 if mm is not None and nm is not None:
  st.markdown(f'<div class="card"><h4>Fair comparison at matched real alarm burden</h4>Budget sliders are targets fit on Hospital A, so real Hospital B rates differ. Reading the curves below at the same real burden: at {no["alert_rate"]:.2f} alerts/100 h (NEWS2-style setting) {SHORT[method]} catches about <b>{mm:.1f}%</b> vs <b>{no["caught_pct"]:.1f}%</b>; at {mo["alert_rate"]:.2f} alerts/100 h ({SHORT[method]} setting) NEWS2-style catches about <b>{nm:.1f}%</b> vs <b>{mo["caught_pct"]:.1f}%</b>. <span class="small">Linear interpolation between the budget grid points; point estimates without confidence intervals.</span></div>',unsafe_allow_html=True)
 fig=go.Figure()
 for name,color in [(method,TEAL),("NEWS2",AMBER)]:
  bb=m["B"]["methods"][name]["cooldowns"][str(cooldown)]
  fig.add_trace(go.Scatter(x=[v["alert_rate"] for v in bb.values()],y=[v["caught_pct"] for v in bb.values()],mode="lines+markers",name=SHORT[name],line=dict(color=color,width=3),marker=dict(size=6),
   customdata=list(bb.keys()),hovertemplate=SHORT[name]+"<br>A target %{customdata}/100h<br>actual %{x:.2f}/100h<br>caught %{y:.1f}%<extra></extra>"))
  op=ops[name]
  fig.add_trace(go.Scatter(x=[op["alert_rate"]],y=[op["caught_pct"]],mode="markers",name=f"{SHORT[name]} at current setting",marker=dict(size=18,color=color,symbol="circle-open",line=dict(width=3)),showlegend=False,hoverinfo="skip"))
 fig.update_layout(title=dict(text="Catch rate vs real alarm burden (up and to the left is better)",font=dict(size=14)))
 style(fig,400).update_layout(legend=dict(x=.98,y=.06,xanchor="right",yanchor="bottom",orientation="v",bgcolor="rgba(255,255,255,.85)"))
 fig.update_xaxes(title="Actual B emitted alerts / 100 patient-hours");fig.update_yaxes(title="Septic patients caught (%)",range=[0,100])
 st.plotly_chart(fig,width="stretch")
 st.caption("Circles mark the current setting. "+m["protocol"]["catch"]+" "+m["protocol"]["false_alarm"])
 st.info(m["protocol"]["budget"])
 with st.expander("How the alarm counts and confidence intervals work"):
  for k in ["catch","false_alarm","catches_per_100_alarms","warning","budget","ci"]:st.write(f"**{k.replace('_',' ').title()}** | {m['protocol'][k]}")
with tabs[2]:
 st.markdown("#### Train here. Test somewhere else.")
 key=m["B"]["methods"]["refined"];news=m["B"]["methods"]["NEWS2"];a_key=m["A_validation"]["methods"]["refined"]
 k2,n2=key["budgets"]["2.0"],news["budgets"]["2.0"]
 st.markdown(f'''<div class="limits"><h4 style="margin:0 0 6px">Read this first: what the results do and do not show</h4><ul>
<li><b>Fewer alarms is the clearest win.</b> At the 5/100 h target, SepsisLens fired {key["budgets"]["5.0"]["alarms"]:,} alarms vs {news["budgets"]["5.0"]["alarms"]:,} for NEWS2-style ({FA_CUT:.0f}% fewer outside-window alarms).</li>
<li><b>The catch-rate gain is small and uncertain:</b> {H5["caught_pct"]:.1f}% (95% CI {interval(H5["ci"]["caught_pct"],1)}) vs {N5["caught_pct"]:.1f}% ({interval(N5["ci"]["caught_pct"],1)}). The intervals overlap.</li>
<li><b>At a tighter 2/100 h target, NEWS2-style catches slightly more</b> ({n2["caught_pct"]:.1f}% vs {k2["caught_pct"]:.1f}%), while firing about twice the alarms ({n2["alert_rate"]:.2f} vs {k2["alert_rate"]:.2f} per 100 h).</li>
<li><b>At equal real alarm burden the gap is larger than 2 points</b> (about {interp_catch("refined",CD,N5["alert_rate"]):.1f}% vs {N5["caught_pct"]:.1f}% at NEWS2-style's {N5["alert_rate"]:.2f}/100 h; interpolated from the budget curve, no confidence interval).</li>
<li>Budgets are targets fit on Hospital A; actual Hospital B rates differ and are always shown. Part of the gain comes from the shared {CD} h cooldown.</li>
<li>Retrospective data. Hospital B had been evaluated before this refinement, so it is an external check, not a pristine holdout. Not a medical device.</li>
</ul></div>''',unsafe_allow_html=True)
 cols=st.columns(4)
 cols[0].metric("B hourly AUROC",fmt(key["auroc"],3),delta=f'{key["auroc"]-news["auroc"]:+.3f} vs NEWS2-style')
 cols[1].metric("AUROC change B - A",fmt(key["auroc"]-a_key["auroc"],3))
 cols[2].metric("Model caught at A target 5",fmt(key["budgets"]["5.0"]["caught_pct"],1,"%"))
 cols[3].metric("NEWS2 caught at A target 5",fmt(news["budgets"]["5.0"]["caught_pct"],1,"%"))
 st.caption(f'Selected shared cooldown: {CD} h. Actual B alarms/100h: model {key["budgets"]["5.0"]["alert_rate"]:.2f}; NEWS2 {news["budgets"]["5.0"]["alert_rate"]:.2f}. Thresholds are frozen from A; these are not matched B alarm rates.')
 st.caption(f'A-only selected candidate: {sel["selected_candidate"]}. Selection uses {sel["A_selection_patients"]:,} patients, disjoint from {sel["A_stack_fit_patients"]:,} stack-fit patients.')
 pct=st.column_config.NumberColumn(format="%.1f");r3=st.column_config.NumberColumn(format="%.3f");r4=st.column_config.NumberColumn(format="%.4f")
 st.markdown("#### Before vs after")
 before_rows=[]
 for name in ["vitals_labs","NEWS2","qSOFA"]:
  v=m["before"]["B"]["methods"][name]
  before_rows.append({"Version":"Before (legacy B ranking)","Method":NAMES[name],"AUROC":v["auroc"],"AUPRC":v["auprc"],"Utility":v["operating"]["utility"],**{f"Caught at {b} (%)":v["budgets"][str(float(b))]["caught_pct"] for b in [2,5,10]}})
 for name in ["refined","NEWS2","qSOFA"]:
  v=m["B"]["methods"][name]
  before_rows.append({"Version":"After (A-locked thresholds)","Method":NAMES[name],"AUROC":v["auroc"],"AUPRC":v["auprc"],"Utility":v["operating"]["utility"],**{f"Caught at {b} (%)":v["budgets"][str(float(b))]["caught_pct"] for b in [2,5,10]}})
 st.dataframe(pd.DataFrame(before_rows),hide_index=True,width="stretch",column_config={"AUROC":r3,"AUPRC":r4,"Utility":r4,**{f"Caught at {b} (%)":pct for b in [2,5,10]}})
 st.caption("Legacy before numbers used retrospective B ranking and no cooldown. After numbers use A-only thresholds and shared cooldown. They are different operating protocols; AUROC/AUPRC remain comparable. Download metrics for the original model under every new policy and cooldown.")
 st.markdown("#### Discrimination: Hospital A validation vs Hospital B")
 st.write("Hospital B is held out from fitting, hyperparameter selection, probability calibration, and operational threshold selection.")
 rows=[]
 for name in NAMES:
  a=m["A_validation"]["methods"][name];b=m["B"]["methods"][name]
  rows.append({"Method":NAMES[name],"A validation AUROC":a["auroc"],"B AUROC":b["auroc"],"B AUROC 95% CI":interval(b["ci"]["auroc"]),
   "A validation AUPRC":a["auprc"],"B AUPRC":b["auprc"],"B AUPRC 95% CI":interval(b["ci"]["auprc"]),
   "AUROC change (B - A)":b["auroc"]-a["auroc"]})
 st.dataframe(pd.DataFrame(rows),hide_index=True,width="stretch",column_config={"A validation AUROC":r3,"B AUROC":r3,"A validation AUPRC":r4,"B AUPRC":r4,"AUROC change (B - A)":st.column_config.NumberColumn(format="%+.3f")})
 st.markdown("#### A-locked operational thresholds")
 st.caption(m["protocol"]["thresholds"])
 rows=[]
 for name in NAMES:
  b=m["B"]["methods"][name];op=b["operating"]
  rows.append({"Method":NAMES[name],"Threshold":b["threshold"],"B alarms /100h":op["alert_rate"],
   "B utility":op["utility"],"Utility 95% CI":interval(op["ci"]["utility"]),"Caught %":op["caught_pct"],
   "Caught % 95% CI":interval(op["ci"]["caught_pct"],1),"Median warning (h)":op["median_warning"],
   "Warning 95% CI":interval(op["ci"]["median_warning"],1)})
 st.dataframe(pd.DataFrame(rows),hide_index=True,width="stretch",column_config={"Threshold":r4,"B alarms /100h":st.column_config.NumberColumn(format="%.2f"),"B utility":r4,"Caught %":pct,"Median warning (h)":pct})
 st.caption(m["protocol"]["utility"])
 c1,c2=st.columns(2)
 c1.image(str(ROOT/"reports/figures/roc.png"),caption="Full Hospital B ROC",width="stretch")
 c2.image(str(ROOT/"reports/figures/calibration.png"),caption="Reliability against challenge labels; early-warning scores may use a different training target",width="stretch")
 st.markdown("#### Subgroup audit | Hospital B")
 audit=st.selectbox("Subgroup model",list(NAMES),format_func=lambda x:NAMES[x])
 sg=pd.DataFrame(m["B"]["methods"][audit]["subgroups"]).T.reset_index(names="Subgroup")
 if "auroc_ci" in sg.columns:sg["auroc_ci"]=sg["auroc_ci"].map(interval)
 sg=sg.rename(columns={"hours":"Hours","patients":"Patients","positive_hours":"Positive hours","auroc":"AUROC","auroc_ci":"AUROC 95% CI"})
 st.dataframe(sg,hide_index=True,width="stretch",column_config={"AUROC":r3})
 st.caption("Recorded binary sex is the dataset's Gender field; it does not describe gender identity. Small groups and positive-label counts limit interpretation.")
 st.markdown("#### Scope and limitations")
 st.write("Retrospective ICU data cannot establish clinical benefit. A/B recordings represent different hospital systems, not a prospective deployment. Missingness and test-ordering can reflect local workflow. Forward-filled values may be stale. Partial NEWS2 and qSOFA omit unavailable clinical assessments. Model calibration can drift across sites.")
 st.write(f'Onset is inferred from shifted labels. First-hour-positive cases excluded from onset-based metrics: {m["B"]["onset_left_censored"]:,} on B; hourly discrimination and official utility retain them.')
 st.write(m["protocol"]["ci"])
 st.write("A validation participates in tuning and threshold selection, so its reported performance may be optimistic. External B results are the principal check. No prospective safety, fairness, or mortality claims are made.")
 st.download_button("Download complete metrics",json.dumps(m,indent=2),file_name="sepsislens_metrics.json",mime="application/json")
with tabs[3]:
 st.markdown("#### Early warning needs evidence, not just a score.")
 sources=m["citations"]
 cols=st.columns(3)
 cols[0].metric("US adults affected each year",f'{sources["CDC"]["adults_yearly"]/1e6:.1f}M')
 cols[1].metric("Deaths or hospice discharges",f'{sources["CDC"]["deaths_or_hospice"]/1000:.0f}K+')
 cols[2].metric("Cases missed in Epic study",f'{sources["Wong"]["missed_pct"]}%')
 st.markdown(f'[CDC: US annual sepsis burden]({sources["CDC"]["url"]})')
 st.markdown(f'{sources["Wong"]["context"]} [Wong et al., JAMA Internal Medicine (2021)]({sources["Wong"]["url"]})')
 st.markdown(f'TREWS: **{sources["TREWS"]["relative_reduction_pct"]}% adjusted relative mortality reduction**. {sources["TREWS"]["context"]} [Adams et al., Nature Medicine (2022)]({sources["TREWS"]["url"]})')
 st.markdown("#### How is this different from the 2019 PhysioNet challenge?")
 st.markdown(f'<div class="card"><ul><li><b>We use the public challenge data, but we ask a different question.</b> The challenge ranked hourly predictions by one utility score. We ask: at a fixed alarm budget, with a cooldown, how does an explainable model compare with NEWS2 on a hospital it never saw?</li><li><b>Strict cross-hospital protocol.</b> Training, model selection and alert thresholds all use Hospital A only; Hospital B is scored once with frozen thresholds, and the comparison uses an identical alert policy for every method.</li><li><b>Alarm burden is a first-class result.</b> Alarms per 100 patient-hours, catches per 100 alarms and warning time are reported, not just AUROC.</li><li><b>Every alert is explained</b> with per-feature SHAP reasons and a replay of what was known hour by hour.</li><li><b>We do not claim to beat challenge entries.</b> Our official utility is {m["B"]["methods"]["refined"]["operating"]["utility"]:.3f} (NEWS2-style {m["B"]["methods"]["NEWS2"]["operating"]["utility"]:.3f}); both are negative because the alert policy is not tuned for that score.</li></ul></div>',unsafe_allow_html=True)
 st.markdown("#### How SepsisLens works")
 s1,s2,s3=st.columns(3)
 s1.markdown('<div class="card"><div class="eyebrow">1. Learn on Hospital A</div><h4>Causal features</h4>Current and past vitals and labs, 6 h trends, hourly changes, shock index and measurement flags. No future data, no admission clocks or identifiers.</div>',unsafe_allow_html=True)
 s2.markdown(f'<div class="card"><div class="eyebrow">2. Lock the policy</div><h4>Alarm budget + {CD} h cooldown</h4>Thresholds per alarm budget are fit on Hospital A, then the model and policy are hashed and frozen before Hospital B is scored.</div>',unsafe_allow_html=True)
 s3.markdown('<div class="card"><div class="eyebrow">3. Test on Hospital B</div><h4>Same rules for every method</h4>SepsisLens, NEWS2-style and qSOFA-style get the identical alarm policy, so the comparison is like for like. Every alert gets SHAP reasons.</div>',unsafe_allow_html=True)
 st.write("Features use current and past vitals/labs, six-hour and longer trends, changes, shock index, and measurement flags. A-only experiments compare early-window objectives, patient weighting, model settings and a linear NEWS2/risk-trend ensemble. A validation selects the final policy. Hospital B is evaluated after the policy lock.")
 st.write("Admission clocks (ICULOS and HospAdmTime), patient identity, hospital identity, labels, and unit indicators are excluded from model inputs. No backward fill or future observations are used.")
 st.markdown("#### Baseline approximations")
 st.write("qSOFA-style uses respiratory rate >=22 and systolic pressure <=100; mental status is unavailable. NEWS2-style uses respiratory rate, oxygen saturation (scale 1), systolic pressure, heart rate and temperature; consciousness, supplemental oxygen and scale-2 eligibility are unavailable. Missing components contribute zero points, potentially understating severity. These partial scores are not validated clinical NEWS2 or qSOFA.")
 st.markdown("#### Open data, reproducible research")
 st.markdown(f'[PhysioNet/CinC Challenge 2019 v1.0.0]({sources["dataset"]["url"]}) | CC BY 4.0. Reyna MA et al. Early Prediction of Sepsis From Clinical Data: The PhysioNet/Computing in Cardiology Challenge 2019. Critical Care Medicine, 2020;48(2):210-217. DOI: 10.1097/CCM.0000000000004145.')
 st.write(f'The {m["demo"]["patients"]}-patient replay bundle is for demonstration. Validation and alarm-budget metrics use the full cohort and come from reports/metrics.json.')
 st.error("NOT FOR CLINICAL USE. Research prototype on retrospective deidentified data. Do not use for diagnosis, triage, treatment decisions, or live patient monitoring.")
st.caption("SepsisLens | DSH Hacks V2 | Open evaluation. Explainable alerts. Honest limitations.")
