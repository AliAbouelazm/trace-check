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
