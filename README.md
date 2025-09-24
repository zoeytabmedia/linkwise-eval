# Linkwise Eval — Afstudeeropdracht

Dit repository is ontwikkeld en gebruikt voor mijn afstudeeropdracht/stage. Het project bevat evaluatiescripts, datasets en rapportages om de kwaliteit van gegenereerde zakelijke berichten te toetsen en reproduceerbaar vast te leggen (DAS: Data Availability Statement).

## Overzicht
- PoC‑1: Guardrails & JSON-validatie (sync checks: PII, lengte/structuur, CTA, JSON-schema)
- PoC‑2: LLM‑as‑Judge batch evaluatie (rubric‑gebaseerde scoring + gewogen eindscore)
- PoC‑3: Regressietest + tracing (vergelijk varianten, drempel voor promotie, Langfuse observability)
- Reproduceerbaarheid: dataset freezes, hashes (`hashes.txt`), freeze manifests en DAS-codes (D1/S1/Rk/Fq)

## Snelstart
- Vereisten: Python 3.10+, `pip`
- Installatie:
  ```bash
  python -m venv .venv
  source .venv/bin/activate  # Windows: .venv\Scripts\activate
  pip install -r requirements.txt
  ```
- Configureer `.env` (kopieer eventueel `.env.example`). Zet provider/model en API keys. Let op: commit nooit secrets.

## Datasets (Freeze)
- Canonical dataset (DAS‑D1):
  - Pad: `data/datasets/linkwise_100_messages_freeze.jsonl`
  - SHA-256: `f0311683738dee41be2c4c6cdaa29a25ecbc18d1493ecade0e5d2908d5cebc00`
  - Records: `n=100`
  - Datum: `2025-09-18`
  - Formaat: JSONL
- Freeze manifesten:
  - `data/datasets/freeze_manifest.json`
  - `evidence/datasets/freeze_manifest.json`
- Extra evidence datasets (mirrors):
  - `evidence/datasets/linkwise_100_messages_freeze.jsonl`
  - `evidence/datasets/linkwise_test_inputs_messages_freeze.csv`

## CLI-gebruik
- PoC‑1 (Guardrails):
  ```bash
  python -m eval.cli.run_poc1_guardrails \
    --dataset evidence/datasets/linkwise_100_messages.csv \
    --schema config/guardrails/json_schema_basic_message.json \
    --out evidence/reports/poc1_guardrails_summary.csv \
    --max-words 120
  ```
- PoC‑2 (LLM‑as‑Judge batch):
  ```bash
  python -m eval.cli.run_poc2_judge_batch \
    --dataset evidence/datasets/linkwise_100_messages.csv \
    --variant V1 \
    --rubric config/rubric/rubric.csv \
    --out evidence/reports/live_poc2_results_$(date +%Y%m%d_%H%M%S).csv
  ```
- PoC‑3 (Regressietest):
  ```bash
  python -m eval.cli.run_poc3_regress \
    --frozen evidence/datasets/linkwise_100_messages.csv \
    --scores_a evidence/reports/live_poc2_results_20250918_162946.csv \
    --scores_b evidence/reports/live_poc2_results_20250918_164200.csv \
    --out evidence/reports/poc3_regression_$(date +%Y%m%d_%H%M%S).json
  ```
- Live demo (optioneel, echte API-calls):
  ```bash
  python run_live_poc_test.py
  ```

## Reproduceerbaarheid (DAS)
- Hashes en paden staan in `hashes.txt` en de freeze manifests.
- Gebruik in documentatie verwijzingen als: “(zie DAS‑D1)” of “(zie DAS‑R5)”.
- Voorbeeld DAS‑item (D1):
  - `DAS‑D1 — linkwise_100_messages_freeze.jsonl · SHA-256: f031…bc00 · n=100 · 2025-09-18 · JSONL`

## Observability / Tracing
- Langfuse kan worden geconfigureerd via `.env` (`LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`).
- Voorbeeld artefacten: `evidence/langfuse/traces_overview.png`, `evidence/langfuse/batch_evaluation_v1_detail.png`.

## Mappenstructuur (kort)
- `config/` – rubric, guardrails, regex/PII
- `data/` – dataset freezes (bron)
- `evidence/` – rapportages, langfuse, mirrors van freezes
- `eval/` – CLI’s en evaluatielogica (PoC‑1/2/3)
- `prompts/` – judge prompt(s)
- `scripts/` – hulpscripts (metrics e.d.)

## VCS
- Initiële commit (referentie): `c61d491f95b81850e415fbfaa95d5a9c9ea6bd31`
- Pin commit‑SHA’s in manifests/README wanneer runs/figuren worden geciteerd.

## Opmerkingen
- Deel geen API‑sleutels/secrets in commits of publieke issues.
- Resultaten en figuren zijn bedoeld voor evaluatie tijdens de afstudeeropdracht.

