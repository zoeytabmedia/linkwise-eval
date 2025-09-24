Langfuse observability evidence placeholder
-------------------------------------------

Stappen voor een verifieerbare run:
1. Zet LANGFUSE_HOST / LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY in je omgeving.
2. Draai bijvoorbeeld:
   `python -m eval.cli.run_poc2_judge_batch --dataset evidence/datasets/linkwise_test_inputs_messages_freeze.csv --variant V1 --out /tmp/ignore.csv`
   of `python run_live_poc_test.py` zodra API-keys beschikbaar zijn.
3. Na afloop noteer trace-id(s) en timestamp in `langfuse_run_log.txt`.
4. Maak 2–3 screenshots in de Langfuse UI (run-overview + detail) en plaats ze hier als
   - overview.png
   - detail.png

Vervang placeholders zodra de eerste echte run beschikbaar is.
