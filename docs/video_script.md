# SepsisLens final demo video script (DSH Hacks V2)

Every screen and control named below exists in `app/app.py`. Numbers come from `reports/metrics.json` (Hospital B, 5 alerts per 100 patient-hours target, 12 h cooldown). The app has no Play button: replay is done with the **Replay hour** slider and the jump buttons.

| Time | Screen to be on | What to click or show | What I say (word for word) |
|---|---|---|---|
| 0:00-0:15 | Patient Replay (title area at the top of the app) | Stay still on the hero banner. Do not click yet. | Sepsis is a dangerous reaction to infection, and it moves fast. Every hour counts. But hospital alarms go off all day, so nurses start to tune them out. That is called alarm fatigue, and it can hide the one alert that matters. |
| 0:15-0:30 | Patient Replay | Point at the hero stat bar, then the sidebar "60-second tour". | SepsisLens is an early warning model for hospital patients. It spots sepsis risk sooner, and it explains why it raised each alert. We train it on one hospital, then test it on another. |
| 0:30-0:55 | Patient Replay | Patient B_p117534 is already chosen in "Hospital B patient". Point at the "Featured case (best-case)" button, then drag the "Replay hour" slider slowly through the stay. | This is a real patient from a public ICU dataset, with the name removed. We replay the stay one hour at a time. The chart only shows what the hospital knew at that hour. Nothing from the future. |
| 0:55-1:15 | Patient Replay | Click "Jump to model alert (h 169)". Point at the green alert marker and the vitals cards (HR, Resp, Temp, SBP, MAP, O2Sat). | At hour 169, the model raises an alert. Now look at the vitals. They still look fairly normal. A person glancing at this chart might not worry yet. |
| 1:15-1:35 | Patient Replay | Click "Jump to NEWS2 alert (h 179)". Point at the orange diamond and the red "Inferred onset" line. | NEWS2 is a common bedside score. It does not alert until hour 179. That is ten hours later. Our best estimate of when sepsis began is hour 181. So the model warned about twelve hours ahead, ten hours before NEWS2. |
| 1:35-2:00 | Patient Replay (scroll down to "Why this score?") | Select "Latest emitted alert" in the "Explain" radio. Point at the red bars. | Now the important part: why. The red bars show what pushed the risk up. Oxygen support, a faster breathing rate, and a kidney blood test called BUN. These are the model's reasons, not proof of cause. |
| 2:00-2:30 | Alarm Budget | Click the "Alarm Budget" tab. Leave "Target A alerts per 100 patient-hours" at 5 and the cooldown at 12. Point at the model versus NEWS2 numbers. | We tested on Hospital B, which the model never trained on. We gave both methods the same alarm budget. SepsisLens had 14.1 percent fewer false alarms. It caught about the same share of septic patients: 69.0 percent, compared with 67.0 percent. That small gap could be luck, so we do not claim a win there. The clearer result is fewer false alarms, which means less noise for nurses. |
| 2:30-2:50 | Trust & Validation | Click the "Trust & Validation" tab. Point at the yellow "Read this first" card. | Here are the limits. This is old data, not a live hospital, and it is not a medical device. I picked this patient to show an early alert. With a tighter budget of two alerts per hundred hours, NEWS2 catches slightly more. Next step: test it with real clinicians. |
| 2:50-2:58 | Patient Replay (or the hero banner) | Hold on the hero banner. | I am the SepsisLens team. Earlier, quieter, and explainable alerts, with honest limits. |

## Controls in the app (exact names)
- Tabs: Patient Replay, Alarm Budget, Trust & Validation, About
- Patient Replay: buttons "Featured case (best-case)", "A case the model missed", "A case NEWS2 caught sooner", "A random patient"; dropdown "Hospital B patient"; buttons "Jump to start", "Jump to model alert (h 169)", "Jump to NEWS2 alert (h 179)", "Jump to end"; slider "Replay hour"; radio "Explain" ("Current hour", "Latest emitted alert"); expander "Inspect all top 35 factors"
- Alarm Budget: slider "Target A alerts per 100 patient-hours"; slider "Cooldown (hours)"; dropdown "Model version"; expander "How the alarm counts and confidence intervals work"
- Trust & Validation: dropdown "Subgroup model"; button "Download complete metrics"

## Numbers check (all from `reports/metrics.json`)
- False alarms 27,340 vs 31,841 = 14.1% fewer. Caught 634/919 = 69.0% vs 616/919 = 67.0%, intervals overlap.
- Demo patient B_p117534: model alert h169, NEWS2 alert h179, inferred onset h181 (12 h and 10 h).
- At 2 alerts per 100 h NEWS2 catches 36.6% vs 34.8%.

## Recording checklist
- Start on **Patient Replay**, scrolled to the top, patient B_p117534, Replay hour at 170 (hard refresh first).
- Browser zoom 110%, window 1440x900. Close other tabs and mute notifications.
- Rehearse once with a timer. Keep the cursor still while talking.
- Do not say FDA, clinically validated, saves lives, or diagnoses.
- Spoken words: 347. Estimated runtime at about 140 words per minute: 149 seconds (2.5 min), with pauses for clicks about 2:50.
