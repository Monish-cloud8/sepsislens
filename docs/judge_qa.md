# Likely judge questions (real numbers only, from `reports/metrics.json`)

**Is this just the PhysioNet 2019 challenge again?** No. The challenge scored a utility function. We ask how many septic patients are caught at a fixed alarm budget versus a NEWS2-style bedside score, trained on Hospital A and tested on Hospital B with thresholds frozen, and every alert is explained. We don't claim to beat challenge entries; our official utility is -0.013 vs -0.027 for NEWS2-style (both negative).

**Is 69.0% vs 67.0% a real win?** Not on its own: +2.0 pp, paired bootstrap 95% interval about -1.6 to +5.6. The clearer result is about 14% fewer outside-window alarms (27,340 vs 31,841), with realized rate 3.67 vs 4.26 per 100 h. At equal realized burden, interpolated from the curves (no interval), the model catches 71.6% vs 67.0%.

**Where does NEWS2 beat you?** At the 2 alerts/100 h target it catches 36.6% vs 34.8%, but at a realized 1.61 vs 0.82 per 100 h. At 10/100 h both are 92.9%.

**Is the demo patient typical?** No, it is a best case. In the 300-patient replay sample (25 evaluable septic): model in window for 19, NEWS2-style 16; where both alert (13), the model is earlier in 5 and NEWS2-style in 8. The app has buttons for a missed case and a NEWS2-faster case.

**Was Hospital B truly held out?** It had been evaluated before this refinement. We froze model and policy by hash and call it an external check, not a pristine holdout.

**Is onset real?** Inferred: first SepsisLabel=1 hour + 6. "False alarm" means outside the useful window, not an adjudicated error.

**Clinical use?** None. Research prototype; NEWS2/qSOFA are partial approximations.
