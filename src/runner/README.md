# Batch Execution Guide

Gebruik de bestaande CLI's voor de PoCs. Voorbeelden:

```bash
python -m eval.cli.run_poc1_guardrails \
  --dataset evidence/datasets/linkwise_test_inputs_messages_freeze.csv \
  --schema config/guardrails/json_schema_basic_message.json \
  --out evidence/reports/poc1_guardrails_latest.csv

python -m eval.cli.run_poc2_judge_batch \
  --dataset evidence/datasets/linkwise_test_inputs_messages_freeze.csv \
  --variant V1 \
  --out evidence/reports/poc2_scores_latest.csv

python -m eval.cli.run_poc3_regress \
  --frozen evidence/datasets/linkwise_test_inputs_messages_freeze.csv \
  --scores_a evidence/reports/poc2_scores_V1.csv \
  --scores_b evidence/reports/poc2_scores_V2.csv \
  --out evidence/reports/poc3_regression_latest.json
```

Elke run schrijft CSV/JSON artefacten onder `evidence/reports/`.
