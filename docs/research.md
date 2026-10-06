# Data audit and CPU baseline

## Provenance and license

Official sources inspected on 2026-10-06:

- https://github.com/RUCBM/AgentProcessBench
- https://huggingface.co/datasets/LulaCola/AgentProcessBench
- https://github.com/RUCBM/AgentProcessBench/blob/main/annotation_platform/ANNOTATION_GUIDE_v1.md

The GitHub data at commit `0a42606b178a8c69d40c5765dc05c342f921e578` was downloaded into temporary local storage. None of its Python code was executed. The Hugging Face card declares MIT and offers only test splits. The GitHub checkout has no separate LICENSE file. This is a card-declared license, not a finding that all upstream task material has been independently cleared. Raw benchmark records and trained weights are not redistributed here; examples in the app are synthetic. JSONL SHA256 hashes are recorded in `research/results.json` and `research/split.json`.

## Actual data

| Subset | Runs | Task IDs | Step labels | Negative | Neutral | Positive |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| bfcl | 250 | 50 | 2590 | 570 | 104 | 1916 |
| gaia_dev | 250 | 50 | 1628 | 851 | 165 | 612 |
| hotpotqa | 250 | 50 | 734 | 179 | 56 | 499 |
| tau2 | 250 | 50 | 3557 | 1110 | 127 | 2320 |
| Total | 1000 | 200 | 8509 | 2710 | 452 | 5347 |

Every task ID has five attempts. Exact normalized question duplicates merge 200 source task IDs into 189 independent split groups. All attempts and exact question duplicates stay together. Semantic paraphrases beyond those IDs and exact normalized matches may remain.

Fields present: total_index, query_index, sample_index, question, data_source, ground_truth, answer_text, messages, tool_metrics, tools, step_labels, final_label; bfcl/tau2 also have task_description. Step labels are a dictionary keyed by zero-based message indices and score assistant messages only. Messages contain role/content and optional tool_calls, name, tool_call_id. Calls contain function name and serialized arguments. A single labeled assistant message can contain several tool calls.

The model allowlist excludes all reference fields, labels, tool_metrics and identifiers. It also excludes the final assistant message in every run, plus explicit answer-tag contents, and uses no future messages. This conservatively drops 1000 targets, leaving 7509 nonfinal labels. Final conversational answers remain visible in the product timeline; they are never fed to a trained model by this app.

Six complete converted runs violate canonical field limits: three have oversized tool names and three have content over 100000 characters. The largest converted record is about 4.6 MB, above the 2 MiB import bound. The adapter rejects such records visibly instead of silently truncating them. Research evaluates all records independently of the UI import limits.

## Representative audit

These observations inspect source labels and nearby evidence; they do not invent annotator explanations.

- BFCL task 0 attempt 0: message 3 is a positive `pwd` call, message 5 a negative `mkdir`, and message 7 neutral `ls`. Tool names alone do not establish correctness; directory state and user constraints matter.
- GAIA task 0 attempt 0: message 2 is positive search, message 4 neutral fetching of related logic-puzzle sources, and message 6 negative further fetching. The returned evidence discusses a related puzzle rather than proving the user's answer. Neutral research should not be equated to a mistake.
- HotpotQA task 0 attempt 0: initial search is positive, while final message 8 is negative and proposes a city while acknowledging a mismatch with the question's school constraint. This final answer is excluded from training/evaluation inputs and targets.
- Tau2 task 0 attempt 0: greeting message 1 is positive; message 15 is negative despite containing an arithmetically correct balance total. The label cannot be diagnosed from that total alone, and the app does not claim a causal explanation.
- Held-out BFCL task 8 attempt 4 message 16 is neutral. Its following tool response reports a missing file, triggering the error rule. This is an observed neutral false positive.
- Held-out BFCL task 9 attempt 0 message 17 is positive `ls` after a directory removal. Repetition triggers a rule although verification can be useful. This is an observed positive false positive.

The upstream rubric allows negative labels to propagate until correction; these labels are process judgments, not ground truth for newly introduced root causes.

## Frozen experiment

The [protocol](../research/PROTOCOL.md) fixes one TF-IDF logistic configuration, threshold 0.5 and seed 42. No held-out tuning was performed. Split sizes after duplicate grouping:

| Split | Independent task groups | Runs | Nonfinal steps |
| --- | ---: | ---: | ---: |
| Train | 113 | 620 | 4824 |
| Validation | 38 | 190 | 1390 |
| Test | 38 | 190 | 1295 |

This is a **custom research split of a public test-only dataset**, not an official benchmark result. Binary mistake detection treats neutral and positive as non-mistakes. Rules inspect completed runs and tool results; ML uses prefixes, so information availability differs. Tool-result flags map to the assistant that made the call.

| Test method | Precision | Recall | F1 | False positives | Neutral flagged |
| --- | ---: | ---: | ---: | ---: | ---: |
| Product structural rules | 0.6424 | 0.3046 | 0.4133 | 59 | 16 / 52 |
| TF-IDF logistic regression | 0.6429 | 0.3879 | 0.4839 | 75 | 7 / 52 |
| Never flag | 0 | 0 | 0 | 0 | 0 / 52 |

The model has higher aggregate F1 here but more false positives overall. There is no demonstrated universal superiority, calibration or causal certainty. Subset composition is uneven, with only 46 held-out HotpotQA nonfinal steps. Full validation/test confusion counts, three-class metrics, per-subset counts and inspectable error IDs are in [results.json](../research/results.json). No trained model is shipped in the application. A sequence/embedding model is not justified at this stage.

Measured initial run: fit 1.85 s; validation inference 0.236 s; test inference 0.228 s; full wall time 3.71 s; peak Python-process RSS 320.56 MiB; 20000 features; sparse training matrix 7.99 MB; coefficients 0.48 MB. These are environment-specific measurements, exclude setup/download/browser memory, and are not production performance guarantees. CPU only, zero paid API calls, no GPU.

## Reproduce

Use Python 3.11+ and Node 18+. Research dependencies are separate from the dependency-free application runtime.

```sh
python3 -m venv .venv
.venv/bin/pip install -r research/requirements.txt
git clone https://github.com/RUCBM/AgentProcessBench.git /tmp/AgentProcessBench
git -C /tmp/AgentProcessBench checkout 0a42606b178a8c69d40c5765dc05c342f921e578
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python research/evaluate.py /tmp/AgentProcessBench/data/AgentProcessBench --output /tmp/trace-check-results.json
```

No upstream scripts are invoked. Compare source hashes and split membership before comparing scores. Reproduction writes the split next to the chosen output. The initial measurement files in this repository are retained as evidence.
