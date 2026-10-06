# Private publication review, not deployment approval

The private app remains functional with the unchanged model. Public publication is blocked by source-derived vocabulary privacy and upstream licensing questions. Do not publish the unchanged model, claim it is sanitized, or treat dataset availability as proof that embedded values are harmless.

## Illustrations and honest outputs

The new positive illustration is handwritten, inspired by a generic BFCL development command pattern. A source trace was inspected locally but is not included in the gallery. Human evidence is concrete: the request specifies styles.css; the echo action targets index.html; the tool says that file does not exist. The model provides no causal explanation. Selection is deliberate and disclosed: the initial generic folder name demo yielded 0.6299316024, whereas WebDevProjects yielded 0.7298843715, crossing the unchanged 0.70 cutoff. The latter result survives the app's redaction unchanged. This is an illustrative selection and a sensitivity limitation, not unseen accuracy or a robust detector claim.

The second handwritten example successfully reads a café menu. The non-ASCII feature causes unsupported-unicode abstention, not a mistake finding. The prior no-suggestion synthetic example remains available, as do all aggregate evaluations. No fit, threshold change, TEST inference or source-vocabulary modification was performed.

## Current vocabulary audit

Exact `password <word>` and `token <word>` vocabulary filters matched two and one candidates respectively. All three trace to immutable TRAIN BFCL content: 84 occurrences in seven task groups, 50 in user messages and 34 in assistant messages; 73 content fields and 11 tool-argument fields. Literal values are excluded from this report. This establishes TRAIN provenance only. Independent upstream fixture evidence proving that the values are fictional/harmless has not been established. Card/phone/name-ID patterns remain within the independent publication auditor's broader review; this narrow check is not an exhaustive privacy audit.

Remediation options for parent review, with no implementation yet:

1. Keep the unchanged model private and release only the rules app. This preserves private predictions and removes the public vocabulary disclosure surface.
2. Obtain evidence and rights clearance for each flagged family. Public benchmark origin alone is insufficient.
3. Design a versioned privacy transformation that removes/redacts suspect vocabulary and relevant feature handling. This changes behavior unless equivalence is proven. Preserve the original artifact privately and compare on permitted, already examined data without fitting or TEST use; do not silently label it the same model.
4. Hashing or encrypting vocabulary shipped to the browser is not a reliable privacy remedy: low-entropy candidates can be guessed, and client decryption keys would also be public. Dropping zero-weight terms is not automatically prediction-preserving because TF-IDF normalization depends on their contributions.

## Load and runtime bounds

Model loading and verification have a separate 15-second wall-clock cap, with visible progress, cancellation and errors. Only after size/hash/shape verification does the worker signal readiness and start the existing 2-second inference cap. Cold uncached Chromium transfer throttled to 500,000 bytes/second took 3.874 seconds total; inference took 0.7 ms. Clear and replacement during transfer cancel the old worker; integrity failure and a bounded loading timeout were tested. No CSP relaxation or network permission change was made.

Firefox and WebKit binaries are absent. Their official browser-download host was already blocked by the environment policy; no alternate download route or new access was attempted. Chromium mobile viewport checks are not a claim of testing physical mobile devices or other engines.

## Review bundle

Run `python3 scripts/package_public_review.py /tmp/tracecheck-publication-review.zip`. It includes an explicit allowlist of static app assets, handwritten examples, notices, manifest and proposed response headers. No repository history, dataset, research logs, model coefficients/vocabulary, or environment files are included. The model module is intentionally omitted pending audit, so this is a private review bundle and not a complete deployable ML release. A prominent incomplete-review banner is added only to packaged HTML; bundled ML controls and the change handler are disabled before any worker/model request. Rules remain usable. The private app is unchanged. Parent must resolve the blocker before preparing a complete release.

Serve over HTTPS with actual response CSP including frame-ancestors, X-Frame-Options, nosniff, no-referrer and appropriate cache policy. The included _headers format is host-specific; server.py headers do not automatically transfer to static hosting. Verify actual response headers and cold loading on the chosen host before publication. No hosting account, deploy operation or visibility change is authorized by preparing this archive.
