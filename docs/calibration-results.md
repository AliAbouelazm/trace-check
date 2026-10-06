# One supervised calibration run: no model promotion

The reviewed command ran once at code head `c51598b319cdefcad893860f1c1ccd5e82a4bbc9`, after parent-confirmed exact-head CI success. All six predeclared thresholds failed at least one promotion gate. No model artifact was exported, no settings were changed, and no fit was repeated. Keep the practical rules-only application as the product.

The [complete immutable result](../experimental/results/calibration-2026-10-06.json) preserves source/split/code hashes, both support stages, label/subset/task-group counts, every threshold, paired task confusion counts, and the supervisor outcome. Original research files remain unchanged.

## Resource and execution record

- Supervisor: exit code 0, no stop reason; elapsed **4.129 seconds**, sampled peak process-group RSS **207964 KiB (203.1 MiB)**, against fixed 60-second/512-MiB limits.
- TF-IDF plus logistic fitting: **1.572 seconds**, one fit configuration, one thread, CPU only. No paid API, GPU or hosted training.
- Source files and frozen split/feature-extractor hashes verified. TEST records were routed out before preparation; no new TEST features, predictions, metrics or error inspection occurred.
- Artifact export and actual-trained-artifact parity were **not reached**, because no threshold qualified. Earlier synthetic/browser/sklearn parity tests are not a substitute for that unperformed actual-artifact check.

RSS is sampled approximately every 10 ms and can miss brief spikes. These measurements are environment-specific. The source download occurred before the supervised command and is not included in its runtime.

## Validation policy comparison

All rows below use all **1390 validation targets**, including unsupported records as abstentions. Rules have 76 TP, 61 FP, 308 FN and 945 TN; their 61 FP include 3 neutral and 58 positive labels. The minimum standalone model support is 20 flags. Combined-policy FP budgets are total <=61, neutral <=3, and per-subset FP no higher than rules.

| Threshold | Model flags | Model TP / FP | Combined TP / FP | Combined neutral FP | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| 0.50 | 143 | 99 / 44 | 137 / 104 | 10 | Standalone neutral/Tau2 and combined FP budgets fail |
| 0.60 | 99 | 78 / 21 | 119 / 82 | 5 | Standalone Tau2 and combined FP budgets fail |
| 0.70 | 50 | 47 / 3 | 97 / 64 | 4 | Combined total, neutral, BFCL and Tau2 budgets fail |
| 0.80 | 22 | 21 / 1 | 79 / 62 | 4 | Combined total, neutral and Tau2 budgets fail |
| 0.90 | 16 | 16 / 0 | 76 / 61 | 3 | Fewer than 20 model flags; adds no detections beyond rules |
| 0.95 | 9 | 9 / 0 | 76 / 61 | 3 | Fewer than 20 model flags; adds no detections beyond rules |

The 0.70 model has high standalone precision (0.94), but that does not satisfy the combined product policy: it adds 21 true positives and 3 false positives beyond rules. At 0.80 it adds 3 true positives and 1 false positive. The reviewed budget permits no increase in combined false positives, so neither is eligible. Raising or lowering those requirements now would be post-result retuning and was not done.

## Actual inference support

| Split | Total targets | Supported | Unsupported | Supported task groups | Unsupported task groups | Total groups |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| TRAIN | 4824 | 3075 (63.74%) | 1749 | 111 | 104 | 113 |
| Validation | 1390 | 878 (63.17%) | 512 | 36 | 37 | 38 |

Mixed-support groups appear in both group columns. TRAIN used all targets for its unchanged fit; support counts describe inference compatibility. Unsupported TRAIN targets comprise 1731 with non-ASCII features and 18 with incompatible envelopes. Validation has 508 non-ASCII and 4 incompatible-envelope targets. There were no additional zero-known-feature abstentions. Input and post-vocabulary support counts are therefore equal in this run.

| Split / label | Supported | Unsupported | Total |
| --- | ---: | ---: | ---: |
| TRAIN mistake | 892 | 642 | 1534 |
| TRAIN neutral | 151 | 157 | 308 |
| TRAIN positive | 2032 | 950 | 2982 |
| Validation mistake | 211 | 173 | 384 |
| Validation neutral | 35 | 31 | 66 |
| Validation positive | 632 | 308 | 940 |

| Split / subset | Supported | Unsupported | Total |
| --- | ---: | ---: | ---: |
| TRAIN BFCL | 1283 | 192 | 1475 |
| TRAIN GAIA | 290 | 507 | 797 |
| TRAIN HotpotQA | 183 | 175 | 358 |
| TRAIN Tau2 | 1319 | 875 | 2194 |
| Validation BFCL | 422 | 50 | 472 |
| Validation GAIA | 88 | 163 | 251 |
| Validation HotpotQA | 43 | 37 | 80 |
| Validation Tau2 | 325 | 262 | 587 |

The conservative ASCII boundary excludes ordinary English containing curly quotes or dashes as well as other languages. Support is uneven across labels and subsets. These measurements do not establish multilingual usefulness or calibrated probabilities.

## Product recommendation and empirical limits

Retain JSON import, the timeline, filtering, evidence-backed rules, redaction, examples and export. Keep the experimental model code disconnected from the UI. There is no qualifying artifact to activate or review for product integration.

This is development validation on previously examined public benchmark tasks, not fresh held-out evidence or a significance claim. Paired independent-task confusion counts are retained for rules, never-flag, and every standalone/combined policy, but confidence intervals and statistical significance remain unassessed. No claim of universal model inferiority or superiority follows. Any new experiment would need a separately reviewed protocol and, for a fresh assessment, genuinely unseen independently labeled whole tasks; it is not authorized as an automatic follow-up to this result.
