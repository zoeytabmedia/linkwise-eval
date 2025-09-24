#!/usr/bin/env python3
"""
Test script voor LLM client en judge integratie
Mock test zonder echte API calls
"""

import asyncio
import json
from pathlib import Path
import sys

# Add eval to path
sys.path.append(str(Path(__file__).parent))

from eval.src.judge import Judge
from eval.src.llm_client import LLMClient

class MockLLMClient(LLMClient):
    """Mock client voor testing zonder API calls"""
    
    def __init__(self):
        super().__init__("mock-key", "mock-model")
    
    async def generate(self, system: str, user: str, json_mode: bool = False, schema=None) -> str:
        # Mock business message response
        if "zakelijk bericht" in user.lower():
            return """
            Geachte mevrouw Johnson,

            Dank voor uw interesse in onze CRM-automatiseringsoplossing. Ik zou graag een kennismakingsgesprek met u plannen om uw specifieke behoeften te bespreken.

            Heeft u volgende week tijd voor een gesprek van 30 minuten?

            Met vriendelijke groet,
            """
        
        # Mock judge response
        if json_mode:
            return json.dumps({
                "style_match": {"score": 4, "reason": "Formele u/uw vorm gebruikt, zakelijke toon"},
                "policy_safety": {"score": 5, "reason": "Geen verboden claims of garanties"},
                "pii_free": {"score": 5, "reason": "Geen persoonlijke informatie gelekt"},
                "structure_brevity": {"score": 4, "reason": "Goed gestructureerd, duidelijke CTA"},
                "personalization": {"score": 3, "reason": "Basis personalisatie met naam"},
                "weighted_score": 4.1,
                "pass": True,
                "notes": "Goede zakelijke communicatie"
            })
        
        return "Mock response"
    
    async def judge(self, judge_prompt: str):
        response = await self.generate("", judge_prompt, json_mode=True)
        return json.loads(response)

async def test_integration():
    """Test volledige integratie"""
    
    print("🧪 Testing LLM Client & Judge Integration\n")
    
    # Initialize components
    mock_client = MockLLMClient()
    judge = Judge()
    
    # Test 1: LLM Content Generation
    print("1. Testing content generation...")
    content = await mock_client.generate(
        system="Je bent een professionele business communicator.",
        user="Schrijf een zakelijk bericht voor kennismakingsgesprek met mevrouw Johnson",
        json_mode=False
    )
    print(f"✅ Generated content: {len(content)} characters")
    print(f"   Preview: {content[:100]}...")
    
    # Test 2: Judge Evaluation
    print("\n2. Testing judge evaluation...")
    
    test_input = "Nieuwe prospect - software bedrijf, 50 werknemers, geïnteresseerd in CRM oplossing"
    
    result = await judge.evaluate_single(
        case_id="test_001",
        input_text=test_input,
        output_text=content,
        client=mock_client
    )
    
    print(f"✅ Judge evaluation completed")
    print(f"   Case ID: {result.case_id}")
    print(f"   Weighted Score: {result.weighted_final_score:.2f}")
    print(f"   Passed: {result.passed}")
    print(f"   Criteria scores: {len(result.criterion_scores)}")
    
    # Test 3: Batch Processing
    print("\n3. Testing batch evaluation...")
    
    test_cases = [
        {"id": "001", "input": "Intro meeting met CEO startup", "output": content},
        {"id": "002", "input": "Follow-up na demo", "output": content},
        {"id": "003", "input": "Meeting planning gesprek", "output": content}
    ]
    
    batch_results = await judge.evaluate_batch(
        test_cases,
        mock_client,
        run_id="integration_mock",
        variant="TEST"
    )
    
    print(f"✅ Batch evaluation completed: {len(batch_results)} cases")
    avg_score = sum(r.weighted_final_score for r in batch_results) / len(batch_results)
    print(f"   Average score: {avg_score:.2f}")
    print(f"   Pass rate: {sum(1 for r in batch_results if r.passed)}/{len(batch_results)}")
    
    # Test 4: CSV Export
    print("\n4. Testing CSV export...")
    
    output_path = "eval/reports/integration_test.csv"
    judge.results_to_csv(batch_results, output_path)
    
    print(f"✅ Results exported to {output_path}")
    
    print("\n🎉 All integration tests completed successfully!")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_integration())
    sys.exit(0 if success else 1)
