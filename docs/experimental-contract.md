# Experimental local inference prerequisites

The inference prerequisites were verified with synthetic fixtures. The subsequent [single reviewed calibration run](calibration-results.md) fitted a research model but passed no promotion gate, so no trained artifact was exported or enabled. The rules app does not import any experimental module. Frozen research files are unchanged.

## Supported input and feature boundary

`experimental/contract.py:make_envelope` produces an envelope with exactly `envelope_version: 1`, `run` (unchanged canonical v1), and `messages`. Each original message has exactly `role` and `step_ids`. Roles are user, assistant, tool, or excluded. An assistant group maps its assistant step first, then all its tool calls in original order. A user or tool group maps one correctly typed step. An excluded system slot maps no steps and retains no system text. Flattened mappings must cover every canonical step exactly once in order. Missing, duplicate, reordered or mis-typed mappings are rejected. Arbitrary canonical v1 files are not assumed to have original-message provenance and remain rules-only.

The feature function uses the current plus previous two ORIGINAL message slots, preserves excluded slots when counting the window, strips answer-tag contents, uses Python code-point slicing at 4000 characters per content/argument field, and keeps the last 12000 code points of the joined feature. It rejects final assistant, future and non-assistant targets. Nonstring content and arguments are serialized by the Python adapter before transfer, avoiding divergent JSON serializer behavior. Explicit mappings preserve message boundaries; their presence is not evidence that a log is authentic or complete.

The scoring contract deliberately supports ASCII feature text only. Unicode features are constructed exactly, but receive `unsupported-unicode` abstention rather than approximate Python Unicode tokenization/case behavior in JavaScript. This is a new, conservative coverage restriction for review, not multilingual parity. Model fitting may retain the frozen vectorizer configuration; validation must apply this abstention policy before threshold selection and count every unsupported record in coverage and recall denominators. Empty/OOV features also abstain. Do not drop unsupported rows from evaluation.

## JSON artifact and fixed caps

| Component | Hard contract |
| --- | --- |
| Envelope and artifact | Separately <= 2 MiB UTF-8; checked before JSON parsing |
| Canonical steps and original groups | <= 2000 each; existing per-field limits retained |
| Feature text | <= 12000 Unicode code points |
| Vocabulary | 1 to 20000 unique terms, each <= 200 UTF-16 units |
| IDF | One finite value per term, from 1 through 100 |
| Coefficients | Exactly 3 finite rows, one value per term, absolute value <= 1000 |
| Intercepts | Exactly 3 finite values, absolute value <= 1000 |
| Classes | Exactly [-1, 0, 1] in this order |
| Threshold | Exactly one of 0.50, 0.60, 0.70, 0.80, 0.90, 0.95 |
| Decision ambiguity | Abstain within 1e-6 of the threshold |
| Worker lifetime | 2000 ms maximum including startup; explicit cancellation terminates worker |

The artifact requires version 1, feature contract `original-messages-v1`, tokenizer `sklearn-ascii-v1`, vocabulary, IDF, coefficients, intercepts, threshold and provenance. Provenance is either synthetic with empty source hashes/null split hash, or train-validation with bounded SHA-256 source hashes and a split hash. These are traceability fields, not signatures or proof that a model passed the promotion gates. Unknown fields, nonfinite numbers, incompatible dimensions and versions are rejected. JSON export never rounds learned weights to meet the cap; an oversized model fails export and remains research-only. There is no pickle, joblib, model URL, executable payload or dynamic evaluation.

`reviewExperimental` starts an isolated module Worker and always terminates it on success, cancellation, error or timeout. It returns numeric message/step positions, uncalibrated scores and abstention reasons; it does not return log excerpts or sensitive identifiers. The worker stays on CPU and makes no network request beyond same-origin static module loading. It does not persist inputs. There is no UI call site, toggle or automatic invocation yet. Future UI integration must explicitly request the experimental review and map numeric positions onto the redacted timeline, keeping model suggestions separate from observed rule evidence.

## Executable proof, without fits

```sh
bash scripts/check.sh
# Additional authoritative sklearn audit using the existing pinned research environment:
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 experimental/check_sklearn.py
```

The ordinary CI suite generates synthetic fixtures at runtime, compares exact Python/Node/browser feature strings and scores, checks malformed contracts, tests timeout/cancellation and confirms the rules UI stays functional. No dataset or trained artifact is checked in. The extra sklearn audit requires the already documented research dependencies, assigns handcrafted coefficients/IDF directly, and patches all fit methods to fail. It compares the reference scores with real sklearn 1.8.0 `transform`/`predict_proba`, without fitting. It is a mandatory pre-fit review check; ordinary CI does not install research dependencies for it.

Coverage includes zero/one/multiple calls, excluded system slots, final/future rejection, nonstring arguments, answer-tag stripping including Python's long-s case equivalence, astral code-point truncation, 12000-character clipping, repeated terms, bigrams, OOV/Unicode abstention, stable softmax and threshold ambiguity. Policy tests prove that a model matching standalone FP counts can still fail the stricter combined rules-plus-model gate.

## Initial preflight evidence

Caps above were fixed before preflight, independently of dataset results. A synthetic 20000-feature artifact serialized to 1363691 bytes. On the development environment:

- 20 exact feature cases and 27 score/abstention cases passed in Chromium. Maximum score error against the Python reference: 1.11e-16. The separate sklearn audit passed 19 numeric cases with the same maximum error.
- Representative envelope: about 30 ms total worker request latency.
- 2000-group envelope (1771928 bytes): about 434 ms, with 43 main-page timer ticks during the request.
- Adversarial large fields (2001768 bytes): about 72 ms, with 7 timer ticks.
- Sampled harness process-tree RSS baseline: 705328 KiB; peak: 1073304 KiB; increase: 367976 KiB. This includes Python, server, driver and Chromium processes and double-counts shared pages. It is not worker heap, incremental model memory, or a hard browser-memory guarantee. Serialized-size and time caps are enforced; a per-worker browser memory limit is not available here.

These are environment-specific observations, not benchmark or production guarantees. CI reruns the bounded checks and reports current measurements. The separate training budget remains 60 seconds/512 MiB; no training occurred in this preflight.
