# One semantic detector proposal: preflight blocked

No benchmark encoding or head fit has occurred. The environment's HTTPS proxy returned **403 Forbidden** for Hugging Face access. Transfer attempts stopped; no credentials, alternate download route, model mirror or proxy bypass was used. Official documentation remained readable through the web research tool. The [status record](../semantic/preflight-status.json) keeps unavailable measurements null.

## Verified source metadata

The official [model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) declares Apache-2.0, about 22.7 million parameters, 384 output dimensions and a 256-wordpiece sentence limit. Freeze revision [1110a243fdf4706b3f48f1d95db1a4f5529b4d41](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/commit/1110a243fdf4706b3f48f1d95db1a4f5529b4d41). This is the publisher's license declaration, not an independent clearance of all pretraining sources.

Official file metadata and pointer records identify safetensors as 90868376 bytes and FP32 ONNX as 90405214 bytes, with SHA-256 values in [source.json](../semantic/source.json). Both hashes also appear on the revision-specific [safetensors](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/blob/1110a243fdf4706b3f48f1d95db1a4f5529b4d41/model.safetensors) and [ONNX](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/blob/1110a243fdf4706b3f48f1d95db1a4f5529b4d41/onnx/model.onnx) pages. Local bytes have not been acquired or verified. Reference plus deployment weights alone total 181273590 bytes; do not download the entire repository or its pickle variant.

The publisher's [efficiency documentation](https://sbert.net/docs/sentence_transformer/usage/efficiency.html) explains that standalone ONNX needs pooling and normalization outside the Transformer graph. The proposed runtime explicitly uses attention-masked mean pooling and L2 normalization, then CPUExecutionProvider only. It does not rely on an ONNX token output already being a sentence embedding.

## Frozen representation and head proposal

`semantic/contract.py` fixes this representation before seeing new dataset results:

- Use only the allowed task, current nonfinal assistant message with its ordered tool names/arguments, and previous two ORIGINAL message slots. Preserve system slots when counting the window but exclude their text. Exclude future messages, final assistant targets, labels, references and final answers. Strip answer-tag contents. Explicit original-message mappings remain required for app imports.
- Serialize current message/calls in source order. Cap each content/argument to 4000 code points, task to 4000, joined action to its first 12000 and previous-message context to its last 12000 before tokenization. These truncations must be counted in future coverage reporting.
- Context stream: first 64 task WordPieces followed by the last 190 prefix WordPieces, with CLS/SEP. Action stream: first 254 current-action WordPieces, with CLS/SEP. Each stream is at most 256 tokens. Underfilled task space is not reassigned to prefix. Unicode is passed to the official tokenizer; there is no ASCII gate or substituted tokenizer.
- Encode context and action independently with the single frozen FP32 encoder, normalize each 384-vector, and concatenate in the fixed order `[context, action]` to 768 dimensions. Do not average the streams, fine-tune the encoder or normalize the concatenation again.
- After preflight and protocol approval, fit exactly one supervised logistic head on TRAIN: C=1, lbfgs, maximum 500 iterations, default class weights, seed 42, classes [-1,0,1]. No scaler fit, model sweep, prompts search, embeddings similarity threshold or encoder tuning. A pretrained embedding alone is not a trained error detector.

The existing whole-task memberships/source hashes remain immutable. TEST is excluded before feature construction or encoding. Compare never-flag, rules, and the one head with the same six predeclared score thresholds and unchanged standalone/combined FP gates. Preserve unsupported targets in denominators and report actual coverage, Unicode unknown-token counts, truncation, labels, subsets and paired task counts. No adjustment after results. The earlier TF-IDF 0.70 result added 21 TP and 3 FP, failed the agreed combined gate, and is not evidence that all models are useless.

## Executable synthetic preflight scaffold

`semantic/preflight.py` accepts only an explicit local model directory and output path. There is no dataset argument, downloader, fitting API, server or app import. It verifies both weight sizes/hashes, checks required tokenizer/config files, disables network use during model loading, uses safetensors and `trust_remote_code=False`, and forces CPU/one-thread execution.

It is prepared to compare official fast-tokenizer IDs with the local tokenizer JSON, compare FP32 PyTorch/reference mean-pooling against standalone ONNX pooling/normalization on synthetic English punctuation, accents, decomposed Unicode, Arabic, Japanese, emoji and long inputs, and record unknown tokens, shape/norm checks, numerical agreement, load latency, three warmed fixed-batch CPU timings, dependency versions and peak RSS. Required embedding agreement is max absolute error <=1e-4 and cosine >=0.99999. Handcrafted 768-dimensional coefficients also check local/reference softmax agreement to 1e-6 without fitting. Subsequent learned-head score/decision parity would still be required separately.

Seven synthetic standard-library tests have run. The actual encoder harness has **not** run, its third-party dependencies are not installed here, and it is not claimed to be validated. Full small-file provenance/digests and dependency pins must be recorded with the approved local bundle before measuring. Do not enable this optional heavy preflight in ordinary CI.

Safe now:

```sh
python3 -m unittest discover -s tests -p 'test_semantic_contract.py'
```

After approved local files and verified CPU dependency pins are available, the intended synthetic-only invocation is:

```sh
python3 semantic/preflight.py --model-dir /tmp/tracecheck-minilm-pinned \
  --output /tmp/tracecheck-minilm-synthetic-preflight.json
```

This command is a scaffold pending the missing resources and verified runtime lock, not authorization to encode benchmark records.

## Resource and product gate

The old 60-second/512-MiB/2-MiB TF-IDF caps are not asserted to fit this encoder. A deployment bundle will already require roughly 91 MB for ONNX plus tokenizer/configs, excluding the CPU runtime. A tentative artifact ceiling of 128 MiB is metadata-based, not yet an approved or measured final cap. Reference weights and PyTorch are preflight-only and should not be part of a future deployable bundle.

No honest throughput-based time limit or measured memory cap can be finalized while transfer is blocked. **Preflight-only** ceiling: 120 seconds and 2 GiB process-group RSS, enforced on the normal command by the synthetic-preflight process-group supervisor. After synthetic measurements, derive one conservative TRAIN/validation encoding deadline from worst fixed-batch throughput for 12428 streams plus startup/head fitting, and set memory/artifact limits with measured headroom. Present the concrete values for review before the one fit. Do not treat the provisional preflight ceiling as a fit budget or loosen an approved fit budget after results.

Prefer a local CPU Python/ONNX backend if browser packaging is too costly. This would change the current tab-only privacy boundary: explicit opt-in logs would cross loopback into a local process. Before any UI connection, review strict loopback binding, origin/CSRF protection, request-size limits, cancellation, memory-only processing, disabled request logging, no retention and no outbound network. The current app server has no upload endpoint and CSP blocks fetch; neither has been changed here. Without an approved interface, use an offline CLI preflight only.

Next required input is an approved local copy of the pinned official model files (plus recorded tokenizer/config provenance) or authorized environment access to obtain them. After synthetic measurement and plan review, one supervised TRAIN/validation head fit may be considered. If it later fails, retain the app and evidence; do not launch an automatic model-search loop or activate a failed artifact.

## Read-only access diagnosis

The only execution-environment Hugging Face request was a GET to `https://huggingface.co/api/models/sentence-transformers/all-MiniLM-L6-v2?blobs=true`. No weight-download request was made. Both uppercase/lowercase HTTP(S) proxy variables point to `http://proxy:8080`, without embedded credentials; Hugging Face has no NO_PROXY entry. The retained error is `Tunnel connection failed: 403 Forbidden` from Python's HTTP CONNECT handling for `huggingface.co:443`.

The original process did not preserve headers or read the error body. One subsequently authorized read-only CONNECT status probe through the same proxy returned `403 Forbidden`, `server: envoy`, `content-type: text/plain`, `content-length: 16`, `connection: close`, `date: Tue, 06 Oct 2026 21:00:19 GMT`, and body `Domain forbidden`. It sent no TLS handshake or origin GET and was closed after capturing the refusal. Full redacted evidence is in [access-diagnosis.json](../semantic/access-diagnosis.json).

This establishes an environment proxy domain-access restriction, not a Hugging Face application failure. The precise saved allowlist rule remains unknown. No origin GET retry, weight request, network-setting change, credential creation or alternative download route occurred. Parent review and specific authorization are required before changing access.

## Offline gates now implemented

The normal preflight command starts a separate process group under a 120-second wall-time and 2-GiB aggregate RSS supervisor. RSS is sampled every 10 ms, so this is a sampled kill threshold, not a kernel-enforced instantaneous memory ceiling. Success, failure, timeout and interruption clean up the process group. Only a successful worker result can become the requested report. Ordinary tests exercise harmless success, time/memory stops, ceiling-increase rejection and a failed normal CLI invocation; they do not import or execute an encoder.

`semantic/runtime-lock.json` deliberately remains unverified with null small-file digests and dependency versions. `semantic/provenance.py` rejects that state before encoder imports. It requires exact official revision URLs, SHA-256 and sizes for every listed tokenizer/config file, and exact installed dependency versions. Missing pins cannot silently fall back to installed packages or network access. Completing and verifying these pins remains blocked; no versions or hashes have been invented.

The synthetic harness now records per-field character counts after answer-tag removal, aggregate task/prefix/action character loss, per-stream token loss, and every action tool-call span's character retention plus token retention/removal. Appended calls that disappear entirely are explicitly counted. The rules and never-flag detector remain primary quality baselines. Archived TF-IDF used a different input and coverage contract; any later comparison must disclose that difference and cannot isolate a causal benefit from the semantic encoder.
