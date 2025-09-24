#!/usr/bin/env python3
"""
PoC-2 CLI: LLM-as-Judge batch evaluatie

Usage:
    python -m eval.cli.run_poc2_judge_batch \
        --dataset eval/datasets/linkwise_test_inputs_messages.csv \
        --variant V1 --rubric eval/datasets/linkwise_eval_rubric.csv \
        --out eval/reports/poc2_scores_V1.csv
"""

import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent.parent))

from eval.src.judge import Judge
from eval.src.llm_client import create_llm_client


def parse_args():
    parser = argparse.ArgumentParser(description="PoC-2: LLM-as-Judge batch evaluatie")
    
    parser.add_argument(
        "--dataset",
        required=True,
        help="Pad naar test dataset CSV"
    )
    
    parser.add_argument(
        "--variant", 
        required=True,
        help="Variant naam (bv. V1, V2) voor tracking"
    )
    
    parser.add_argument(
        "--rubric",
        help="Pad naar rubric CSV (optioneel, gebruikt default)"
    )
    
    parser.add_argument(
        "--out",
        required=True,
        help="Output pad voor scores CSV"
    )
    
    return parser.parse_args()


async def run_poc2_judge_batch(
    dataset_path: str,
    variant: str,
    rubric_path: str = None,
    output_path: str = None
):
    """Hoofdfunctie voor PoC-2 batch evaluatie"""
    
    print("⚖️  PoC-2: LLM-as-Judge batch evaluatie gestart")
    print(f"📄 Dataset: {dataset_path}")
    print(f"🏷️  Variant: {variant}")
    
    # Load dataset
    if not Path(dataset_path).exists():
        print(f"❌ Dataset bestand niet gevonden: {dataset_path}")
        return False
        
    df = pd.read_csv(dataset_path)
    print(f"📊 {len(df)} cases geladen")
    
    if len(df) < 100:
        print(f"⚠️  Waarschuwing: Slechts {len(df)} cases, target is ≥100")
    
    # Initialize judge en LLM client
    judge = Judge(rubric_path=rubric_path)
    client = create_llm_client()
    print("🧠 LLM client geïnitialiseerd")
    
    # Prepare cases voor batch evaluatie
    cases = []
    for idx, row in df.iterrows():
        cases.append({
            "id": str(row.get('id', idx)),
            "input": row.get('input', ''),
            "output": row.get('output', row.get('message', ''))
        })
    
    print(f"\n🔄 Evaluating {len(cases)} cases...")
    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    # Run batch evaluation
    try:
        results = await judge.evaluate_batch(
            cases,
            client,
            run_id=f"poc2_{variant}_{run_id}",
            variant=variant
        )
        print(f"✅ {len(results)} cases geëvalueerd")
        
    except Exception as e:
        print(f"❌ Fout tijdens batch evaluatie: {e}")
        return False
    
    # Save results
    if output_path:
        judge.results_to_csv(results, output_path)
    
    # Print summary
    print("\n📈 SAMENVATTING:")
    passed_cases = sum(1 for r in results if r.passed)
    valid_scores = [r.weighted_final_score for r in results if r.weighted_final_score is not None]
    avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0

    print(f"  Total cases: {len(results)}")
    print(f"  Passed (≥3.5): {passed_cases} ({passed_cases/len(results)*100:.1f}%)")
    print(f"  Average score: {avg_score:.2f}")
    
    # Check acceptatiecriteria
    success = len(results) >= 100 and avg_score >= 3.5
    print(f"\n{'✅ PoC-2 Batch GESLAAGD' if success else '❌ PoC-2 Batch GEFAALD'}")
    
    return success


def main():
    """CLI entry point"""
    args = parse_args()
    
    try:
        success = asyncio.run(run_poc2_judge_batch(
            dataset_path=args.dataset,
            variant=args.variant,
            rubric_path=args.rubric,
            output_path=args.out
        ))
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Fout tijdens PoC-2 uitvoering: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
