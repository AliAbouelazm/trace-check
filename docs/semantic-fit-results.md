# Semantic v2 one-fit result: no candidate passed the gate

The single approved run completed successfully, but none of the six frozen validation thresholds passed the existing quality gate. **No candidate model was exported or activated.** There was no retry, refit, threshold expansion, gate change or TEST encoding/scoring. The rules app remains functional.

The executed commit was `b19b736937ea65bafa1507718ecd6b64a2c9554a`, after successful CI run `37536721520`. Protocol SHA-256: `ec179fd1965ff4f3af73dc7bef55e788945e18519fee40add31e7363384b9c84`. The exact driver and protocol were not changed during or after the run. The four source JSONL files were absent locally, so they were restored from the previously frozen upstream commit `0a42606b178a8c69d40c5765dc05c342f921e578`; all four frozen hashes matched. No upstream code was executed. Source restoration preceded the supervised runtime.

[Full summary, paired task metrics, coverage, provenance and invocation receipt](../semantic/results/one-fit-v2-2026-10-06.json) are committed. The [lossless compressed original report](../semantic/results/one-fit-v2-2026-10-06-full.json.gz) includes all 4,824 TRAIN and 1,390 validation text-redacted positional records. Its uncompressed SHA-256 is `d28a7af9f3c41727ade41587bc93af4087de1265eae6a01ff04ea081e1c58e68`. Every evidence record was checked for the allowed structural strings and numeric audits; none contains source content, tool names, argument text, answers or call IDs. Raw data, model weights and private staging/output directories are ignored by Git.

## Actual runtime and parity

| Measurement | Result |
| --- | ---: |
| End-to-end time through final report preparation | 638.611 seconds |
| Supervisor elapsed | 638.457 seconds |
| Encoder/cache phase | 629.579 seconds |
| Sole logistic head fit | 1.107 seconds |
| Sampled peak worker process-group RSS | 561,424 KiB (548.266 MiB) |
| Actual encoder stream calls, including duplicate batch misses | 10,384 |
| Average actual streams per encoder/cache-phase second | 16.494 |
| Supported target representations, including cache hits | 6,081 |
| Memory-only cache entries / hits / bytes | 5,175 / 889 / 15,897,600 |
| JSON round-trip learned-head score maximum error | 0.0 |
| Learned-head decisions at all six thresholds | Exact agreement |
| Selected threshold / exported model files | None / none |

The fixed 2,210-second and 2-GiB gates passed with worker exit zero and no supervisor stop. RSS sampling is every 10 ms and can miss brief spikes. The final report publication gate passed. Because the quality gate failed, the 128-MiB candidate-artifact ceiling was not exercised on a learned artifact; there is no learned bundle size to report. Coefficients were not retained or exported by the reviewed driver.

Exactly one head fit completed. Under the frozen code, completion establishes that no `ConvergenceWarning` occurred and `n_iter_` remained below 500. The driver did not serialize its exact iteration count; it is unrecorded. There was no rescue fit to recover it. The successful parity calculation used the learned coefficients after a JSON round trip, before applying the unchanged policy gates.

## All six validation policies

All counts use **1,390 validation targets across all 38 frozen validation task groups**, including unsupported targets. There are 384 negative, 66 neutral and 940 positive targets. Rules alone flagged 137 targets: 76 TP and 61 FP (3 neutral, 58 positive), with recall 19.79% and precision 55.47%. Never-flag has zero TP/FP and 384 FN. TEST remains excluded.

| Threshold | Model TP | Model FP | Model flags | Combined TP | Combined FP | Extra TP vs rules | Extra FP vs rules | Eligible |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 0.50 | 183 | 139 | 322 | 213 | 198 | 137 | 137 | No |
| 0.60 | 115 | 96 | 211 | 154 | 156 | 78 | 95 | No |
| 0.70 | 62 | 60 | 122 | 107 | 121 | 31 | 60 | No |
| 0.80 | 34 | 32 | 66 | 88 | 93 | 12 | 32 | No |
| 0.90 | 17 | 15 | 32 | 80 | 76 | 4 | 15 | No |
| 0.95 | 4 | 2 | 6 | 76 | 63 | 0 | 2 | No |

Every combined policy adds false positives, violating the zero-additional-FP requirement. At 0.95, all four model true positives were already covered by rules, two new false positives remain, and the model also fails the minimum 20-flag requirement. No threshold was selected. Per-subset and neutral/positive FP counts, per-task confusion tables and per-task precision/recall/F1 for all policies are retained in the summary, not just for a favored threshold.

At 0.50, standalone recall rises to 47.66% and F1 to 0.518, but 139 standalone FP and 198 combined FP fail the agreed precision-oriented deployment condition. This is a measured tradeoff, not evidence of a safe automatic detector. The archived TF-IDF 0.70 policy added 21 TP and 3 FP and also failed. Its differing input/support contract prevents interpreting the comparison as a controlled encoder-only effect. No further model search follows this result automatically.

## Coverage and truncation

| Split | Task groups | All targets | Supported | Unsupported | Any character/token truncation |
| --- | ---: | ---: | ---: | ---: | ---: |
| TRAIN | 113 | 4,824 | 4,725 | 99 | 4,566 |
| Validation | 38 | 1,390 | 1,356 | 34 | 1,165 |

TRAIN abstentions: 93 names exceeding eight tokens, two names exceeding 128 characters, two actions with more than four calls, and two empty/unknown-only no-call actions. Validation abstentions: 33 names exceeding eight tokens and one name exceeding 128 characters. All 34 validation abstentions remain in the denominators: six negative and 28 positive targets; no neutral targets were excluded from scoring support. Supported coverage is 97.95% of TRAIN and 97.55% of validation targets.

Validation has 1,165 truncated targets (83.81%) across any counted stage, and 2,694 unknown tokens before token allocation in the character-bounded fields. These totals include repeated context and fields within targets; they are not counts of unique unknown words or failed semantic predictions. The original per-target numeric audits preserve the separate character and token stages. The v2 allocation guarantees the retained tokenized names and head/tail slices for supported calls, not full argument semantics or multilingual quality.

All 189 independent source task groups remain frozen: 113 TRAIN, 38 validation, 38 excluded TEST. The code records all validation groups for each policy and retains label/subset coverage. No evaluation denominator was reduced to make the quality gate pass.

## Result preservation and next boundary

The external observer preserved numeric coverage and the unpublished staged report while the approved process ran; the published report with final resource accounting is authoritative. The exclusive attempt receipt records completion and `artifact_ready=false`. The only published run output is `report.json`; no candidate directory exists. Raw worker logs were not uploaded or committed.

Parent review of these actual quality and product tradeoffs is the next step. This result does not authorize ML activation, exporting a failed model, changing the gate, additional fitting, paid APIs or deployment. The existing rules workflow remains available to users.

Local result validation passed: 43 Python tests, 20 JavaScript tests, both browser suites, unchanged approved code/package pins, lossless archive hash verification, and exact policy recomputation from saved scores without model execution. Browser suites used explicit system Chromium 151.0.7922.173 and Playwright 1.62.0. Exact result-commit CI remains a separate remote check on PR #5.
