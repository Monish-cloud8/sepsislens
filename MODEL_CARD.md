# SepsisLens model card
**NOT FOR CLINICAL USE.** Retrospective research and hackathon education only. Not a diagnostic, triage or treatment tool.

## Data and intended population
PhysioNet/CinC Challenge 2019 v1.0.0 ICU recordings. Hospital A for development, Hospital B for external evaluation. Deidentified historical recordings have selection and institutional biases. No live EHR integration.
B has 20,000 patients and 761,995 hourly observations. 223 first-hour-positive B patients are excluded from onset-based metrics.

## Model and training
Class-weighted LightGBM, two variants, no admission-clock features, A-only tuning and patient-disjoint A-only Platt scaling. Seeds and split lists are saved in models/. SHAP explains base-tree log-odds. Explanation templates describe the model, not clinical recommendations.

## External metrics
| Method | B AUROC (95% CI) | B AUPRC (95% CI) | Official utility | Caught % | Warning h |
|---|---|---|---|---|---|
| vitals | 0.659 (0.644-0.674) | 0.035 (0.032-0.039) | 0.076 | 31.0 | 7.0 |
| vitals_labs | 0.726 (0.713-0.738) | 0.045 (0.040-0.051) | 0.058 | 17.0 | 7.5 |
| NEWS2 | 0.643 (0.630-0.656) | 0.027 (0.025-0.030) | 0.044 | 30.5 | 8.0 |
| qSOFA | 0.578 (0.568-0.589) | 0.018 (0.017-0.020) | 0.014 | 23.7 | 8.0 |

## Workload comparison
| Method | Budget /100h | Caught % | Catches /100 alarms | Nonbeneficial hourly alarms | Median warning h |
|---|---|---|---|---|---|
| vitals_labs | 1.0 | 14.7 | 1.77 | 7017 | 7.0 |
| vitals_labs | 2.0 | 23.6 | 1.42 | 14180 | 8.0 |
| vitals_labs | 5.0 | 39.3 | 0.95 | 35997 | 9.0 |
| vitals_labs | 10.0 | 54.2 | 0.65 | 72807 | 11.0 |
| NEWS2 | 1.0 | 15.9 | 1.92 | 7215 | 7.0 |
| NEWS2 | 2.0 | 25.8 | 1.56 | 14529 | 8.0 |
| NEWS2 | 5.0 | 42.0 | 1.01 | 36641 | 9.0 |
| NEWS2 | 10.0 | 59.4 | 0.72 | 73682 | 10.0 |

## Subgroup AUROC for vitals + labs
| Group | Hours | Positive hours | AUROC (95% CI) |
|---|---|---|---|
| Age <50 | 178211 | 2605 | 0.711 (0.682-0.739) |
| Age 50-64 | 236414 | 3301 | 0.727 (0.707-0.748) |
| Age 65-79 | 258942 | 3661 | 0.731 (0.712-0.752) |
| Age 80+ | 88428 | 1213 | 0.741 (0.704-0.776) |
| Female (0) | 350416 | 4664 | 0.746 (0.727-0.764) |
| Male (1) | 411579 | 6116 | 0.710 (0.690-0.727) |

All model subgroup results and A validation metrics are in reports/metrics.json. Binary sex recording is incomplete; subgroup discrimination is not evidence of fairness.

## Metric definitions and uncertainty
- **Thresholds**: Conservative 5 hourly alerts/100 hours on A validation; unchanged on B.
- **Budget**: Retrospective label-free within-cohort score ranking, SHA256 patient-hour tie-break; not a prospectively deployable threshold or tuning on B outcomes.
- **Catch**: At least one hourly alert in [inferred onset-12h, inferred onset); first-label-positive patients excluded because onset is left-censored.
- **False Alarm**: An hourly alert outside the useful pre-onset window, including repeated late/post-onset alerts.
- **Catches Per 100 Alarms**: Distinct caught patients / all hourly alerts x100; not hourly PPV.
- **Warning**: Median onset minus first useful alarm, conditional on a catch.
- **Onset**: First positive SepsisLabel hour + 6; inferred, not independently observed. First-hour positives are left-censored.
- **Ci**: 500 percentile bootstrap replicates resampling whole patients, fixed model/threshold/ranking; excludes model-training and threshold-selection uncertainty.
- **Auprc**: Average precision (step-function PR area).
- **Calibration**: Platt scaling fitted on held-out A training patients; not refitted on B.

## Limitations
Retrospective research cannot demonstrate improved patient outcomes. Missingness and test-ordering may encode local workflow; lab measurement flags can shift across hospitals. Forward-fill never uses the future, but observations can become stale. A validation participates in model selection, so its performance is optimistic. Bootstrap intervals hold the model and operating rule fixed and omit training uncertainty. Binary recorded sex and broad age groups are incomplete fairness audits.
Onset is inferred, not independently observed. First-hour-positive recordings have left-censored onset and are excluded from onset-based catch/warning denominators, but retained in hourly AUROC/AUPRC and utility. Some inferred onsets fall outside the recording. Alerts count every positive hour with no cooldown; this is an explicit workload proxy, not a validated nursing workflow. False alarms mean alarms outside the evaluable pre-onset window, including left-censored or undefined onset; they are not clinically adjudicated false positives.
qSOFA-style omits mental status. NEWS2-style uses oxygen-saturation scale 1 and omits consciousness, supplemental oxygen and scale-2 eligibility. Missing components contribute zero, potentially understating severity. These approximations are not validated clinical NEWS2/qSOFA. Official utility is threshold-dependent and distinct from the custom pre-onset catch metric.
The default replay is a deliberately selected illustrative case. The rest of the demo is randomly sampled. Demo replays are not used to estimate external performance.

## Citation and licensing
Data: Reyna MA et al. Early Prediction of Sepsis From Clinical Data: The PhysioNet/Computing in Cardiology Challenge 2019. Critical Care Medicine. 2020;48(2):210-217. DOI: [10.1097/CCM.0000000000004145](https://doi.org/10.1097/CCM.0000000000004145). [Dataset v1.0.0](https://physionet.org/content/challenge-2019/1.0.0/), CC BY 4.0. Demo patient values and derived recordings retain this attribution/license.
Official scoring source and BSD license: [physionetchallenges/evaluation-2019](https://github.com/physionetchallenges/evaluation-2019), vendored without changes in vendor/official.py.
[CDC sepsis burden](https://www.cdc.gov/sepsis/about/), [Wong et al. 2021](https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/2781307), [Adams et al. / TREWS 2022](https://www.nature.com/articles/s41591-022-01894-0).

