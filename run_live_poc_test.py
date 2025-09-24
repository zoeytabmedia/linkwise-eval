#!/usr/bin/env python3
"""
Live PoC Test met echte OpenAI API calls

Test flow:
1. Genereer zakelijke berichten via OpenAI
2. Run PoC-1 guardrails op echte LLM output  
3. Run PoC-2 judge evaluatie op echte output
"""

import asyncio
import json
from pathlib import Path
import sys
import pandas as pd
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

from eval.src.llm_client import create_llm_client
from eval.src.sync_checks import SyncChecks
from eval.src.judge import Judge
from eval.src.tracing import tracing_manager

async def generate_test_content(client, input_cases):
    """Genereer echte business content voor test cases"""
    
    print("🤖 Generating business messages via OpenAI...")
    generated_content = []
    
    system_prompt = """Je bent een professionele business communicator voor B2B software verkoop.
Schrijf altijd zakelijke berichten in formele u/uw vorm.
Houd berichten beknopt (max 120 woorden) en voeg een duidelijke call-to-action toe."""

    for i, case in enumerate(input_cases[:5]):  # Limiteer tot 5 voor kostenbeheersing
        print(f"  Generating case {i+1}/5: {case['phase']}")
        
        prompt = f"""
        Context: {case['input']}
        Fase: {case['phase']}
        
        Schrijf een passend zakelijk bericht. Gebruik formele u/uw vorm en voeg een concrete call-to-action toe.
        """
        
        try:
            content = await client.generate(
                system=system_prompt,
                user=prompt,
                json_mode=False
            )
            
            generated_content.append({
                "case_id": case['id'],
                "phase": case['phase'],
                "input": case['input'],
                "generated_output": content.strip()
            })
            
        except Exception as e:
            print(f"    ❌ Error generating case {i+1}: {e}")
            generated_content.append({
                "case_id": case['id'], 
                "phase": case['phase'],
                "input": case['input'],
                "generated_output": f"ERROR: {str(e)}"
            })
    
    return generated_content

async def run_poc1_on_generated_content(generated_content):
    """Run PoC-1 guardrails op echte LLM output"""
    
    print("\n🛡️  Running PoC-1 Guardrails on generated content...")
    checker = SyncChecks()
    results = []
    
    for case in generated_content:
        if case['generated_output'].startswith('ERROR:'):
            continue
            
        print(f"  Checking case {case['case_id']}...", end=' ')
        
        result = checker.run_all_checks(
            text=case['generated_output'],
            case_id=case['case_id'],
            phase=case['phase'],
            max_words=120,
            cta_required=True,
            output_mode="text"
        )
        
        results.append(result)
        
        # Status indicator
        if result["severity"] == "pass":
            print("✅")
        elif result["severity"] == "warn":
            print("⚠️")
        else:
            print("❌")
    
    return results

async def run_poc2_judge_evaluation(
    generated_content,
    poc1_results,
    client,
    run_id: str,
    variant: str = "LIVE"
):
    """Run PoC-2 judge evaluation op echte content met gating"""
    
    print("\n⚖️  Running PoC-2 Judge Evaluation with gating...")
    judge = Judge()
    
    # Gating logic: alleen soft-fails naar judge, skip hard-fails
    judge_cases = []
    skipped_cases = []
    
    poc1_lookup = {r['case_id']: r for r in poc1_results}
    
    for case in generated_content:
        if case['generated_output'].startswith('ERROR:'):
            continue
            
        case_id = case['case_id']
        poc1_result = poc1_lookup.get(case_id, {})
        
        # Hard-fail criteria: PII detected or JSON invalid (for json mode)
        has_pii = len(poc1_result.get('checks', {}).get('pii_hits', [])) > 0
        json_invalid = not poc1_result.get('checks', {}).get('json_valid', True)
        
        if has_pii or (json_invalid and poc1_result.get('output_mode') == 'json'):
            print(f"  Skipping case {case_id} (hard-fail: {'PII' if has_pii else 'JSON-invalid'})")
            skipped_cases.append(case_id)
            continue
            
        judge_cases.append({
            "id": case['case_id'],
            "input": case['input'],
            "output": case['generated_output']
        })
    
    print(f"  Gated: {len(judge_cases)} cases to judge, {len(skipped_cases)} hard-fails skipped")
    
    try:
        results = await judge.evaluate_batch(
            judge_cases,
            client,
            run_id=run_id,
            variant=variant
        )
        
        print(f"✅ Judge evaluation completed: {len(results)} cases")
        for result in results:
            if result.failed_judge_parse:
                print(f"  Case {result.case_id}: PARSE_FAILED ({'PASS' if result.passed else 'FAIL'})")
            else:
                print(f"  Case {result.case_id}: {result.weighted_final_score:.2f} ({'PASS' if result.passed else 'FAIL'})")
            
        return results
        
    except Exception as e:
        print(f"❌ Judge evaluation failed: {e}")
        return []

async def main():
    """Main test execution"""
    
    print("🧪 LIVE PoC TEST met OpenAI gpt-5-mini + LangFuse tracing")
    print("=" * 50)
    
    # Start main trace
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if tracing_manager.langfuse:
        main_trace = tracing_manager.langfuse.trace(
            name=f"live_poc_test_{timestamp}",
            input={"test_type": "live_api", "model": "gpt-5-mini", "cases": 5},
            tags=["poc_test", "live_api", "gpt-5-mini"],
            metadata={
                "timestamp": timestamp,
                "project": "linkwise-eval", 
                "environment": "development"
            }
        )
        print("📊 LangFuse trace started")
    
    # Load test cases
    df = pd.read_csv("eval/datasets/linkwise_test_inputs_messages.csv")
    input_cases = df.to_dict('records')
    
    # Initialize LLM client
    client = create_llm_client()
    print(f"🔧 Using: {type(client).__name__} with {client.model}")
    
    # Step 1: Generate content
    generated_content = await generate_test_content(client, input_cases)
    
    # Step 2: PoC-1 Guardrails
    poc1_results = await run_poc1_on_generated_content(generated_content)
    
    # Step 3: PoC-2 Judge (with gating)
    poc2_results = await run_poc2_judge_evaluation(
        generated_content,
        poc1_results,
        client,
        run_id=f"live_{timestamp}",
        variant="LIVE"
    )
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save generated content
    with open(f"eval/reports/live_test_content_{timestamp}.json", 'w') as f:
        json.dump(generated_content, f, indent=2, ensure_ascii=False)
    
    # Save PoC-1 results  
    if poc1_results:
        with open(f"eval/reports/live_poc1_results_{timestamp}.json", 'w') as f:
            json.dump(poc1_results, f, indent=2, ensure_ascii=False)
    
    # Save PoC-2 results
    if poc2_results:
        judge = Judge()
        judge.results_to_csv(poc2_results, f"eval/reports/live_poc2_results_{timestamp}.csv")
    
    # Print summary
    print(f"\n📊 LIVE TEST SUMMARY")
    print(f"Generated content: {len(generated_content)} cases")
    
    if poc1_results:
        passed_poc1 = len([r for r in poc1_results if r['severity'] == 'pass'])
        print(f"PoC-1 Guardrails: {passed_poc1}/{len(poc1_results)} passed")
    
    if poc2_results:
        passed_poc2 = len([r for r in poc2_results if r.passed])
        valid_scores = [r.weighted_final_score for r in poc2_results if r.weighted_final_score is not None]
        parse_failed = len([r for r in poc2_results if r.failed_judge_parse])
        
        if valid_scores:
            avg_score = sum(valid_scores) / len(valid_scores)
            print(f"PoC-2 Judge: {passed_poc2}/{len(poc2_results)} passed, avg score: {avg_score:.2f}")
        else:
            print(f"PoC-2 Judge: {passed_poc2}/{len(poc2_results)} passed, no valid scores")
            
        if parse_failed > 0:
            print(f"  Parse failures: {parse_failed} cases")
    
    # Complete main trace
    if tracing_manager.langfuse:
        valid_scores = [r.weighted_final_score for r in poc2_results if r.weighted_final_score is not None]
        avg_score = sum(valid_scores) / max(1, len(valid_scores)) if valid_scores else 0
        
        main_trace.update(
            output={
                "summary": {
                    "generated_cases": len(generated_content),
                    "poc1_passed": len([r for r in poc1_results if r['severity'] == 'pass']) if poc1_results else 0,
                    "poc1_total": len(poc1_results) if poc1_results else 0,
                    "poc2_passed": len([r for r in poc2_results if r.passed]) if poc2_results else 0,
                    "poc2_total": len(poc2_results) if poc2_results else 0,
                    "poc2_avg_score": avg_score,
                    "parse_failures": len([r for r in poc2_results if r.failed_judge_parse]) if poc2_results else 0
                }
            },
            tags=["completed", f"poc1_pass_{len([r for r in poc1_results if r['severity'] == 'pass']) if poc1_results else 0}"]
        )
        tracing_manager.langfuse.flush()
        print("📊 LangFuse trace completed and flushed")
        print(f"   View traces at: {tracing_manager.langfuse.host}/project/linkwise-eval")

    print(f"\n💾 Results saved with timestamp: {timestamp}")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
