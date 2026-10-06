# Static release candidate, not deployment approval

The unchanged frozen model is retained for a complete static release candidate after source-context review. The flagged credential/name/payment-ID families are benchmark fixture material, and the remaining long numeric candidates are simulated identifiers or conversion-number fragments. This resolves the specific candidate audit; it does not make the vocabulary anonymous or establish universal upstream rights clearance. No deployment or visibility change is authorized. See the bundled THIRD-PARTY-NOTICES.txt for license texts, provenance and residual limitations.

## Illustrations and honest outputs

The new positive illustration is handwritten, inspired by a generic BFCL development command pattern. A source trace was inspected locally but is not included in the gallery. Human evidence is concrete: the request specifies styles.css; the echo action targets index.html; the tool says that file does not exist. The highlighted model window is only cd, its result and echo. It excludes the earlier styles.css instruction and later missing-file result, so the score does not demonstrate recognition of the filename conflict. Human evidence uses additional full-run context. The expandable redacted input preview makes this distinction visible. Selection is deliberate and disclosed: the initial generic folder name demo yielded 0.6299316024, whereas WebDevProjects yielded 0.7298843715, crossing the unchanged 0.70 cutoff. The latter result survives the app's redaction unchanged. This is an illustrative selection and a sensitivity limitation, not unseen accuracy or a robust detector claim.

The second handwritten example successfully reads a café menu. The non-ASCII feature causes unsupported-unicode abstention, not a mistake finding. The prior no-suggestion synthetic example remains available, as do all aggregate evaluations. No fit, threshold change, TEST inference or source-vocabulary modification was performed.

## Current vocabulary audit

Exact `password <word>` and `token <word>` vocabulary filters matched two and one candidates respectively. All three trace to immutable TRAIN BFCL content: 84 occurrences in seven task groups, 50 in user messages and 34 in assistant messages; 73 content fields and 11 tool-argument fields. Literal values are excluded from this report. A subsequent read-only check pinned official gorilla commit `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`. All seven source user-message sequences exactly match official `multi_turn_base_151`, `175`, `177`, `184`, `189`, `190`, and `195` fixtures. All three candidates occur in their initial_config password/access_token fields. The posting API loads scenario credentials into memory and compares them locally; the travel API loads scenario tokens and simulates bookings with in-memory balances and generated transaction IDs. This is concrete simulated-fixture provenance for these three candidates, not a blanket clearance for the entire vocabulary. The independent auditor additionally matched all 42 flagged name/user IDs and 36 credit/gift/certificate IDs to official tau2 airline/retail fixtures, the phone prefix to its telecom database, and 121 of 126 long numeric terms to BFCL/tau2 fixtures. The bounded remaining-index check is recorded below. These are candidate-family findings, not an exhaustive anonymization claim.

Historical fallback options, not needed or authorized by the resolved candidate findings:

1. Keep the unchanged model private and release only the rules app. This preserves private predictions and removes the public vocabulary disclosure surface.
2. Obtain evidence and rights clearance for each flagged family. Public benchmark origin alone is insufficient.
3. Design a versioned privacy transformation that removes/redacts suspect vocabulary and relevant feature handling. This changes behavior unless equivalence is proven. Preserve the original artifact privately and compare on permitted, already examined data without fitting or TEST use; do not silently label it the same model.
4. Hashing or encrypting vocabulary shipped to the browser is not a reliable privacy remedy: low-entropy candidates can be guessed, and client decryption keys would also be public. Dropping zero-weight terms is not automatically prediction-preserving because TF-IDF normalization depends on their contributions.

## Load and runtime bounds

Model loading and verification have a separate 15-second wall-clock cap, with visible progress, cancellation and errors. Only after size/hash/shape verification does the worker signal readiness and start the existing 2-second inference cap. Cold uncached Chromium transfer throttled to 500,000 bytes/second took 3.874 seconds total; inference took 0.7 ms. Clear and replacement during transfer cancel the old worker; integrity failure and a bounded loading timeout were tested. No CSP relaxation or network permission change was made.

Firefox and WebKit binaries are absent. Their official browser-download host was already blocked by the environment policy; no alternate download route or new access was attempted. Chromium mobile viewport checks are not a claim of testing physical mobile devices or other engines.

## Review bundle

Run `python3 scripts/package_public_review.py /tmp/tracecheck-static-candidate.zip --complete` for the complete candidate. The builder checks the unchanged model payload byte count and SHA-256, then packages only the explicit static-asset allowlist, handwritten examples, notices, manifest and proposed response headers. No repository history, raw dataset, research logs or environment files are included. The model vocabulary/coefficients are included intentionally as the app's learned artifact, with source-derived-term warnings and no new license grant for Trace Check.

Without --complete, the earlier private review mode still omits the model, adds an INCOMPLETE PRIVATE REVIEW BUNDLE banner and disables ML controls/handler before any worker request. It must not be mistaken for the complete candidate. Neither mode deploys or changes visibility.

Serve over HTTPS with actual response CSP including frame-ancestors, X-Frame-Options, nosniff, no-referrer and appropriate cache policy. The included _headers format is host-specific; server.py headers do not automatically transfer to static hosting. Verify actual response headers and cold loading on the chosen host before publication. No hosting account, deploy operation or visibility change is authorized by preparing this archive.


Official provenance sources for the narrow credential check:

- [Pinned BFCL fixture](https://github.com/ShishirPatil/gorilla/blob/6ea57973c7a6097fd7c5915698c54c17c5b1b6c8/berkeley-function-call-leaderboard/bfcl_eval/data/BFCL_v4_multi_turn_base.json). Local file SHA-256: 1a21a995d06fd6f20ba55de7bced30ef953ec35e998f502ec2ecf4d66ef1c43a.
- [Posting API scenario loading and local authentication, lines 29-65](https://github.com/ShishirPatil/gorilla/blob/6ea57973c7a6097fd7c5915698c54c17c5b1b6c8/berkeley-function-call-leaderboard/bfcl_eval/eval_checker/multi_turn_eval/func_source_code/posting_api.py#L29).
- [Travel API scenario state, lines 41-78](https://github.com/ShishirPatil/gorilla/blob/6ea57973c7a6097fd7c5915698c54c17c5b1b6c8/berkeley-function-call-leaderboard/bfcl_eval/eval_checker/multi_turn_eval/func_source_code/travel_booking.py#L41) and [simulated booking, lines 465-586](https://github.com/ShishirPatil/gorilla/blob/6ea57973c7a6097fd7c5915698c54c17c5b1b6c8/berkeley-function-call-leaderboard/bfcl_eval/eval_checker/multi_turn_eval/func_source_code/travel_booking.py#L465).

No candidate literals were sent to external search or copied into this evidence note. The independent auditor supplied the broader identifier-family and upstream-notice review before the complete model-containing candidate was prepared. Deployment remains a separate user decision.


## Final seven-index TRAIN context check (no literal values)

| Vocabulary index | TRAIN source and representative location | Classification |
|---|---|---|
| 1058, 1060 | gaia_dev query 6, sample 0, search-result messages 19/23/25/37/39/43/47; 7 field occurrences each | Fractional-digit tokens from decimal unit-conversion values in retrieved content, not credential/identity fields. No raw GAIA content is bundled. |
| 1094 | bfcl query 40, sample 0, register_credit_card result message 9 and book_flight arguments message 12; 12 occurrences | Simulated card_id; official travel_booking.py lines 183-219 generates an in-memory random ID. |
| 1183 | bfcl query 48, samples 1/3, purchase_insurance result message 13; 10 occurrences | Simulated insurance_id; official travel_booking.py lines 857-892 generates an in-memory random ID. |
| 1316 | bfcl query 21, sample 0, liter_to_gallon call message 3, result message 4; 7 occurrences | Fractional digits of conversion output; arithmetic matches liter-to-US-gallon conversion within 1e-5 relative tolerance. |
| 4220, 4222 | bfcl query 40, register_credit_card arguments (sample 0 message 8); 5 occurrences each | Card-number/verification bigrams; value tokens match official multi_turn_base_172 fixture. |

All checks used immutable TRAIN routing and the unchanged artifact. No TEST messages, fit, threshold search, external literal-value search or silent vocabulary edits were used. The public paper's Appendix F describes LLM-generated trajectories; simulator/fixture matching supplies the stronger specific evidence for the flagged structured families.
