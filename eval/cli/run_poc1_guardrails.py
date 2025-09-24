#!/usr/bin/env python3
"""
PoC-1 CLI: Guardrails & JSON-validatie

Usage:
    python -m eval.cli.run_poc1_guardrails \
        --dataset eval/datasets/linkwise_test_inputs_messages.csv \
        --schema eval/schemas/basic_message_schema.json \
        --out eval/reports/poc1_guardrails_summary.csv
"""

import argparse
import asyncio
import json
from pathlib import Path
import pandas as pd
import sys
import os

# Add parent directory to path voor imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from eval.src.sync_checks import SyncChecks


def parse_args():
    parser = argparse.ArgumentParser(description="PoC-1: Guardrails & JSON validatie")
    
    parser.add_argument(
        "--dataset", 
        required=True,
        help="Pad naar test dataset CSV"
    )
    
    parser.add_argument(
        "--schema",
        help="Pad naar JSON schema bestand (optioneel)"
    )
    
    parser.add_argument(
        "--out",
        required=True, 
        help="Output pad voor guardrails rapport CSV"
    )
    
    parser.add_argument(
        "--max-words",
        type=int,
        help="Maximum aantal woorden per output (optioneel)"
    )
    
    return parser.parse_args()


async def run_poc1_guardrails(
    dataset_path: str,
    schema_path: str = None, 
    output_path: str = None,
    max_words: int = None
):
    """Hoofdfunctie voor PoC-1 uitvoering"""
    
    print("🔍 PoC-1: Guardrails & JSON-validatie gestart")
    print(f"📄 Dataset: {dataset_path}")
    
    # Load dataset
    if not Path(dataset_path).exists():
        print(f"❌ Dataset bestand niet gevonden: {dataset_path}")
        return False
        
    df = pd.read_csv(dataset_path)
    print(f"📊 {len(df)} cases geladen")
    
    # Load schema (optioneel)
    schema = None
    if schema_path and Path(schema_path).exists():
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        print(f"📋 JSON schema geladen: {schema_path}")
    
    # Initialize guardrails
    checker = SyncChecks()
    
    # Process alle cases
    results = []
    print("\n🔄 Processing cases...")
    
    for idx, row in df.iterrows():
        case_id = row.get('id', str(idx))
        output_text = row.get('expected_output', row.get('output', ''))
        phase = row.get('phase', 'unknown')
        
        print(f"  Case {case_id}...", end=' ')
        
        # Run alle checks volgens nieuwe contract
        case_result = checker.run_all_checks(
            text=output_text,
            case_id=case_id,
            phase=phase,
            max_words=max_words,
            json_schema=schema,
            cta_required=True,
            output_mode="text"
        )
        
        results.append(case_result)
        
        # Status indicator
        if case_result["severity"] == "pass":
            print("✅")
        elif case_result["severity"] == "warn":
            print("⚠️")
        else:
            print("❌")
    
    # Save results als JSON voor gedetailleerde analyse
    if output_path:
        os.makedirs(Path(output_path).parent, exist_ok=True)
        
        # Save detailed JSON results
        json_path = output_path.replace('.csv', '_detailed.json')
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Save summary CSV voor Excel analyse
        summary_data = []
        for result in results:
            summary_row = {
                'case_id': result['case_id'],
                'phase': result['phase'],
                'severity': result['severity'],
                'word_count': result['word_count'],
                'pii_hits_total': len(result['checks']['pii_hits']),
                'nogo_hits_total': len(result['checks']['nogo_hits']),
                'cta_present': result['checks']['cta_present'],
                'json_valid': result['checks']['json_valid'],
                'length_ok': result['checks']['length_ok'],
                'total_latency_ms': result['timings_ms']['total']
            }
            summary_data.append(summary_row)
            
        pd.DataFrame(summary_data).to_csv(output_path, index=False)
        print(f"\n💾 Summary CSV: {output_path}")
        print(f"💾 Detailed JSON: {json_path}")
    
    # Print summary volgens checklist specs
    print("\n📈 BATCH RAPPORT:")
    total_cases = len(results)
    passed = len([r for r in results if r['severity'] == 'pass'])
    warned = len([r for r in results if r['severity'] == 'warn'])
    failed = len([r for r in results if r['severity'] == 'fail'])
    
    print(f"  total_cases: {total_cases}")
    print(f"  pass: {passed}, warn: {warned}, fail: {failed}")
    print(f"  json_invalid: {len([r for r in results if not r['checks']['json_valid']])}")
    print(f"  pii_hits_total: {sum(len(r['checks']['pii_hits']) for r in results)}")
    print(f"  nogo_hits_total: {sum(len(r['checks']['nogo_hits']) for r in results)}")
    print(f"  cta_missing: {len([r for r in results if not r['checks']['cta_present']])}")
    print(f"  length_violations: {len([r for r in results if not r['checks']['length_ok']])}")
    
    # Latency percentiles (p95, p99)
    latencies = [r['timings_ms']['total'] for r in results]
    if latencies:
        p95 = pd.Series(latencies).quantile(0.95)
        p99 = pd.Series(latencies).quantile(0.99)
        print(f"  p95_sync_ms: {p95:.1f}, p99_sync_ms: {p99:.1f}")
    
    # Check acceptatiecriteria: ≥95% PII hit rate, 0 high-risk PII leaks
    pii_clean_rate = (total_cases - sum(len(r['checks']['pii_hits']) for r in results)) / total_cases * 100
    high_risk_leaks = sum(1 for r in results if len(r['checks']['pii_hits']) > 0)
    
    print(f"\n🎯 ACCEPTATIECRITERIA:")
    print(f"  PII clean rate: {pii_clean_rate:.1f}% (target: ≥95%)")
    print(f"  High-risk PII leaks: {high_risk_leaks} (target: 0)")
    
    success = pii_clean_rate >= 95.0 and high_risk_leaks == 0
    print(f"\n{'✅ PoC-1 GESLAAGD' if success else '❌ PoC-1 GEFAALD'}")
    
    return success


def main():
    """CLI entry point"""
    args = parse_args()
    
    try:
        success = asyncio.run(run_poc1_guardrails(
            dataset_path=args.dataset,
            schema_path=args.schema,
            output_path=args.out,
            max_words=args.max_words
        ))
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Fout tijdens PoC-1 uitvoering: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()