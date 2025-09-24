Hieronder staat een **PRD (Product Requirements Document)** dat je 1‑op‑1 aan **Claude Code** kunt geven in je IDE. Het dekt **PoC‑1/2/3**, houdt rekening met **DeepEval** én **LangFuse**, verwerkt de **Console v1→v2 bevindingen**, en is geschreven zodat een developer het direct kan implementeren. Dit PRD is bovendien in lijn met je PvA/MVP‑architectuur en HU‑verwachtingen (proces, traceerbaarheid, privacy, reproduceerbaarheid).  &#x20;

---

# PRD — Linkwise Evaluation & Tracing PoCs (v1.0)

## 0. Samenvatting

Er wordt een PoC‑pakket opgeleverd voor **kwaliteitsborging** en **traceerbare evaluatie** van LLM‑uitvoer binnen Linkwise. Het pakket bestaat uit:
**PoC‑1 Guardrails & JSON‑validatie (sync)**, **PoC‑2 LLM‑as‑Judge + 10–20% menselijke kalibratie**, **PoC‑3 Batch‑regressietest + Tracing/Observability**. Doel: van ad‑hoc beoordelen naar **systematisch, meetbaar en privacy‑bewust evalueren**, reproduceerbaar voor andere HBO‑ICT‑contexten.&#x20;

**Belangrijke context uit nulmeting (Anthropic Console):**

* V1→V2 toonde **objectieve verbetering** door kleine promptregels: **0% code fences** (was 71%), **100% u/uw‑vorm** (was 9,5%) en **0% impliciete claims** (was 4,8%). Dit legitimeert de PoC’s en de focus op guardrails + regressietests. (Wordt als bewijs in resultatenhoofdstuk gebruikt.)
* Console is geschikt als **handmatige nulmeting**, niet als schaalbare oplossing. PoC’s brengen automatisering, observability en reproduceerbaarheid.&#x20;

---

## 1. Doelen, scope en definitie van succes

**Businessdoel**: kwaliteit en veiligheid van AI‑uitvoer **blijvend** aantonen, met minimale handmatige arbeid en duidelijke audit trail.
**Technisch doel**: evaluatie‑pijplijn met **sync guardrails**, **judge‑scoring** en **tracebare regressietests**.
**Scope**: PoC’s in **ontwikkel/testomgeving**; **géén** productie‑integratie (wel integratie‑klaar). Testen op **geanonimiseerde/synthetische** data.&#x20;

**Acceptatiecriteria (Set A)**

1. **Batch‑evaluatie**: ≥ **100** outputs per promptvariant automatisch scoren + rapporteren (CSV + grafieken).
2. **PII‑hygiëne**: op synthetische PII‑set ≥ **95%** detectie/masking; **0** high‑risk PII ongefilterd in logs.
3. **Kalibratie**: mens‑vs‑LLM‑judge **≤ 1 punt** verschil bij **≥ 80%** van steekproef (10–20%).
   Latency wordt **gemeten**, maar is **geen knock‑out** voor de PoC. (In lijn met PvA: reproduceerbaar, onderbouwd, privacy‑bewust.)&#x20;

**Niet in scope**

* Volledige agent‑tracing in productie.
* Multi‑tenant rapportages voor klanten.
* Contractuele compliance‑certificering. (Komt in aanbevelingen/roadmap.)&#x20;

---

## 2. Belangrijke ontwerpkeuzes & aannames

* **Provider‑agnostisch**: er wordt een dunne **LLM‑client‑abstractie** gebouwd. Sommige providers bieden “structured/JSON output” of “response schemas”; anderen niet. De PoC **forceert** JSON‑schema client‑side (valideer met `jsonschema`) zodat resultaten **uniform** zijn.
* **LangFuse** wordt gebruikt voor **tracing/observability** (PoC‑3); dit sluit aan op de MVP‑architectuurkeuze.&#x20;
* **DeepEval** kan optioneel worden gebruikt als **evaluatie‑engine** voor bepaalde metrics (relevance/faithfulness), maar de PoC blijft **zonder** afhankelijkheden bruikbaar. (Plug‑in architectuur, zie §6.)&#x20;
* **Privacy by design**: PII‑masking vóór opslag/logging; dataminimalisatie en retentie (PoC‑1 verplicht). (HU‑eis: proces + verantwoording.)&#x20;

---

## 3. Doelgroepen & rollen

* **Developer**: implementeert CLI’s, checks, judge, tracing; levert rapporten.
* **Evaluator (mens)**: reviewt 10–20% steekproef met rubric.
* **Projectbegeleiding**: leest dashboards/rapporten; besluit over “promotie” van nieuwe promptversies.&#x20;

---

## 4. Systeemoverzicht (high‑level)

**Datastromen (PoC‑flow):**

1. **Dataset (CSV)** → **LLM‑client** → modeloutput
2. **Sync guardrails** (regex/heuristiek + **JSON‑schema**)
3. **Judge‑scoring** (LLM‑as‑judge) → **scores CSV**
4. **Tracing** (LangFuse) → runs, spans, metadata, scores
5. **Regressietest** (V1 vs V2 op **bevroren** dataset) → rapport
6. **Menselijke steekproef** → kalibratie‑rapport (mens vs model)

**Artefacten**: `reports/*.csv`, `reports/*.md`, LangFuse dashboards, screenshots. (De opzet volgt PvA‑methode en MVP‑architectuur.) &#x20;

---

## 5. Functionele eisen per PoC

### PoC‑1 — Guardrails & JSON‑validatie (sync)

**Doel**: “fouten die pijn doen” **vroeg** en **snel** afvangen: PII, no‑go, woordlimiet, policy‑strings, JSON‑validatie.
**Functionaliteit**

* **PII‑detector**: e‑mail, telefoon (NL/EU), IBAN (NL/EU), LinkedIn‑profiel‑URL; maskeren **vóór** opslag/tracing.
* **No‑go token check** (case‑insensitive; woordgrenzen), **woordlimiet** en optionele policy‑strings (bv. “garanderen”, “risicoloos”).
* **JSON‑schema validatie** (schema meegeleverd, uitbreidbaar per use‑case).
* **Rapport**: aantallen overtredingen per criterium; latency‑percentielen voor sync‑checks.
  **Inputs**: `datasets/linkwise_test_inputs_messages.csv` (uitbreidbaar naar ≥100 rows) en `datasets/linkwise_pii_test_sentences.csv`.
  **Outputs**: `reports/poc1_guardrails_summary.csv`, `reports/poc1_latency.json`, 1–2 screenshots (fouten/top‑oorzaken).
  **Succes**: PII‑hit‑rate ≥95%, **0** high‑risk PII in logs; 100% schema‑valide JSON waar vereist. (Conform requirements privacy/PII‑flow).&#x20;

### PoC‑2 — LLM‑as‑Judge + 10–20% menselijke kalibratie

**Doel**: schaalbaar scoren op **stijl/personalization/structuur/safety**; kalibratie voorkomt bias.
**Functionaliteit**

* **Judge‑prompt** die **alleen JSON** teruggeeft: per criterium score 0–5 + korte reden; **gewogen eindscore**.
* **Batch‑run**: ≥100 cases per variant → `reports/poc2_scores.csv`.
* **Menselijke steekproef**: 10–20% met **identieke rubric** → `reports/poc2_human_ratings.csv`.
* **Vergelijking**: MAE en **% binnen ±1 punt** per criterium; kalibratierapport.
  **Succes**: ≥80% binnen ±1 punt; heldere discrepantie‑voorbeelden en eventuele rubric‑aanpassing. (Past bij methodematrix: reproduceerbaar en toepasbaar.)&#x20;

### PoC‑3 — Batch‑regressietest + Tracing/Observability

**Doel**: wijzigingen **evidence‑based** doorvoeren; volledige audit trail.
**Functionaliteit**

* **Dataset freeze** (kopie): `datasets/frozen/<date>_cases.csv`.
* **V1 vs V2** run met **exact dezelfde** dataset; log in **LangFuse**: `run_id`, `prompt_version`, `model`, `input_hash`, `scores`, `latency`, tags.
* **Vergelijkingsrapport**: gemiddelde/median eindscore, % pass, per‑criterium verschil, eventuele bootstrap‑schatting (optioneel).
* **Beslisregel**: promotie alleen bij **+≥0,25** eindscore én **geen** verslechtering op policy/PII.
  **Succes**: 2 screenshots (runs‑overzicht en scorevergelijking) + rapport; trace‑coverage 100%. (Sluit aan op MVP‑architectuur en LangFuse‑keuze.)&#x20;

---

## 6. Architectuur & implementatie‑richtlijnen

### 6.1 Repo‑structuur (voor Claude Code)

```
eval/
  datasets/
    linkwise_test_inputs_messages.csv
    linkwise_pii_test_sentences.csv
    frozen/
  schemas/
    basic_message_schema.json
  prompts/
    judge_v1.txt
  src/
    __init__.py
    llm_client.py           # provider-agnostische client
    sync_checks.py          # PII/no-go/len/policy + JSON schema
    judge.py                # judge-call + scoring + weights
    regress.py              # V1 vs V2 vergelijken
    tracing.py              # LangFuse integratie
    pii_patterns.py         # regexes (email/phone/IBAN/url)
    utils.py                # io, hashing, timing
  reports/
  cli/
    run_poc1_guardrails.py
    run_poc2_judge_batch.py
    run_poc2_compare_human.py
    run_poc3_regress.py
  .env.example
  requirements.txt
  README.md
```

### 6.2 Packages & omgevingsvariabelen

* **Python 3.11+**; `pip install jsonschema pandas numpy regex httpx pydantic python-dotenv`
* **LangFuse** (PoC‑3): `pip install langfuse` + `.env`: `LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY`.
* **Optioneel DeepEval** (PoC‑2 als engine): `pip install deepeval` (achter interface).&#x20;

### 6.3 LLM‑client‑abstractie

```python
class LLMClient:
    def __init__(self, provider: str, api_key: str, model: str): ...
    async def generate(self, system: str, user: str, json_mode: bool=False, schema: dict|None=None) -> str: ...
    async def judge(self, judge_prompt: str) -> dict: ...
```

* **json\_mode/schema**: als provider “structured outputs” ondersteunt, gebruiken; anders **schema‑forcering** via prompt + client‑side **`jsonschema.validate`**.
* Providerkeuze via `.env`: `PROVIDER=openai|anthropic|...`, `MODEL=...`. (Vendor‑agnostisch, zoals gewenst in PvA/MVP.)&#x20;

### 6.4 LangFuse tracing (PoC‑3)

* Decorator `@observe()` op batchfuncties; set **trace tags**: `["linkwise", phase, variant]`.
* Log metadata **zonder PII** (eerst maskeren). Zie MVP‑voorbeeld (decorator pattern).&#x20;

### 6.5 DeepEval integratie (optioneel)

* Adapter `deepeval_adapter.py` met functies `score_relevance`, `score_faithfulness`.
* Resultaten terugschrijven naar dezelfde `reports/poc2_scores.csv` kolommen zodat rapporten uniform blijven.&#x20;

---

## 7. Data, schema’s en rubric

### 7.1 Datasets (meegeleverd)

* `linkwise_test_inputs_messages.csv` (≥100 rijen; fasen intro/followup/meeting; no‑go‑sets; max\_words; hints).
* `linkwise_pii_test_sentences.csv` (email, phone, IBAN, profiel‑URL, adressen + expected mask).
  *(Bestanden zijn al gegenereerd in eerdere sessie en kunnen worden uitgebreid.)*

### 7.2 JSON‑schema (basis)

`schemas/basic_message_schema.json`:

```json
{"type":"object","additionalProperties":false,
 "properties":{"message":{"type":"string","minLength":10},
              "cta":{"type":"string","minLength":0},
              "next_step":{"type":"string","enum":["propose_times","await_reply","handover"]}},
 "required":["message","cta"]}
```

### 7.3 Rubric (weights & drempels)

* **Criteria**: `style_match(0.30)`, `policy_safety(0.30)`, `pii_free(0.20)`, `structure_brevity(0.10)`, `personalization(0.10)`; **PASS ≥ 3.5**.
* CSV `linkwise_eval_rubric.csv` met definities en drempels. (Afgeleid uit je methodematrix/requirements.) &#x20;

---

## 8. CLI‑commando’s (voor developer)

**PoC‑1**

```
python -m eval.cli.run_poc1_guardrails \
  --dataset eval/datasets/linkwise_test_inputs_messages.csv \
  --schema eval/schemas/basic_message_schema.json \
  --out eval/reports/poc1_guardrails_summary.csv
```

**PoC‑2**

```
python -m eval.cli.run_poc2_judge_batch \
  --dataset eval/datasets/linkwise_test_inputs_messages.csv \
  --variant V1 --rubric eval/datasets/linkwise_eval_rubric.csv \
  --out eval/reports/poc2_scores_V1.csv

python -m eval.cli.run_poc2_compare_human \
  --model eval/reports/poc2_scores_V1.csv \
  --human eval/reports/poc2_human_ratings.csv \
  --out eval/reports/poc2_calibration_V1.json
```

**PoC‑3**

```
python -m eval.cli.run_poc3_regress \
  --frozen eval/datasets/frozen/2025-09-08_cases.csv \
  --scores_a eval/reports/poc2_scores_V1.csv \
  --scores_b eval/reports/poc2_scores_V2.csv \
  --out eval/reports/poc3_regress_summary.json
```

---

## 9. Testplan & rapportage

**PoC‑1**

* Meet: #no‑go hits, #PII hits per type, #JSON‑invalid, woordlimiet‑overtredingen; **p95 latency** sync‑checks.
* Rapporteer: tabel + heatmap top‑oorzaken; 1–2 voorbeeldoutputs (geanonimiseerd).

**PoC‑2**

* Meet: score‑distributies per criterium, eindscore, **mens vs model** (MAE, % binnen ±1).
* Rapporteer: histogrammen + tabel discrepanties; 3 case‑call‑outs (goed, borderline, fout).

**PoC‑3**

* Meet: Δ‑eindscore (V2‑V1), Δ per criterium, % pass; trace‑coverage = 100%.
* Rapporteer: samenvatting + 2 LangFuse screenshots. (Pattern volgt MVP‑architectuurvalidatie.)&#x20;

---

## 10. Beperkingen, risico’s, mitigaties

* **Structured output verschillen per provider** → altijd ook **client‑side schema‑validatie**.
* **LLM‑judge bias/kosten** → **steekproef mens**; cache/seed waar mogelijk.
* **PII‑regex false negatives** → combineer met voorbeeldzinnen, periodieke audit (200 zinnen).
* **Vendor lock‑in risico** → data‑export (CSV/JSON) + **LangFuse open‑source core**.&#x20;

---

## 11. Roadmap (na PoC)

* **Agent‑tracing** (toolcalls, chain‑of‑thought **niet** loggen; alleen metadata)
* **Outcome‑metrics** koppelen (reply rate) naast kwaliteitsscores.
* **Multi‑tenant dashboards** voor klanten.
* **Automatische regressie‑alerts** in CI. (Sluit aan op jouw MVP‑pad.)&#x20;

---

## 12. Koppeling aan onderwijs (HU) – wat in het verslag moet staan

* **Methodiek**: literatuur + PoC’s + batches + kalibratie + regressie (methode‑mix) met logboek.&#x20;
* **Resultaten**: Console v1→v2 + PoC‑rapporten (tabellen, screenshots).
* **Kwaliteitsborging & ethiek**: PII‑masking, dataminimalisatie/retentie, audit trail, geen misleidende claims. (Bronvermelding APA; privacy‑maatregelen expliciet.)&#x20;

---

## 13. Takenlijst (voor Claude Code)

**Infra & setup**

* [ ] Repo‑structuur en `requirements.txt` aanmaken; `.env.example` met keys (provider, LangFuse).
* [ ] `llm_client.py`: provider‑agnostische client + optionele structured output; fallback = client‑side schema‑validatie.

**PoC‑1**

* [ ] `sync_checks.py`: PII‑regex (email/phone/IBAN/URL), no‑go, woordlimiet, policy strings; masker vóór opslag.
* [ ] `run_poc1_guardrails.py`: batchloader, checks, latency meting, CSV/JSON rapport.

**PoC‑2**

* [ ] `judge.py`: laad `prompts/judge_v1.txt`; call LLM; parse JSON; gewogen score; schrijf CSV.
* [ ] `run_poc2_judge_batch.py`: batch ≥100; variantflag; output per case.
* [ ] `run_poc2_compare_human.py`: lees mens‑ratings; bereken MAE en % binnen ±1; schrijf rapport.

**PoC‑3**

* [ ] `tracing.py`: LangFuse decorator + context update; PII masker op metadata.
* [ ] `run_poc3_regress.py`: V1/V2 vergelijken op frozen dataset; beslisregel toepassen; samenvatting schrijven.

**Docs**

* [ ] `README.md`: hoe draaien, welke artefacten opleveren, waar screenshots vandaan komen.
* [ ] `reports/summary_<date>.md`: template met tabellen en 2 screenshots.

---

### Bijlagen / referenties in dit PRD

* PvA (methodematrix, fasering, kwaliteitscriteria) — gebruikt voor doelen/methoden. &#x20;
* MVP‑architectuur (LangFuse‑keuze, decorator‑integratie, risico’s) — gebruikt voor PoC‑3/integratie.
* Requirements‑document (privacy/PII, toolingoverzicht) — gebruikt voor PoC‑1/2 keuzes.&#x20;
* HU‑leidraad (proces, logboek, verantwoording) — gebruikt voor verslagopbouw/bewijs.&#x20;

---

## Opmerkingen m.b.t. modellen en structured output

* **Assumptie**: sommige providers hebben “JSON/structured output” of “response schema” features; anderen minder strikt. De PoC **verlaat zich niet** op providerfeatures en controleert **altijd** zelf via `jsonschema`.
* **Multi‑provider**: LLM‑client‑abstractie maakt gebruik van meerdere modellen (Claude, OpenAI, OSS via proxy) mogelijk; dit sluit aan op je anti‑lock‑in strategie.&#x20;

---

### Klaar om te starten

Je kunt dit PRD direct aan **Claude Code** geven. Als de eerste implementatie van **PoC‑1** draait, lever dan het **guardrails‑rapport** (CSV/JSON) en 1–2 screenshots; ik schrijf er meteen nette alinea’s voor je verantwoordingsdocument bij (methode → bevinding → conclusie), met verwijzingen naar PvA/MVP/leidraad.&#x20;
