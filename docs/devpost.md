# SepsisLens: Devpost submission text

**Tagline:** Explainable sepsis early warning, tested on a hospital it never trained on, and honest about what it can't prove.

**Links:** Demo: [DEMO_URL] | Code: [REPO_URL] | Video: [VIDEO_URL] | One-pager: `docs/sepsislens_onepager.pdf`

> Research prototype. Not a medical device. Not for clinical use.

## Inspiration
Sepsis can become life-threatening within hours, and treating it early matters. But early-warning systems have a second problem: alarm fatigue. A tool that fires constantly gets ignored, and one that is tuned quiet misses patients. We wanted to ask a fair question: at the *same* alarm budget, can a model warn earlier than a standard bedside score, and can it show *why* it alerted, when tested on a hospital it never saw?

## What it does
SepsisLens is an explainable sepsis early-warning research tool with a Streamlit dashboard:
- **Patient Replay:** step through a Hospital B ICU stay hour by hour. Only information available at that hour is shown, with the model score, emitted alerts, and a NEWS2-style comparison.
- **Explanations:** a SHAP breakdown for each alert showing which measurements pushed the score up.
- **Alarm Budget:** choose an alert budget (alerts per 100 patient-hours) and a cooldown and see catch rates against a NEWS2-style and qSOFA-style score.
- **Trust & Validation:** full results, confidence intervals, subgroup checks and every caveat.

Headline result on the external hospital (5 alerts per 100 patient-hours target, 12-hour cooldown): about **14% fewer outside-window alarms** than a NEWS2-style score (27,340 vs 31,841) at a **similar catch rate**: 69.0% of eligible septic patients (634/919) vs 67.0% (616/919), with overlapping 95% intervals. At equal *realized* alarm burden (interpolated from the budget curves, point estimates only) the model catches 71.6% vs 67.0%. The featured demo case (alert 12 h before inferred onset, 10 h before NEWS2) is a best case, and the app also opens a missed case and a case where NEWS2 alerted sooner. In the 300-patient replay sample (25 evaluable septic patients) the model alerts in the window for 19 and NEWS2-style for 16; where both alert, the model is earlier in 5 and NEWS2-style in 8.

**How this differs from the 2019 PhysioNet challenge:** the challenge optimized a utility score; we ask a different question, how many septic patients are caught at a fixed alarm burden compared with a bedside score, tested across hospitals with frozen thresholds, with every alert explained. We do not claim to beat challenge entries (our official utility is -0.013 vs -0.027 for NEWS2-style, both negative).

## How we built it
- **Data:** PhysioNet/CinC Challenge 2019 ICU records (CC BY 4.0). Hospital A is used for training, calibration and alarm-threshold selection; Hospital B (20,000 patients, 761,995 patient-hours) is the external test.
- **Model:** LightGBM on causal hourly features (only current and past data), patient-disjoint splits, SHAP for explanations.
- **Alarm policy:** thresholds fit on Hospital A per target budget plus a causal cooldown that suppresses repeat alerts. Baselines get the identical policy so the comparison is like for like.
- **Evaluation:** a "catch" is at least one alert in the 12 hours before inferred onset; false alarms are alerts outside that window. 500 patient-level bootstrap resamples give confidence intervals. The unmodified official PhysioNet scorer is included.
- **App:** Streamlit reading a small preloaded demo bundle (300 Hospital B patients, about 17 MB total), so it runs with no uploads and no training at startup. Pinned runtime requirements, tests and an AppTest smoke script cover every control.

## Challenges
- **Honest comparison.** Matching "the same alarm budget" is subtle: thresholds are fit to a target on Hospital A, but realized rates on Hospital B drift. We report both the target and the realized rate for every method.
- **Onset is inferred**, not observed (first positive label hour + 6), so warning time is a research estimate.
- **Small effects.** The catch-rate gain at 5 alerts/100 h is +2.0 points, and a paired bootstrap interval spans roughly -1.6 to +5.6 points. We chose to say so rather than overclaim.
- **Reusing a test set.** Hospital B had been evaluated before our refinement, so we froze the model and policy by hash and treat it as an external check, not a pristine holdout.

## Accomplishments that we're proud of
- A genuine cross-hospital evaluation with thresholds frozen before the external test.
- About 14% fewer outside-window alarms than the NEWS2-style baseline at the same target budget with a similar catch rate, and higher hourly AUROC (0.726 vs 0.643).
- A demo that shows its own misses: the app has buttons for a missed case and a case where NEWS2 was faster.
- Alerts you can interrogate: every alert has an explanation, and the replay never shows the future.
- An honest-limits section built into the product, including the result where NEWS2 looks better: at a tighter 2 alerts/100 h target it catches slightly more (36.6% vs 34.8%), though it fires about twice as many alarms (1.61 vs 0.82 per 100 h).

## What we learned
- Report the operating point, not just AUROC: a better score does not automatically mean better patient catches.
- Alarm policy matters. Part of the improvement comes from the cooldown rule, not only the model.
- Plain, checkable numbers (generated from one metrics file) build more trust than big claims.

## What's next
- Validate on additional hospitals and prospectively, with clinicians defining useful alert windows.
- Use the full NEWS2 and qSOFA definitions (consciousness, supplemental oxygen) rather than partial approximations.
- Study fairness more thoroughly than our binary sex and age-band audit.
- Explore how alerts fit real clinical workflow before any claim of benefit.

## Built with
Python 3.11, Streamlit, LightGBM, SHAP, pandas, NumPy, Numba, PyArrow, Plotly, scikit-learn, pytest; PhysioNet/CinC Challenge 2019 dataset; Streamlit Community Cloud; GitHub.
