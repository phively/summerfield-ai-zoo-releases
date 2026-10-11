# Public comparison contract fixture

This unrelated document-assistant fixture exercises the reusable comparison contract with the baseline and improved candidates in the sibling `targets/document-assistant` directory. Its two cases are one indivisible development group, so the partition explicitly records insufficient coverage for the requested five folds and 10% holdout; it is not a cross-validation or final-holdout result. When a final holdout exists, its IDs and groups belong in the partition, while its content and grading checks remain outside the supplied development suite until separate authorization.

From the repository root:

```text
python plugins/work-smarter/skills/superb-skills/scripts/compare_candidates.py \
  --candidate baseline=plugins/work-smarter/evals/fixtures/superb-skills/targets/document-assistant/baseline/SKILL.md \
  --candidate improved=plugins/work-smarter/evals/fixtures/superb-skills/targets/document-assistant/improved/SKILL.md \
  --suite plugins/work-smarter/evals/fixtures/superb-skills/comparison-contract/suite.json \
  --partition-plan plugins/work-smarter/evals/fixtures/superb-skills/comparison-contract/partition.json \
  --config plugins/work-smarter/evals/fixtures/superb-skills/comparison-contract/config.json \
  --output output/document-assistant-preflight.json \
  --preflight
```

Replace the pending target hash and smoke fields with values from the authorized preflight and inspected smoke trial before running the comparison. The fixture is development evidence; it does not authorize a Cloud run or final holdout validation.
