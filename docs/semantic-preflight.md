# Semantic synthetic preflight: measured, awaiting protocol review

The fixed official encoder passed the offline synthetic preflight on 2026-10-06. Both weight files and all nine tokenizer/config files match the recorded byte sizes and SHA-256 digests. No benchmark rows were encoded, no head was fitted, and the app still runs its existing rules with ML disabled. This is runtime feasibility evidence, not detector-quality evidence.

[Full measurements](../semantic/results/synthetic-2026-10-06.json), [source and runtime hashes](../semantic/results/synthetic-code-hashes.json), [download evidence](../semantic/access-approved-download.json), and [current status](../semantic/preflight-status.json) are committed. Large weights remain only in `/tmp/tracecheck-minilm-pinned` and are ignored by Git.

## Source and access

Model: `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. Safetensors: 90,868,376 bytes; ONNX: 90,405,214 bytes. Both match [source.json](../semantic/source.json). Downloads started only at revision-specific official resolve URLs. A redirect guard accepted HTTPS on `huggingface.co`, `cas-bridge.xethub.hf.co`, and `us.aws.cdn.hf.co` only; every observed redirect stayed within that set. Signed query strings were not recorded. No credentials, alternate routes, network changes, or log uploads were used.

User-supplied policy version: `94da5f27-122f-414b-8034-e2062aaad871~cecfgver_6ac5678c4dc8819aad9f24adfacc8ad1`. This is a supplied identifier, not an independent inspection of the saved policy. The previous blocked attempt is retained in [access-policy-recheck.json](../semantic/access-policy-recheck.json); its two-domain restriction is historical.

The pinned publisher model card declares Apache-2.0. Its verified, unmodified copy and attribution are retained under [semantic/notices](../semantic/notices/NOTICE.txt). The revision has no standalone LICENSE/NOTICE. No weights are redistributed here; any future distribution must retain attribution and the license text. The measured model has 22,713,216 parameters and 384 output dimensions.

## Actual CPU measurements

Linux x86_64, Python 3.12.14, five visible logical CPUs, one inference thread, `CPUExecutionProvider` only. This is one synthetic run on shared hardware; it does not establish production latency or language accuracy. Ordinary regression tests overlapped part of the run.

| Measurement | Result |
| --- | ---: |
| Supervisor elapsed | 9.9555 seconds |
| Model/runtime load | 2.5479 seconds |
| Sampled peak process-group RSS | 920,636 KiB (899.06 MiB) |
| Worker peak RSS | 920,456 KiB |
| Batch 8, up to 30 tokens, slowest of 3 warmed runs | 0.063934 seconds; 125.13 streams/s |
| Batch 8, 256 tokens, slowest of 3 warmed runs | 0.671418 seconds; 11.915 streams/s |
| PyTorch/ONNX normalized embedding max absolute error | 1.4529e-7 |
| Minimum cosine agreement | 0.9999998808 |
| Handcrafted head probability max absolute error | 5.5399e-9 |
| ONNX plus nine config/tokenizer files | 91,104,751 bytes (86.88 MiB) |
| Both reference and deployment model files | 181,973,127 bytes |

The 120-second/2-GiB supervisor and independent final publication gate passed unchanged. RSS is sampled every 10 ms, not a kernel-enforced instantaneous ceiling. The deployment-file figure excludes runtime packages, reference safetensors, future coefficients and notices. A deployable application bundle has not been built or measured. Including the retained model card and this repository's notice remains well below the proposed 128-MiB model-artifact cap; runtime distribution must be budgeted separately.

Twenty streams from ten synthetic cases passed shape and unit-norm checks, masked mean pooling and L2-normalization parity, and ordered `[context, action]` 768-dimensional concatenation. Handcrafted coefficients passed score and six-threshold decision parity without fitting. This does not validate a learned head. Thirty task/prefix/action tokenizations matched the official fast tokenizer exactly. The warning about raw input exceeding 512 tokens arose while auditing untruncated token IDs; every encoded stream was capped at 256.

## Unicode and truncation findings

Synthetic English punctuation, accents, decomposed accents, Arabic, Japanese, emoji, script-like text and long inputs were exercised. Japanese produced three unknown tokens in its action; the emoji case produced one. The other cases produced none. Matching tokenizer IDs is not proof of useful multilingual representations.

The long repeated-content case capped 12,600 content characters to 4,000, then removed 524 of 778 action tokens. Its appended `read_file` call retained all 34 characters before token allocation and zero of its 15 tokens afterward.

The combined stress case independently exercised all field and stream caps:

- Task: 5,000 to 4,000 characters, then 800 to 64 tokens.
- Prefix: after per-field limits, 16,037 to 12,000 characters, then 1,744 to 190 tokens.
- Action: after per-field limits, 20,054 to 12,000 characters, then 1,466 to 254 tokens.
- Four action calls: two removed entirely by the joined-action character cap; the second call partially retained; all four absent after token allocation. Each 9,000-character argument was first capped to 4,000. The 6,000-character action content was first capped to 4,000.

Per-field losses and subsequent joined-stream losses are distinct stages in the report, so they must not be mistaken for alternative totals. A future coverage report must disclose invisible calls and truncated actions. This run does not change the frozen representation to improve those outcomes.

## Reproduce synthetic-only execution

The [runtime lock](../semantic/runtime-lock.json) verifies exact versions for all seven direct packages and hashes all nine small files before encoder imports. [requirements-cpu.txt](../semantic/requirements-cpu.txt) freezes the complete installed package set; `pip check` passed. CPU torch came from its CPU package index, other packages through the existing package-manager route. No GPU packages are required. These are observed working pins, not a package security audit.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install 'torch==2.6.0+cpu' --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r semantic/requirements-cpu.txt
.venv/bin/python -m pip check
# Requires separately authorized, hash-verified local official model files.
# The output path must not already exist.
.venv/bin/python semantic/preflight.py --model-dir /tmp/tracecheck-minilm-pinned \
  --output /tmp/tracecheck-minilm-synthetic-preflight.json
```

The harness has no dataset argument, downloader, fit API, app import or server. It uses `local_files_only=True`, `trust_remote_code=False`, safetensors only, offline flags and a socket-connect guard. Do not add this optional heavy run to ordinary CI. Missing files, wrong hashes, unverified pins, dependency mismatches and resource overruns fail closed.

## Proposed next-run caps, not authorized to execute

For the previously scoped 12,428 TRAIN/validation streams, batch eight means 1,554 batches. At the slowest observed full-length batch time, encoding projects to 1,043.38 seconds. A conservative proposal is `10 * ceil((2 * 1554 * 0.671418409 + 120) / 10) = 2210 seconds` total, covering encoding at twice observed cost plus 120 seconds for load, bookkeeping and one head fit. This is an estimate; neither full-data preprocessing nor fitting was measured. A later executable driver must enforce a single 2,210-second wall deadline, 2,048-MiB sampled process-group RSS cap, and 128-MiB serialized model-artifact cap, with fail-closed final publication and no surviving child processes. No budget increase or automatic retry after a cap failure.

The memory proposal is 2.28 times the measured combined PyTorch/ONNX preflight peak. A future encoding runtime should load ONNX only, batch eight, and store at most 6,214 ordered float32 pairs (19,089,408 bytes); that design still needs executable review. A later driver's scikit-learn dependencies and score/decision parity must also be pinned and checked. It does not yet exist, and there is deliberately no runnable benchmark/fit command in this change. Parent review of the caps and final executable protocol is required before any benchmark encoding or fit.

## Frozen representation and head proposal


`semantic/contract.py` fixes this representation before seeing new dataset results:

- Use only the allowed task, current nonfinal assistant message with its ordered tool names/arguments, and previous two ORIGINAL message slots. Preserve system slots when counting the window but exclude their text. Exclude future messages, final assistant targets, labels, references and final answers. Strip answer-tag contents. Explicit original-message mappings remain required for app imports.
- Serialize current message/calls in source order. Cap each content/argument to 4000 code points, task to 4000, joined action to its first 12000 and previous-message context to its last 12000 before tokenization. These truncations must be counted in future coverage reporting.
- Context stream: first 64 task WordPieces followed by the last 190 prefix WordPieces, with CLS/SEP. Action stream: first 254 current-action WordPieces, with CLS/SEP. Each stream is at most 256 tokens. Underfilled task space is not reassigned to prefix. Unicode is passed to the official tokenizer; there is no ASCII gate or substituted tokenizer.
- Encode context and action independently with the single frozen FP32 encoder, normalize each 384-vector, and concatenate in the fixed order `[context, action]` to 768 dimensions. Do not average the streams, fine-tune the encoder or normalize the concatenation again.
- After preflight and protocol approval, fit exactly one supervised logistic head on TRAIN: C=1, lbfgs, maximum 500 iterations, default class weights, seed 42, classes [-1,0,1]. No scaler fit, model sweep, prompts search, embeddings similarity threshold or encoder tuning. A pretrained embedding alone is not a trained error detector.

The existing 189 task groups, whole-task memberships and source hashes remain immutable. TEST is excluded before feature construction or encoding. Compare never-flag, rules, and the one head with the same six predeclared score thresholds and unchanged standalone/combined FP gates. Preserve unsupported targets in denominators and report actual coverage, Unicode unknown-token counts, truncation, labels, subsets and paired task counts. No adjustment after results. The earlier TF-IDF 0.70 result added 21 TP and 3 FP, failed the agreed combined gate, and is not evidence that all models are useless.

## Product boundary and validation

The browser app remains functional with rules and never-flag baselines. This change adds no UI upload endpoint, semantic model activation or outbound app requests. Prefer a local CPU ONNX backend for a later practical detector, but any opt-in transfer of logs across loopback first needs interface review: loopback binding, origin/CSRF protection, size limits, cancellation, no request logging, memory-only processing and no outbound network. No paid service, GPU, API or deployment was used.

Validation: 30 Python tests and 20 JavaScript tests passed, including provenance rejection and final-publication ceiling tests. Both browser suites passed using an explicit `CHROMIUM_PATH=/usr/bin/chromium` override, Chromium 151.0.7922.173 and Playwright 1.62.0. The default bundled Playwright binary was absent; system-browser success is not identical to CI browser parity. Parent CI and merge remain pending. Browser tests used existing synthetic fixtures, not benchmark encoding or detector fitting.
