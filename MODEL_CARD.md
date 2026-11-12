# SepsisLens model card
**Research prototype. NOT FOR CLINICAL USE.** Retrospective evaluation and hackathon education only.

## Intended use and exclusions
Research into cross-hospital warning, workload and explainability. No prospective diagnosis, triage, treatment decisions or live monitoring. Data are historical deidentified ICU recordings from PhysioNet/CinC Challenge 2019.

## Development and selection
Selected candidate: original. Shared cooldown: 12 hours. All fitting, feature trials, calibration, model selection, cooldown selection and thresholds use Hospital A. Stacker training and assessment use different A-validation patients. No B threshold fitting or score quantiles.
Original models use patient-disjoint A training/calibration/validation splits. Longer windows and early targets are retained only if selected; failed experiments remain documented.
## Inferred onset
First SepsisLabel=1 recording hour + 6. Labels are shifted six hours early. Onset is inferred, not independently observed. First-hour-positive records are left-censored; 223 B recordings are excluded from onset-based catch denominators while remaining in hourly metrics and official utility.

## External results and operating protocols
| Version | Method | AUROC | AUPRC | Official utility | Caught at 2 (%) | At 5 (%) | At 10 (%) |
|---|---|---|---|---|---|---|---|
| Before: legacy B ranking | vitals_labs | 0.726 | 0.0448 | 0.0583 | 23.6 | 39.3 | 54.2 |
| Before: legacy B ranking | NEWS2 | 0.643 | 0.0271 | 0.0436 | 25.8 | 42.0 | 59.4 |
| Before: legacy B ranking | qSOFA | 0.578 | 0.0182 | 0.0142 | 20.6 | 39.5 | 60.2 |
| After: A-locked, shared cooldown | refined | 0.726 | 0.0448 | -0.0130 | 34.8 | 69.0 | 92.9 |
| After: A-locked, shared cooldown | NEWS2 | 0.643 | 0.0271 | -0.0268 | 36.6 | 67.0 | 92.9 |
| After: A-locked, shared cooldown | qSOFA | 0.578 | 0.0182 | -0.0349 | 26.2 | 54.4 | 92.9 |

Legacy before and A-locked after are different workload protocols. A-consistent comparison:
| Version | Method | AUROC | AUPRC | Official utility | Caught at 2 (%) | At 5 (%) | At 10 (%) |
|---|---|---|---|---|---|---|---|
| Before: A-locked, no cooldown | vitals_labs | 0.726 | 0.0448 | 0.0540 | 6.5 | 15.6 | 29.9 |
| Before: A-locked, no cooldown | NEWS2 | 0.643 | 0.0271 | 0.0488 | 21.2 | 38.5 | 54.0 |
| Before: A-locked, no cooldown | qSOFA | 0.578 | 0.0182 | 0.0110 | 16.8 | 27.9 | 52.6 |
| After: A-locked, shared cooldown | refined | 0.726 | 0.0448 | -0.0130 | 34.8 | 69.0 | 92.9 |
| After: A-locked, shared cooldown | NEWS2 | 0.643 | 0.0271 | -0.0268 | 36.6 | 67.0 | 92.9 |
| After: A-locked, shared cooldown | qSOFA | 0.578 | 0.0182 | -0.0349 | 26.2 | 54.4 | 92.9 |

| Method | A target | Actual B alarms/100h | Caught (%) | Catches/100 alarms | Median warning h |
|---|---|---|---|---|---|
| refined | 2 | 0.82 | 34.8 | 5.12 | 5.0 |
| refined | 5 | 3.67 | 69.0 | 2.27 | 7.0 |
| refined | 10 | 8.88 | 92.9 | 1.26 | 7.0 |
| NEWS2 | 2 | 1.61 | 36.6 | 2.74 | 6.0 |
| NEWS2 | 5 | 4.26 | 67.0 | 1.90 | 6.0 |
| NEWS2 | 10 | 8.88 | 92.9 | 1.26 | 7.0 |
| qSOFA | 2 | 1.44 | 26.2 | 2.19 | 6.0 |
| qSOFA | 5 | 4.31 | 54.4 | 1.52 | 6.0 |
| qSOFA | 10 | 8.88 | 92.9 | 1.26 | 7.0 |

## A-only experiment outcomes
| Candidate | A caught at 2 (%) | At 5 (%) | At 10 (%) | Retained |
|---|---|---|---|---|
| original | 56.5 | 81.3 | 93.8 | yes |
| early6_12 | 25.9 | 74.6 | 93.8 | no |
| early6_12_long | 23.3 | 77.7 | 93.8 | no |
| early6_12_smooth | 18.1 | 76.2 | 93.8 | no |
| preonset12_long | 52.8 | 79.3 | 93.8 | no |
| preonset12_flexible | 52.8 | 80.8 | 93.8 | no |
| hourly_long | 45.6 | 79.3 | 93.8 | no |
| original_stack | 53.4 | 83.4 | 93.8 | no |
| early6_12_long_stack | 42.0 | 76.7 | 93.8 | no |
| preonset12_long_stack | 50.3 | 81.9 | 93.8 | no |
| hourly_long_stack | 44.6 | 81.3 | 93.8 | no |

## Subgroup audit for the selected model
| Group | Patients | Positive hours | AUROC (95% CI) |
|---|---|---|---|
| Age <50 | 4818 | 2605 | 0.711 (0.682 - 0.739) |
| Age 50-64 | 6278 | 3301 | 0.727 (0.707 - 0.748) |
| Age 65-79 | 6582 | 3661 | 0.731 (0.712 - 0.752) |
| Age 80+ | 2322 | 1213 | 0.741 (0.704 - 0.776) |
| Female (0) | 9268 | 4664 | 0.746 (0.727 - 0.764) |
| Male (1) | 10732 | 6116 | 0.710 (0.690 - 0.727) |

## Definitions and uncertainty
- **Thresholds**: For each target budget and cooldown, fit a label-free threshold grid on A validation only; apply the saved rule unchanged to B. Actual B alert rates may differ. No B quantiles or B threshold search.
- **Budget**: Budget slider specifies an A-validation capacity target, not an exact external B alarm rate. Actual B rates are shown; compare methods using both catches and actual burden.
- **Cooldown**: An alert at hour t suppresses the next N hours for that patient. Earliest repeat is t+N+1. Same selected N applies to every method. No future data is used.
- **Catch**: At least one emitted alert in [inferred onset-12h, inferred onset); first-hour-positive cases excluded from onset metrics.
- **False Alarm**: An emitted alert outside the evaluable useful pre-onset window, including undefined/left-censored onset. Research workload proxy, not clinically adjudicated false positives.
- **Catches Per 100 Alarms**: Distinct caught patients / all emitted alarms x100.
- **Warning**: Median onset minus first useful emitted alert, conditional on a catch.
- **Onset**: First SepsisLabel=1 recording hour + 6. Labels were shifted six hours early. Inferred, not independently observed; first-hour-positive cases are left-censored.
- **Ci**: 500 percentile bootstrap resamples of whole patients; frozen model, A-thresholds and causal cooldown sequences. Excludes model-selection/training uncertainty.
- **Utility**: Unmodified official PhysioNet 2019 normalized utility applied to emitted sparse alerts; this score penalizes suppressed hourly positives and is not optimized for episodic alert workflows.
- **Auprc**: Average precision against the original hourly challenge labels, even for models trained on pre-onset targets.
- **Calibration**: Base models use A-only Platt scaling for their training target. A stacked policy score is not a calibrated probability of the challenge label; reliability plots audit that mismatch.
## Limitations
This is retrospective methodological research, not evidence of clinical benefit. **Not for clinical use.** Missingness/test ordering and carried-forward measurements can reflect local workflow. First-hour-positive recordings have left-censored onset: they remain in hourly discrimination/utility but are excluded from onset-based catches and warning-time denominators. Some inferred onsets fall beyond the recording.
The original B evaluation has already been seen. This refinement is A-only development followed by another external check on the same B cohort, not a new untouched confirmatory study. Do not claim B is a pristine final holdout for future iterations. No B threshold quantiles or B model selection are used in this run.
A validation is used for development, so its performance is optimistic. Stacker fitting uses a separate patient slice from candidate assessment. Bootstrap intervals freeze the selected model, thresholds and alert sequences; they omit training/selection uncertainty.
Cooldown lowers repeated burden but also limits maximum attainable alarm rate. A target may be unattainable; B rates can drift in either direction. Read actual B rates beside catches. The official hourly utility penalizes suppressed positive hours and is not an episodic-alert utility. It is reported without changing the reference scoring logic.
Outside-window alarms are not adjudicated clinical false positives. They include records with undefined/left-censored onset. NEWS2-style omits consciousness, supplemental oxygen and scale-2 eligibility; qSOFA-style omits mental status. Missing components contribute zero. These partial scores are not validated clinical NEWS2/qSOFA.
Binary recorded sex and age bands are incomplete fairness audits. The default replay is automatically chosen to illustrate an early model alert; it is deliberately selected, not representative performance evidence.

## Explanation contract
Cached SHAP explains the selected base tree's raw log-odds. If a stacker is selected, its exact additive linear contributions are separately displayed; base-tree SHAP alone does not explain the final ensemble. Contributions are not causal effects.
## Licensing and attribution
Dataset: Reyna MA et al. Early Prediction of Sepsis From Clinical Data: The PhysioNet/Computing in Cardiology Challenge 2019. Critical Care Medicine. 2020;48(2):210-217. [DOI](https://doi.org/10.1097/CCM.0000000000004145). [PhysioNet v1.0.0](https://physionet.org/content/challenge-2019/1.0.0/), CC BY 4.0. Demo patient values/derived records retain this attribution.
The unmodified [official PhysioNet 2019 evaluator](https://github.com/physionetchallenges/evaluation-2019) is in vendor/official.py with its BSD license. Project code uses MIT; data licensing remains separate.

