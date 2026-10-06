export const REVIEW_MODEL = Object.freeze({
  "version": "tfidf-review-reconstruction-2026-10-06",
  "sha256": "10bf769e803e38cd50aef8af86599b482e9e585fc8e59c95a711d517774ec164",
  "bytes": 1866714,
  "cutoff": 0.7,
  "source": {"repository":"https://github.com/RUCBM/AgentProcessBench","revision":"0a42606b178a8c69d40c5765dc05c342f921e578","license_declaration":"Publisher MIT declaration; see THIRD-PARTY-NOTICES.txt for upstream provenance and residual rights limitations","notice":"review-model-NOTICE.txt"},
  "kind": "reconstructed-manual-review",
  "feature_contract": "original-messages-v1",
  "automatic_promotion_eligible": false,
  "validation": {
    "total": 1390,
    "supported": 878,
    "suggestions": 50,
    "labeled_mistakes": 47,
    "false_positives": 3,
    "additional_tp_beyond_rules": 21,
    "additional_fp_beyond_rules": 3
  },
  "limitations": [
    "Development validation only; previously examined tasks, not a fresh held-out test.",
    "Scores are uncalibrated decision scores, not confidence or error probabilities.",
    "Original message grouping is required. Non-ASCII features abstain.",
    "The automatic-flag gate failed. These are optional manual-review suggestions.",
    "Matching archived counts does not prove identity with the lost original fitted weights."
  ]
});
