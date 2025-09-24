todos.md (voor SWE)

Observability
- Pas trace_judge_evaluation en trace_batch_evaluation toe in eval/src/judge.py en batch-pad; commit-hash opnemen in DAS.
- Genereer 1 end-to-end Langfuse run en lever run_id + screenshot. Gebruik spans: content_generation, poc1_guardrails, poc2_judge_evaluation.
- Optioneel: voeg OpenTelemetry SDK + prometheus_client toe; exposeer /metrics met histogram-buckets voor latency per laag.

CI/CD
- Voeg minimale workflow toe (.github/workflows/eval.yml) die PoC1 en PoC3 draait, artefacten publiceert (CSV/JSON) en drempel-checks uitvoert.
- Publiceer p50/p95/p99 en policy/PII-stats als job-artefact; exit non-zero bij drempelbreuk.

Datasets & regressie
- Maak freeze-script dat SHA256-manifest schrijft voor eval/datasets; output dataset_hash → opnemen in DAS.
- Draai PoC3 op freeze-set; produceer regressierapport met Δ-scores; link naar artefact in DAS.

Mens vs. judge
- Lever kleine human-annotatie-set (n ≥ 30) en script voor IAA (Cohen’s κ). Doel: overeenstemming ≥ 80% binnen ±1 punt; κ ≥ [..].

Privacy/config
- Zet retentie/EU-residency/audit-logging in infra/config; documenteer variabelen (.env) en lever bewijslink; verifieer PII-masking vóór export.

Documentatie/beslislog
- Voeg 3 korte ADR’s toe: guardrails-scope, judge-kalibratie, regressie-promotiecriteria; map naar NIST (Govern/Map/Measure/Manage).

Bewijsankers voor DAS
- Aanleveren: [run_id], [commit_hash], [dataset_hash], [workflow-link], [artefact-URL].
