# One fixed semantic head: review-only executable protocol

**Do not execute the benchmark command below until the parent approves this exact code/protocol.** The driver is `semantic/fit.py`. No benchmark encoding or head fit was performed while preparing it. There is no automatic model search, threshold expansion, retry, cap increase, app activation or deployment.

## Inputs, partitioning and labels

`semantic/data.py` verifies the immutable split SHA-256 `7a7d222f87069b840eccab45abb3d7e35da51fc2b11e62a18d89a9a34eab7524`, exact source-file inventory and each manifest source SHA-256 before routing. It hashes bytes again while consuming them, validates 200 source groups and five attempts each, merges normalized question duplicates into 189 independent groups, and rejects duplicates crossing splits. Symlink source files are rejected. The CLI cannot supply an alternate split or hash.

The JSONL container must be parsed to inspect routing metadata, but TEST messages and labels are never inspected by target preparation, rules, tokenizer, encoder, fitter or scorer. Only question hashes are used to validate duplicate-task routing across all splits. All TEST groups remain excluded because TEST is spent. The loader returns TRAIN/validation rows only. Before any encoding, target counts must equal 4,824 TRAIN and 1,390 validation nonfinal assistant labels; class values must be exactly from `[-1, 0, 1]`.

The representation may use only the task question, current nonfinal assistant content and ordered tool function names/arguments, and previous two ORIGINAL message slots. System slots count toward that two-slot window but their text is excluded. Future messages, final answers, labels, references, outcome fields and IDs do not enter embeddings. `<answer>...</answer>` contents are replaced before character counting. The existing adapter supplies the rules baseline only; rules may inspect later tool results within the nonfinal run, as disclosed in the prior baseline protocol. Rules mapping, including last-call-ID wins, is unchanged.

## Frozen feature version

`semantic-v2-text94-tools4x40-args16head15tail-context64x190`:

1. Task: first 4,000 Unicode code points. Prefix: serialize the previous two slots with the existing role/content/call ordering and per-field 4,000-character limits, then retain the last 12,000 characters. Current content: first 4,000 characters, preceded by `assistant `.
2. Current calls are processed separately from prose. Names must fit within 128 code points without truncation; longer names make the whole action unsupported. Arguments at most 4,000 characters are unchanged; longer arguments retain the first 2,000 plus last 2,000 characters, concatenated deterministically without a new separator. A call does not lose its character allocation to another call or to prose.
3. Tokenize each field independently with the verified official tokenizer JSON, no automatic padding or truncation. Context: `[CLS] + first 64 task IDs + last 190 prefix IDs + [SEP]`. No unused task budget is reassigned.
4. With one to four current calls: `[CLS] + first 94 text IDs + call slots in original order + [SEP]`. Each call slot is its complete tokenized name (maximum eight IDs), up to 31 argument IDs, then `[SEP]`. If arguments exceed 31 IDs, retain first 16 plus last 15; otherwise retain all. Text/name/argument/call budgets do not borrow from each other. Maximum length is `1 + 94 + 4*(8+31+1) + 1 = 256`.
5. With no calls, use `[CLS] + first 254 text IDs + [SEP]`. Original role markers and all sequence/call separators use the pinned tokenizer's official IDs. Token type IDs are zero; padding has attention mask zero.
6. More than four calls, any name exceeding eight tokens, empty/unknown-only name, nonempty arguments whose retained slice is empty/unknown-only, and an empty/unknown-only no-call action cause whole-action abstention. Unsupported records are never encoded or fitted; they remain in all target denominators. Partial unknown tokens are preserved and counted. There is no ASCII filter or language-specific exception. A supported action guarantees the reserved token representation of every call, not semantic completeness or multilingual accuracy.
7. One frozen FP32 MiniLM encoder, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, CPUExecutionProvider, one intra/inter-op thread, batch at most eight streams. Masked mean-pool last hidden states and L2-normalize each 384-vector. Feature order is `[context, action]`, 768 float32 values. No scaler, encoder fitting, fine-tuning, stream averaging or second normalization.

Character counts are after answer-tag removal. Per-field character losses, prefix losses, token losses, unknown counts, call counts, and every support reason are retained without input text. The original v1 representation and measurements are archived; there will be no revision after observing benchmark results.

## Runtime, source identity and cache

Before any dataset processing, `verify_protocol` checks code hashes and fit dependency pins from `semantic/fit-protocol.json`. The ONNX runtime verifies exact local weight and nine small-file sizes/SHA-256 hashes and all direct runtime package versions. No remote code or pickle is loaded. Offline environment flags and a socket connection guard are active in the worker. The rules subprocess has no network operations and its code is hash-pinned.

The memory-only embedding cache is new for each invocation. Keys hash encoder revision, feature version and the combined feature/contract/runtime code SHA, source hashes, frozen split SHA and TRAIN/validation assignment, prepared-input SHA and token-ID SHA. Labels, outcomes and IDs are not encoder inputs or cache values. Identical text in different splits cannot share a cache entry. No persistent cache is deserialized or reused; no embeddings or raw logs are written to Git. Cache values are bounded to 32 MiB and the target ceiling to 6,214 pairs. The main float32 feature matrix is at most 19,089,408 bytes. Only supported TRAIN row indices and labels reach `fit`.

The complete dependency inventory is `semantic/requirements-fit-cpu.txt`; direct fit pins include scikit-learn 1.8.0, NumPy 2.2.6, SciPy 1.17.0, joblib 1.5.3 and threadpoolctl 3.6.0. The synthetic encoder check uses the same runtime and feature code as the proposed driver.

## Exactly one head and the unchanged gate

Fit one `LogisticRegression(C=1.0, solver='lbfgs', max_iter=500, class_weight=None, random_state=42, tol=1e-4)` on supported TRAIN pairs. No validation rows enter `fit`. All three classes must be present; any scikit-learn `ConvergenceWarning` is promoted to an exception around the sole fit call, including abnormal termination before 500 iterations. A warning or iteration limit failure aborts without a candidate. No balancing, feature selection, scaler, hyperparameter search, refit or retry.

Validation scores are mistake-class (`-1`) softmax probabilities, not calibrated confidence. Unsupported targets have `score=null` and no model flag. Compare never-flag, the existing rules and the head at exactly `.50, .60, .70, .80, .90, .95`. The existing `experimental/policy.py` is hash-pinned and reused unchanged:

- Flag only if score is greater than the threshold and more than `1e-6` away from it.
- At least 20 model flags are required.
- Both standalone model and rules-OR-model must have no greater total FP, neutral FP or per-subset FP than rules.
- Among eligible policies choose highest model recall, then highest threshold. No eligible policy means no candidate artifact.

Retain all validation targets and all frozen validation task groups, including groups with zero targets, in paired per-task confusion tables and derived precision/recall/F1. Report positive and neutral FP separately, never-flag/rules/model/combined metrics, label/subset coverage, and all unsupported targets. TRAIN/validation coverage includes all respective frozen groups, including zero-target groups and per-subset group membership. TEST group counts appear only as routing provenance, not evaluation denominators. The earlier TF-IDF result (21 extra TP, 3 extra FP at .70) remains archived and failed its combined gate; its differing representation prevents a controlled causal comparison.

For each retained target, export only source subset, frozen group, query/attempt/message positions, label, rule flag, model score, support reason and numeric coverage audit. No prompts, content, argument text, tool names, call IDs, answers or raw traces are exported. This is fully text-redacted positional evidence for authorized local inspection of the original source. It does not provide a causal explanation or expose logs to the app.

Learned JSON coefficient/intercept softmax must match scikit-learn scores within `1e-6` and all six threshold decisions exactly on supported validation vectors. Serialization is JSON, never pickle/joblib. A candidate is local and does not authorize automatic app flags; the gate is a necessary condition for later product review.

## End-to-end limits and publication

One invocation, proposed fixed caps: 2,210 seconds wall time, 2,048 MiB aggregate child process-group RSS sampled every 10 ms, 128 MiB total candidate-model files, 32 MiB report, 32 MiB embedding values. The supervisor passes only the remaining end-to-end wall budget to the worker. This covers verification, routing, preprocessing, encoding, fit, evaluation, parity, serialization and model-file copying. It kills the complete child process group on time/RSS exhaustion and cleans up on every exit or interruption.

The parent independently checks final supervisor status/time/RSS, the single-fit completion report, recomputed validation gates, exact artifact inventory, pinned model hashes, each file's size/digest and total bytes. It checks the full wall deadline before and after atomic same-filesystem publication. A failing gate produces no candidate. Resource/provenance/parity/convergence failures publish no report or model; only a small sanitized failure receipt survives. A successful quality-gate failure may publish the bounded redacted report without a candidate. No raw exception message or traceback is recorded by the worker.

The candidate contains ONNX, nine small files, JSON head, protocol/lock and retained model card/notice/Apache license text. Runtime wheels and reference safetensors are excluded. This is a model-file cap, not a whole installed-application cap. A new output directory and exclusive attempt receipt prevent accidental overwrite/retry of that attempt. Never retry a failed run under a fresh output name without explicit parent review.

## Reviewed command, deliberately not run

Install the already verified CPU dependencies in the isolated environment and check pins. The source data must already exist locally and match the immutable manifest; this driver has no downloader.

```sh
# If recreating the isolated CPU environment:
python3 -m venv .venv
.venv/bin/python -m pip install 'torch==2.6.0+cpu' --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r semantic/requirements-fit-cpu.txt
.venv/bin/python -m pip check
# ONLY after explicit parent approval of this commit and protocol:
.venv/bin/python semantic/fit.py \
  --data research/data \
  --model-dir /tmp/tracecheck-minilm-pinned \
  --output semantic/runs/semantic-v2-one-fit \
  --execute-reviewed-fit
```

Without `--execute-reviewed-fit`, the CLI exits before opening data. Tests use synthetic rows, a toy tokenizer and stub estimator/encoder. They never call the benchmark worker. No upload endpoint, browser model, paid API, GPU, deployment or automatic promotion is included. After parent review, one authorized run may supply evidence for a practical local detector; failure retains the functioning rules app and does not trigger model search.
