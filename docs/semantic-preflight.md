# Semantic preflight v2: measured and followed by one reviewed run

The revised synthetic-only encoder check passed. The parent then approved one exact-commit supervised run, which completed within its resource limits but failed every frozen validation quality gate. **No candidate model was exported or activated.** See the [actual one-fit results](semantic-fit-results.md). The executable protocol below is preserved as the pre-run review record; it is not authorization to run again. The app continues to use its rules.

- [Executable protocol and review command](semantic-fit-protocol.md)
- [Frozen machine-readable protocol](../semantic/fit-protocol.json)
- [Driver](../semantic/fit.py), [v2 features](../semantic/features.py), [shared CPU runtime](../semantic/runtime.py)
- [Final v2 measurements](../semantic/results/synthetic-v2-2026-10-06.json)
- [V1 measurements](../semantic/results/synthetic-2026-10-06.json) and [archived v1 analysis](semantic-preflight-v1.md)

## V2 action representation

The v1 action appended tool calls after prose, allowing long prose to erase every call. V2 reserves 94 tokens for assistant text and four separate 40-token call slots. Each slot allows the complete tool name up to eight tokens, the argument head/tail up to 31 tokens, and a separator. Calls remain in original order. Unused budgets are not reassigned. Actions with more than four calls, names exceeding either 128 characters or eight tokens, or empty/unknown-only names abstain. Nonempty unknown-only retained arguments also abstain. Every supported call retains its complete tokenized name and argument representation. This is not a claim that the representation preserves every argument detail.

With no tool calls, text may use 254 tokens. Context remains first 64 task tokens plus last 190 prefix tokens. Each stream receives CLS/SEP and stays within 256 tokens. The two normalized 384-vectors are concatenated as `[context, action]`, never averaged or normalized again. The full deterministic character and token rules, unknown handling and denominators are in the executable protocol.

## Final synthetic measurements

Fixed official revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, one CPU thread, Python 3.12.14. Source files and seven direct runtime package versions remain exactly pinned. This run uses the same `Encoder.encode` implementation as the proposed fit driver, compared against safetensors/PyTorch masked mean pooling and L2 normalization.

| Measurement | V2 result |
| --- | ---: |
| Supervised elapsed | 8.9705 seconds |
| Load | 3.3039 seconds |
| Sampled process-group peak RSS | 819,888 KiB (800.67 MiB) |
| Batch eight, 31 tokens, slowest of three | 0.058565 seconds; 136.60 streams/s |
| Batch eight, 256 tokens, slowest of three | 0.573968 seconds; 13.938 streams/s |
| Normalized embedding max absolute error | 1.6019e-7 |
| Minimum cosine agreement | 0.9999998808 |
| Handcrafted head score max absolute error | 4.5743e-9 |
| Exact tokenizer comparisons | 56 fields |
| ONNX plus nine config/tokenizer files | 91,104,751 bytes |

Ten supported synthetic cases produced 20 encoded streams. The four-call long-input case retained 94 text tokens, all five tokens of each distinct name, and 31 argument tokens per call. Each 447-token capped argument retained its first 16 and last 15 tokens; explicit sentinels verified both ends survived. Three additional cases (five calls, overlong name, emoji-only argument) abstained and were not encoded. Japanese and emoji unknown-token counts remain visible in the report; no multilingual quality claim follows from tokenizer parity.

The unchanged 120-second / 2-GiB preflight supervisor and final publication gate passed. RSS remains a 10-ms sampled threshold. The original v1 run and its code hashes remain archived at commit `861d65baf9ba60869dffd71b7772115c71b4c31a`. An intermediate local v2 smoke run preceded the parent's clarification to retain argument tails; it is not the frozen result or a basis for model selection. The linked final run is the head/tail contract check. No benchmark results informed either change.

## Proposed fit caps

Keep the proposed 2,210-second end-to-end deadline, 2-GiB sampled process-group RSS and 128-MiB candidate-model cap. Using the slower v1 measurement, 1,554 batches at 0.671418409 seconds project to 1,043.38 seconds. Twice that cost plus 120 seconds, rounded up to ten seconds, is 2,210 seconds. V2's projected encoding time is about 891.95 seconds. Neither preprocessing nor a full classifier fit has been measured; these are fail-closed ceilings, not completion guarantees. No rescue tuning or budget increase follows exhaustion.

## Validation and access

Both official weights remain hash-verified in `/tmp/tracecheck-minilm-pinned`, outside Git. Approved model download hosts and sanitized transfer evidence are retained in [access-approved-download.json](../semantic/access-approved-download.json). No additional model downloads, network changes, credentials, paid services, GPU, deployment or log uploads were needed for v2. The pinned upstream model card, provenance notice and standard Apache-2.0 license text are retained under `semantic/notices/`.

Validation passed: 42 Python tests, 20 JavaScript tests, both browser suites with explicit system Chromium 151.0.7922.173 and Playwright 1.62.0, and `pip check`. The bundled Playwright browser remains unavailable; parent CI must check its pinned browser. Standard tests exercise full call retention, abstention, TEST exclusion, source hashes, split-specific cache keys, TRAIN-only one-fit selection with a stub estimator, unchanged FP gates, zero-target task denominators, redacted positional evidence, resource stops and final publication checks. Separate synthetic cache and JSON-head arithmetic checks use an encoder stub and no classifier fit. Browser behavior is unchanged; the existing browser suites remain part of validation. This synthetic validation record predates the separately approved one-fit run. Any further execution requires new parent review.
