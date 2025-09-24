#!/usr/bin/env python3
"""
PoC-3 CLI: Batch-regressietest + Tracing

Usage:
    python -m eval.cli.run_poc3_regress \
        --frozen eval/datasets/frozen/2025-09-08_cases.csv \
        --scores_a eval/reports/poc2_scores_V1.csv \
        --scores_b eval/reports/poc2_scores_V2.csv \
        --out eval/reports/poc3_regress_summary.json
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent.parent))

from eval.src.tracing import RegressionTracer


def parse_args():
    parser = argparse.ArgumentParser(description="PoC-3: Batch-regressietest + Tracing")
    
    parser.add_argument(
        "--frozen",
        required=True,
        help="Pad naar frozen dataset CSV"
    )
    
    parser.add_argument(
        "--scores_a",
        required=True,
        help="Pad naar scores CSV voor variant A (baseline)"
    )
    
    parser.add_argument(
        "--scores_b", 
        required=True,
        help="Pad naar scores CSV voor variant B (nieuwe versie)"
    )
    
    parser.add_argument(
        "--out",
        required=True,
        help="Output pad voor regressie summary JSON"
    )
    
    return parser.parse_args()


async def run_poc3_regression(
    frozen_path: str,
    scores_a_path: str,
    scores_b_path: str,
    output_path: str
):
    """Hoofdfunctie voor PoC-3 regressietest"""
    
    print("📊 PoC-3: Batch-regressietest + Tracing gestart")
    print(f"🧊 Frozen dataset: {frozen_path}")
    print(f"📈 Variant A scores: {scores_a_path}")
    print(f"📈 Variant B scores: {scores_b_path}")
    
    # Validate input files
    required_files = [frozen_path, scores_a_path, scores_b_path]
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"❌ Bestand niet gevonden: {file_path}")
            return False
    
    # Load datasets
    try:
        frozen_df = pd.read_csv(frozen_path)
        scores_a_df = pd.read_csv(scores_a_path)
        scores_b_df = pd.read_csv(scores_b_path)
        
        print(f"📊 Frozen dataset: {len(frozen_df)} cases")
        print(f"📊 Scores A: {len(scores_a_df)} cases")
        print(f"📊 Scores B: {len(scores_b_df)} cases")
        
    except Exception as e:
        print(f"❌ Fout bij laden datasets: {e}")
        return False
    
    # Validate dataset alignment
    if len(scores_a_df) != len(scores_b_df):
        print(f"❌ Score datasets hebben verschillende lengte: {len(scores_a_df)} vs {len(scores_b_df)}")
        return False
    
    # Extract variant names from file paths
    variant_a = Path(scores_a_path).stem.split('_')[-1] if '_' in Path(scores_a_path).stem else 'A'
    variant_b = Path(scores_b_path).stem.split('_')[-1] if '_' in Path(scores_b_path).stem else 'B'
    
    # Initialize regression tracer
    tracer = RegressionTracer(
        frozen_dataset_path=frozen_path,
        variant_a=variant_a,
        variant_b=variant_b
    )
    
    print(f"\n🔄 Running regression analysis: {variant_a} vs {variant_b}")
    
    # Convert DataFrames to list of dicts voor tracer
    results_a = scores_a_df.to_dict('records')
    results_b = scores_b_df.to_dict('records')
    
    # Run traced regression analysis
    try:
        regression_summary = await tracer.trace_regression_run(results_a, results_b)
        
    except Exception as e:
        print(f"❌ Fout tijdens regressie analyse: {e}")
        return False
    
    # Save summary
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(regression_summary, f, indent=2)
    
    print(f"\n💾 Regressie summary opgeslagen: {output_path}")
    
    # Print results
    print("\n📈 REGRESSIE RESULTATEN:")
    print(f"  Variant A ({variant_a}) avg score: {regression_summary.get('avg_score_a', 0):.3f}")
    print(f"  Variant B ({variant_b}) avg score: {regression_summary.get('avg_score_b', 0):.3f}")
    print(f"  Score verbetering: {regression_summary.get('score_improvement', 0):+.3f}")
    print(f"  Verbetering %: {regression_summary.get('improvement_percentage', 0):+.1f}%")
    
    # Check promotion criteria
    meets_threshold = regression_summary.get('meets_promotion_threshold', False)
    print(f"  Promotie threshold (≥+0.25): {'✅ GEHAALD' if meets_threshold else '❌ NIET GEHAALD'}")
    
    # Check trace coverage
    expected_traces = len(results_a) + 1  # Case comparisons + summary
    print(f"  LangFuse trace coverage: TODO% (target: 100%)")
    
    success = meets_threshold
    print(f"\n{'✅ PoC-3 GESLAAGD - Variant B goedgekeurd voor promotie' if success else '❌ PoC-3 GEFAALD - Variant B niet geschikt voor promotie'}")
    
    return success


def main():
    """CLI entry point"""
    args = parse_args()
    
    try:
        success = asyncio.run(run_poc3_regression(
            frozen_path=args.frozen,
            scores_a_path=args.scores_a, 
            scores_b_path=args.scores_b,
            output_path=args.out
        ))
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Fout tijdens PoC-3 uitvoering: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()