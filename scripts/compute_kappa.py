"""Quick helper to compute Cohen's kappa on HITL annotations."""
import json
from pathlib import Path
from collections import Counter

ANNOTATIONS = Path('evidence/iaa/hitl_annotations.json')
OUT_PATH = Path('evidence/iaa/iaa_report.json')

if not ANNOTATIONS.exists():
    raise SystemExit("HITL annotations not found; fill evidence/iaa/hitl_annotations.json first.")

data = json.loads(ANNOTATIONS.read_text())
items = data.get('items', [])

human_a_scores = []
human_b_scores = []

for item in items:
    human_scores = item.get('human_scores') or {}
    a = human_scores.get('annotator_a')
    b = human_scores.get('annotator_b')
    if a is None or b is None:
        continue
    human_a_scores.append(float(a))
    human_b_scores.append(float(b))

if len(human_a_scores) < 5:
    raise SystemExit("Insufficient paired annotations; need ≥5 to compute kappa.")

# Discretise to integer buckets for kappa
labels_a = [round(score) for score in human_a_scores]
labels_b = [round(score) for score in human_b_scores]

observed = sum(1 for a, b in zip(labels_a, labels_b) if a == b) / len(labels_a)
label_space = sorted(set(labels_a + labels_b))
count_a = Counter(labels_a)
count_b = Counter(labels_b)
pe = sum((count_a[label] / len(labels_a)) * (count_b[label] / len(labels_b)) for label in label_space)

kappa = (observed - pe) / (1 - pe) if pe != 1 else 1.0

report = {
    "n_pairs": len(labels_a),
    "labels": label_space,
    "observed_agreement": observed,
    "expected_agreement": pe,
    "cohens_kappa": kappa,
    "targets": {
        "agreement_pct": ">=0.80 binnen ±1 punt",
        "kappa": ">=0.60"
    }
}

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUT_PATH.write_text(json.dumps(report, indent=2))
print(f"Kappa report saved to {OUT_PATH}")
