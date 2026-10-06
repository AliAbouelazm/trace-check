# Trace Check

Review a completed agent run locally. Import JSON, read the task/tool/result timeline, search and filter, inspect evidence-backed review flags, and export a redacted JSON report. Built-in examples cover clean completion, useful exploration, retries, and missing evidence.

## Run

Python 3.10+ is the only runtime requirement. From this directory:

```sh
python3 server.py
```

Open the loopback address printed by the command (normally http://127.0.0.1:8765). Use an example or download the sample, replace its task and steps, and import the completed run. On Windows, use `python server.py` if your Python command is `python`. If the port is occupied, use `python3 server.py --port 0` to select an available port. The server also works when invoked by its absolute path from another directory. Press Ctrl+C to stop. Node 18+ is required for tests and the dataset adapter. No npm install, paid API, account, model download or runtime network connection is required.

## Review behavior

Structural rules identify missing tool results, unmatched results, three identical calls, and error-like tool responses. Every flag states its evidence and uncertainty. A flag requests human review; it does not establish a mistake or cause. Valid retries, polling and neutral exploration can trigger flags. No flags does not mean the run is correct.

The app does not show trained-model confidence. A frozen CPU TF-IDF logistic experiment is included separately in `research/`. Its scores are uncalibrated and it is not used for uploaded logs. See [research results](docs/research.md) and [frozen protocol](research/PROTOCOL.md).

## Import format

Only Trace Check JSON v1 is accepted. Download sample JSON in the app. Unknown fields are rejected, including benchmark labels and answers. Steps preserve input order. `id` is required and unique for every step. Optional `call_id` connects tool calls and results; matching rules cannot operate without it. For parallel calls, assign each call its own call_id and reuse that ID on its result, even if results arrive out of order. Provider-specific logs and JSONL must be converted into this canonical format first. See [schema](docs/schema.json).

```json
{
  "schema_version": 1,
  "run_id": "my-run",
  "task": "Find the project files",
  "status": "completed",
  "steps": [
    {"id": "1", "kind": "tool_call", "tool": "list_files", "call_id": "c1", "content": "{\"path\":\".\"}"},
    {"id": "2", "kind": "tool_result", "tool": "list_files", "call_id": "c1", "status": "ok", "content": "README.md"}
  ]
}
```

Files are bounded to 2 MiB, 2000 steps, 100000 characters per content field, and 20000 characters for the task. Oversized and malformed files fail visibly. The adapter converts one AgentProcessBench row locally, omits labels/reference fields/system prompts, and rejects rows exceeding the app limits without silently truncating them:

```sh
python3 research/adapter.py /path/to/AgentProcessBench/data/AgentProcessBench/bfcl.jsonl /tmp/run.json --row 0
```

## Privacy and trust

File contents stay in browser memory. There is no upload endpoint, localStorage, analytics, execution of logged commands, automatic remediation, or raw upload retention. Clear or refresh to discard the review. Browser extensions and downloads are outside this guarantee. Exports are explicit user actions and contain the full redacted timeline and all flags, including steps hidden by filters. The [report v1 schema](docs/report-schema.json) describes its version, timestamp, review method, limitations and step-linked observations. A report is an export wrapper: save its `run` object as a separate JSON file to review it again. Redaction can expand near-limit strings, so such a run may need manual reduction before reimport. Reimport recomputes structural observations; it never trusts exported flags.

Automatic redaction covers common token patterns, email addresses and named secrets. It is best effort, not a credential detector guarantee. Remove secrets before import and inspect reports before sharing. Log HTML is displayed as text; URLs and commands are never executed. The static server binds only to loopback and serves only `web/`.

## Checks

```sh
npm test
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tests/browser_smoke.py
```

Browser checks require Python Playwright and an installed Chromium. Research reproduction requires the pinned dependencies in `research/requirements.txt`; no research dependencies are needed to use the app.

## V1 acceptance

- [x] Download and import sample JSON; validate and explain malformed, oversized, duplicate-ID and unsupported-schema errors.
- [x] Read ordered task, assistant, tool call and tool result steps; search and combine kind/flag filters.
- [x] Show evidence, uncertainty and rule source for suspicious steps; keep neutral exploration distinct from proven mistakes.
- [x] Present truthful confidence labels: rules only in product, uncalibrated model scores only in research.
- [x] Export a redacted report and clear the current review without retention.
- [x] Smoke, privacy, injection and browser interaction checks.
- [x] Bundle a dataset adapter, provenance audit, frozen task-held-out split, rules/CPU model metrics and resource measurements.

Live monitoring, automatic fixes, model deployment, external publication and hosted storage are outside v1. This repository is independent of physics-adaptation.

## CPU CI and budget

Run `bash scripts/check.sh` for the complete CPU check suite. Browser tests default to the Chromium revision bundled with pinned Playwright; they print the actual browser and package versions. To deliberately use a local system browser, set `CHROMIUM_PATH=/absolute/path/to/chromium`; that run does not establish parity with CI. Native keyboard-picker failures include passive focus, activation, disabled-state, event and console diagnostics. CI runs one standard `ubuntu-latest` job on pull requests and pushes to `main`, with a 10-minute timeout and cancellation of superseded runs. Feature-branch pushes do not create duplicate runs. Official actions are pinned to commit SHAs, permissions are read-only, and checkout verifies the exact PR head (or main commit). The job installs pinned Python Playwright and Chromium, then runs JavaScript, research-integrity, security and desktop/mobile browser checks. No model fits, raw data downloads, matrix, caches, uploaded artifacts or larger runners are used. The owner verified the account's included Actions allowance and $0 stop-usage setting; this workflow does not change billing or permissions. Local checks are not a remote CI success.

See the [bounded calibration protocol](docs/calibration-plan.md) and the completed development-validation run below. No model has passed the optional local inference gates. The archived research hashes identify the original measured code; the current core additionally redacts full error content before extracting evidence snippets. Rule selection behavior and frozen research evidence are unchanged.

Experimental local-inference prerequisites now have a [bounded JSON/grouping contract and synthetic parity proof](docs/experimental-contract.md). They are not connected to the app. Canonical v1 imports still use rules only. The pre-fit scoring contract conservatively abstains on non-ASCII feature text; no multilingual scoring or trained-model quality is claimed.

The [single reviewed calibration run](docs/calibration-results.md) completed within budget, but none of its six fixed thresholds met every combined-policy promotion gate. No trained artifact was exported; the app remains rules-only. Full development-validation results and coverage are retained without raw dataset records.

## Keyboard and review flow

Use Tab to reach the visible Choose JSON file button and Enter or Space to open the native file picker. A successful load focuses the review heading; an invalid import focuses the error and offers Choose another JSON file. Clear run restores focus to the import button. No-match filters offer Clear filters, which returns focus to search. A zero-observation run explicitly warns that structural rules can miss mistakes. These flows are covered in Chromium desktop/mobile tests; this is not a comprehensive screen-reader audit.
