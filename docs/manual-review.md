# Optional local ML review

Start `python3 server.py`, open the printed loopback address, and choose **Try the synthetic ML walkthrough**. Inspect the two failed tool results, enable **Experimental ML review suggestions**, follow an action to the timeline, then export separate review notes. This handwritten example demonstrates the interface, not accuracy. It can legitimately produce no above-cutoff suggestions. All scored actions remain inspectable.

The original rules and Report v1 stay independent. Every imported or example run starts with ML off. Canonical runs without original message groups cannot use ML. The checkbox starts a disposable worker; cancel, clear, replacement, failure, or a two-second wall-clock timeout terminate it. The app does not fit, execute tools, suppress rules, or certify correctness. Scores are uncalibrated decision scores, never confidence or error probabilities.

## Frozen model and evidence

One separately authorized build reconstruction used the archived TRAIN recipe at `c51598b319cdefcad893860f1c1ccd5e82a4bbc9`: TF-IDF 20,000 unigram/bigram features, min_df 2, sublinear term frequency, logistic C=1, lbfgs, max_iter=500, random_state=42. Runtime pins were numpy 2.3.5, scikit-learn 1.8.0, scipy 1.17.0, joblib 1.5.3, threadpoolctl 3.6.0. It completed in 5.56 seconds with 264.38 MiB sampled process-group peak RSS; the single fit took 1.82 seconds and 40 iterations. No second reconstruction, search, or semantic fit followed.

The JSON payload is 1,866,714 bytes, SHA-256 `10bf769e803e38cd50aef8af86599b482e9e585fc8e59c95a711d517774ec164`. It is bundled as a static JSON data string in `web/review-model-data.js`. The worker checks the payload byte count and hash before JSON parsing. No eval, executable model format, pickle, fetch endpoint, or CSP relaxation is used. `connect-src 'none'` remains in force. Loading the local module sends no log contents.

All archived aggregate and per-task counts matched, but the original artifact was not saved, so byte identity and original per-step prediction identity cannot be established. At the fixed 0.70 cutoff, previously examined validation had 50 suggestions, 47 labeled mistakes and 3 false positives, with 878/1,390 actions supported. Relative to rules it added 21 true positives and 3 false positives, failing the zero-additional-FP gate. These are development observations, not fresh held-out accuracy. TEST remains excluded. The separately measured semantic model also failed and is not shipped into inference.

Actual Python/Node score parity covered all 878 supported validation actions, maximum absolute difference 6.66e-16 with identical decisions. A separate read-only Chromium check compared preserved predictions and feature hashes without fitting; its exact results are in `experimental/results/review-browser-parity-2026-10-06.json`. CI verifies eight synthetic actual-weight golden cases and the existing 20 feature cases, along with real worker/UI flows. No benchmark input text is committed for these checks.

## Inputs, export, and limits

An envelope is exactly `{envelope_version:1,run:<canonical run>,messages:[{role,step_ids}]}`. Preserve original slots and order: user maps one task step; assistant maps one assistant step followed by its tool calls; tool maps one result; excluded maps no steps. Every timeline step must occur exactly once. Do not invent groups from arbitrary canonical steps. The final assistant message is excluded. See [the feature contract](experimental-contract.md).

The feature includes an action and its two preceding original slots. Each content/argument field keeps its first 4,000 Unicode code points; the combined feature keeps its last 12,000. Context and tool-call text may be lost. The panel and export show truncation counts. Non-ASCII features abstain, as do features with no known vocabulary. The input cap is 2 MiB and 2,000 steps/groups; the JSON payload cap is 2 MiB. These are input/time bounds, not an operating-system browser memory guarantee.

Review notes contain the redacted run, positional results, coverage, truncation, elapsed worker time, model version/hash/source, fixed cutoff, and limitations. They do not contain the original unredacted envelope or coefficients. Excerpts show observed log context only; they are not model explanations. Redaction is incomplete and users should inspect exports before sharing.

The bundled vocabulary is source-derived and not anonymous. The source dataset card declares MIT; the source GitHub snapshot has no standalone LICENSE, and upstream clearance was not independently established. The [retained model notice](../web/review-model-NOTICE.txt) records that limitation. This work is in the existing private repository; no deployment, visibility change, or public redistribution was performed.
