# Proposed bounded calibration and optional local inference

Status: proposal awaiting review. No new fits or held-out assessments were run during the archive import. The app remains rules-only.

## Evidence and gaps

The archived experiment measured 3.71 seconds wall time and 320.56 MiB peak Python RSS, with one 1.85-second CPU fit and 20000 TF-IDF features. Those are prior environment-specific measurements, not measurements from this checkout. Test mistake F1 was 0.4133 for rules and 0.4839 for the model, but false positives increased from 59 to 75. Tau2 positive/neutral false positives increased from 5 to 30. Aggregate F1 alone is not a promotion criterion.

The raw data and fitted weights are intentionally absent. Before fitting, retrieve only the previously authorized public dataset revision, verify every recorded source hash, and use the frozen deduplicated whole-task memberships unchanged. Do not fetch or execute upstream scripts. Existing test metrics and error cases have already been examined; neither that split nor a reshuffle of its tasks is a fresh held-out assessment. No genuinely unseen whole-task dataset is currently established.

## One development-only experiment

1. Load TRAIN and validation memberships only. Make the calibration entry point reject TEST group IDs and exclude test records before vectorization or prediction. Keep the original protocol, split and results immutable.
2. Fit exactly one unchanged TF-IDF logistic baseline on TRAIN, retaining the allowlisted prefix features, final-message exclusion and fixed hyperparameters. No embeddings, GPU, hyperparameter search or test inference.
3. Compare never-flag, existing rules, the original 0.5 model threshold, and one abstaining model policy on validation. Search only thresholds 0.50, 0.60, 0.70, 0.80, 0.90 and 0.95. Scores remain uncalibrated ranking scores; threshold selection does not establish probability calibration.
4. Proposed false-positive budget: total, neutral-only and each subset's positive/neutral false-positive counts must each be no higher than the rules on the same validation records. Require at least 20 flagged validation steps to avoid accepting a nearly empty result. Among eligible thresholds choose highest mistake recall, then higher threshold on ties. If none qualify, abstain entirely and retain rules-only behavior.
5. Report precision, recall, F1, TP/FP/FN/TN, neutral versus positive false positives, subgroup support, abstention/coverage and paired task-level uncertainty. Validation selection is development evidence, not an unbiased improvement claim. If the model qualifies, evaluate the union of rules and optional model flags separately: the union can exceed either component's false-positive budget. Do not promote an untested union.

## Resource and stop budget

CPU only, one fit, maximum 60 seconds wall time and 512 MiB process RSS for fit plus validation scoring; one BLAS thread. Enforce limits using a supervised child process before fitting and record actual elapsed time and RSS. Stop on either limit, unexpected data hashes or split overlap. Zero paid APIs, hosted training or GPU. Fits must not run in GitHub Actions; the standard hosted CPU workflow runs only application and integrity tests within the owner-approved included allowance. No automatic retries or larger model if it fails.

## Optional product integration gate

Only after review and a qualifying validation result, implement opt-in local browser inference using a bounded, non-executable JSON vocabulary and coefficients artifact with recorded hashes. Require Python/browser feature and score parity fixtures, a feature-artifact size cap, and a browser latency/memory measurement before promotion. Do not load pickle/joblib from users, start an inference upload service or fetch a remote model at runtime.

Label outputs "Experimental model suggestion, development validation only" and show score/threshold as an uncalibrated decision score, never confidence or causal evidence. Default off. Preserve independent rules and their evidence; explain abstention as insufficient model support, not a clean bill of health. If the gate fails, retain the useful complete rules app and document the failure.

A fresh assessment requires genuinely unseen whole tasks with independently obtained labels, duplicate checks against all previously examined groups, and a protocol frozen before labels are inspected. Without that, every new result remains development-only. No new fit is authorized until this plan is reviewed.

## Review addendum: mandatory feature parity before fitting

The existing 0.5 threshold already fails validation budgets: total false positives 73 versus rules 61, neutral false positives 18 versus 3, and Tau2 positive/neutral false positives 31 versus 2. Do not promote it. The six predeclared threshold candidates, one TRAIN fit, 60-second/512-MiB stop limits and immutable split/source hashes remain unchanged. Every candidate must pass both standalone-model and combined rules-plus-model gates using the same total, neutral and per-subset budgets. If no candidate passes the combined gates, do not integrate model suggestions alongside the rules.

The research feature window is the current plus previous two ORIGINAL messages. The adapter expands one assistant message into an assistant timeline step plus potentially several tool-call steps. The previous two timeline steps are not equivalent. Never infer grouping from `mN` IDs, tool order or adjacency in arbitrary v1 imports.

Before fitting, implement and review a separate, strictly allowlisted adapter envelope retaining original ordered message groups and their explicit timeline-step mapping. Only this format may opt into experimental ML. Canonical v1 imports continue to work with rules, while ML explicitly abstains for lack of original-message grouping. Preserve original slots for excluded system messages because they still occupy positions in the three-message window; do not include their text in features. Reject invalid mappings, reordered/duplicate groups and unbounded content. Do not relax the v1 schema silently.

Executable pre-fit gates, in order:

1. Run `bash scripts/check.sh`: synthetic Python/Node/browser parity, strict envelope/model validation, worker preflight, cancellation, and combined-policy budget gates are now implemented. See [contract and measured proof](experimental-contract.md). No app call site invokes inference.
2. Run `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 experimental/check_sklearn.py` in the pinned research environment. This assigns synthetic weights and patches fit methods to fail. It verifies actual sklearn transform/prediction parity without training.
3. Review the explicit ASCII-only scoring restriction: Unicode features are preserved exactly but abstain during scoring. Unsupported/OOV records stay in all validation denominators. This restriction was selected before any new fit or data analysis. Canonical v1 files without original-message groups remain rules-only.
4. Review the fixed contract caps: input and model each 2 MiB, 2000 original groups/steps, 20000 vocabulary terms, 12000 feature code points, a 2000-ms interruptible browser Worker, exact finite dimensions and unrounded JSON export. Export failure does not authorize reducing the model or changing thresholds after inspecting results.
5. `experimental/bounded.py` now provides a tested Linux supervisor. Its maximum is 60 seconds wall time and 512 MiB summed process-group RSS, with one BLAS thread. It checks RSS approximately every 10 ms and kills the process group on breach; brief between-sample overshoot remains possible. Shared pages can be counted twice, making this conservative. Tests exercise time/RSS stops with harmless processes, not fits. Browser harness RSS is a separate measurement and is not the training budget.
6. After parent review only, implement the single-fit orchestration under that supervisor. Before importing or vectorizing source records, verify source hashes and immutable split membership; exclude every TEST group from feature extraction, fitting, prediction, examples and threshold selection. Do not rewrite the frozen protocol, split, metrics or code hashes. Preserve source text only in temporary local storage. Check adapter compatibility and apply declared abstentions before selection.
7. Fit one unchanged 20000-feature TF-IDF logistic configuration on TRAIN only. Evaluate validation rules, never-flag, threshold 0.5, and exactly the six predeclared candidates. Feed validation records into `experimental/policy.py:choose_threshold`, which requires validation group membership, at least 20 model flags and standalone AND combined total/neutral/per-subset FP gates. Select maximum model recall, then higher threshold on a tie. The executable selector and false-positive-union regression are implemented; the fit orchestration has deliberately not been run or added as an automatic task.
8. Record source/split/code digests, unsupported coverage, counts, precision/recall/F1, abstention, resource usage and the gate receipt as development-only evidence. Export a bounded JSON artifact only if all gates pass. Do not enable the UI merely because export succeeded; subsequent integration still needs reviewed UI labels, redacted positional links and actual-artifact parity/latency checks.

No new fits have run. The final training orchestration and any opt-in UI integration remain subject to parent review. No examined test split or reshuffle can provide a fresh held-out result.

## Driver implementation ready for review

The separate post-merge driver is now implemented. See [final driver review](calibration-driver-review.md) for source boundaries, support accounting, synthetic failure tests and the exact post-approval command. This supersedes the earlier statement that orchestration had not yet been added. It has not been executed: no source data read, new fit, threshold selection or model export has occurred. The rules-only app remains unchanged.
