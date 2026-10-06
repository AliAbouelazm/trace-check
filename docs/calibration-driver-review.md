# Final calibration driver review

This review document preceded execution and was approved by the parent. The [single authorized run](calibration-results.md) has now completed with no qualifying threshold or exported model. The production rules app remains unchanged. The command below records the reviewed invocation; repeating it requires new authorization.

## Source for review

- `experimental/calibrate.py`: immutable data routing, preparation, support accounting, exactly one training operation, validation selection, actual-artifact parity and supervised publication.
- `experimental/calibration_bridge.mjs`: exact browser feature hashes, unchanged product-rule target mapping, and artifact-score checks through the same browser module.
- `tests/test_calibration_driver.py`: synthetic TEST poison records, hash/inventory/group guards, Unicode/compatibility abstention, parity failures and publication failure gates. No fitting or sklearn import occurs in these tests.

The driver branch is based on merged main `6075634f8e821766e14ed5ffd577b69534f80332`. The frozen split digest is `7a7d222f87069b840eccab45abb3d7e35da51fc2b11e62a18d89a9a34eab7524`; the untouched feature extractor digest is checked separately. No source-hash, split or threshold override is exposed by the public CLI.

## Data boundary

All four source files must match the frozen hashes and exact file inventory before routing. The consumed bytes are hashed again while routing, so a file changed after initial verification fails before features. Routing audits 200 original task IDs with five distinct attempts each, merges exact normalized-question duplicates into 189 independent groups, and rejects any duplicate group spanning splits. This checks grouping integrity; it does not reshuffle the frozen split.

TEST records are discarded immediately after routing metadata. JSON must be parsed to route each line, and normalized question hashes are used only for independent-group identity checks. TEST labels/messages are never inspected, adapted, featurized, scored or included in reports. Synthetic TEST rows deliberately have unusable messages and labels and still pass routing tests. The preparation function independently refuses a TEST-tagged record before touching its content.

Only the 4824 TRAIN and 1390 validation nonfinal targets proceed. Canonical/group-envelope compatibility is checked using the actual browser parser, including full completed-run limits. Every compatible feature is hashed in both Python and the browser implementation. A mismatch stops before fitting.

## Abstention and honest coverage

Compatibility failures, any non-ASCII feature (including English curly quotes and dashes), and zero-known-feature vectors abstain at inference. Unsupported targets are never dropped from denominators. All TRAIN targets remain in the single unchanged training fit; reported support describes where the resulting local inference contract is usable, not a filtered training corpus. Unsupported validation records are not passed to classifier prediction.

The gate receipt preserves paired TP/FP/FN/TN counts for every independent validation task for rules, never-flag, and each of the six standalone/combined threshold policies. Every policy uses the same task keys and retains abstentions as negative predictions, so task-level paired resampling can be computed later without refitting or reselecting thresholds. Tests reconcile every per-task count to the aggregate. Confidence intervals and statistical significance remain unassessed; no significance claim is authorized.

Reports distinguish input support (before fitting) and model support (after vocabulary/OOV checks). Both contain actual TRAIN/validation counts of supported/unsupported steps, independent task groups, reasons, labels, subsets and label-by-subset counts. A task with mixed support appears in both task-group support counts; these group counts are not disjoint. No coverage is assumed in advance. No vocabulary, thresholds, text normalization, cap or support restriction may be relaxed after seeing results.

The rules comparison retains the frozen completed-nonfinal-run target mapping, including rules on runs incompatible with UI import. Those records remain in the evaluation denominator and are explicitly identified in support counts. This is development evidence on the previously examined custom validation split, not a new held-out assessment.

## Fit and promotion boundaries

The public command launches a private child under the existing 60-second/512-MiB process-group RSS supervisor, including data verification, preparation, imports, the fit, validation scoring and actual-artifact parity. One-thread BLAS settings are enforced. Polling allows brief between-sample overshoot; publication separately rejects reported elapsed time/RSS above the limits even if the child exits successfully.

The child uses the pinned sklearn/numpy versions, one fixed TF-IDF fit and one logistic fit. It does not perform cross-validation, retries, model search or test inference. Selection uses exactly six frozen thresholds through `choose_threshold`, with minimum 20 model flags and standalone plus combined rules/model total, neutral and per-subset false-positive budgets. Unsupported/OOV rows have null scores throughout selection.

A qualifying model must satisfy the unrounded <=2 MiB JSON contract and actual-weight Python/browser score tolerance of 1e-6 with identical threshold decisions. Otherwise no model is exported. No cap changes, coefficient rounding or refits are attempted. Candidate artifacts live only in a private temporary staging directory. Only supervisor success, a completed report, an eligible threshold, expected candidate digest and byte limit permit copying `model.json` into the final output directory. Timeout, RSS stop, nonzero exit, missing report, denied gate or corrupted candidate cannot publish a model. Existing output directories cannot be overwritten. Input support diagnostics may be retained on failure; no raw logs or feature strings are written to reports.

Publishing this local file is not product promotion: the UI still has no ML call site. Any subsequent opt-in UI work requires review of the report, labels, actual-artifact browser latency and redacted positional links. Failed gates leave the useful rules app intact.

## Commands

Review checks, safe now:

```sh
bash scripts/check.sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 experimental/check_sklearn.py
```

After explicit parent approval only, using a verified local copy of the previously authorized public source revision and the pinned research environment:

```sh
python3 experimental/calibrate.py \
  --execute-reviewed-fit \
  --data /tmp/AgentProcessBench/data/AgentProcessBench \
  --output /tmp/tracecheck-calibration-reviewed
```

This command was executed exactly once after parent-confirmed CI success on `c51598b319cdefcad893860f1c1ccd5e82a4bbc9`. Its existing output cannot be overwritten. Do not rerun it or call the internal worker mode directly. Do not download source data or invoke the fit from CI. Ordinary CI runs only synthetic driver tests and the existing application/parity checks. Remote checks on this results commit and any merge remain parent responsibilities.
