"""
LangFuse tracing integratie voor PoC-3

Decorator pattern voor observability met:
- PII masking voor metadata logging
- Trace tags voor run vergelijking  
- Provider-agnostische implementatie
"""

import os
import functools
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

# LangFuse SDK
try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    print("⚠️ LangFuse not installed, tracing disabled")

from .pii_patterns import PIIPatterns


class TracingManager:
    """Manager voor LangFuse tracing met privacy-by-design"""
    
    def __init__(self):
        self.pii_patterns = PIIPatterns()
        self.langfuse = None
        
        if LANGFUSE_AVAILABLE:
            try:
                self.langfuse = Langfuse(
                    host=os.getenv("LANGFUSE_HOST"),
                    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"), 
                    secret_key=os.getenv("LANGFUSE_SECRET_KEY")
                )
                print("✅ LangFuse connected")
            except Exception as e:
                print(f"❌ LangFuse connection failed: {e}")
                self.langfuse = None
    
    def mask_pii_in_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask PII in trace metadata"""
        if isinstance(data, dict):
            masked = {}
            for key, value in data.items():
                if isinstance(value, str):
                    # Mask PII in string values
                    pii_found = self.pii_patterns.find_all_pii(value)
                    masked_value = self.pii_patterns.mask_pii(value, pii_found)
                    masked[key] = masked_value
                elif isinstance(value, dict):
                    masked[key] = self.mask_pii_in_metadata(value)
                elif isinstance(value, list):
                    masked[key] = [self.mask_pii_in_metadata(item) if isinstance(item, dict) else item for item in value]
                else:
                    masked[key] = value
            return masked
        return data
    
    def create_trace(self, name: str, input_data: Dict[str, Any], tags: Optional[List[str]] = None):
        """Create root span that represents a trace"""
        if not self.langfuse:
            return None, "no-trace"

        masked_input = self.mask_pii_in_metadata(input_data)

        span = self.langfuse.start_span(name=name, input=masked_input)
        trace_id = getattr(span, "trace_id", None) or self.langfuse.create_trace_id()

        span.update_trace(
            name=name,
            input=masked_input,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "project": os.getenv("PROJECT_NAME", "linkwise-eval"),
                "environment": os.getenv("ENVIRONMENT", "development")
            },
            tags=tags or []
        )

        return span, trace_id


# Global tracing manager
tracing_manager = TracingManager()


def trace_judge_evaluation(func):
    """Decorator voor judge evaluation tracing"""
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract case info
        case_id = args[1] if len(args) > 1 else kwargs.get('case_id', 'unknown')
        input_text = args[2] if len(args) > 2 else kwargs.get('input_text', '')
        output_text = args[3] if len(args) > 3 else kwargs.get('output_text', '')
        
        # Create trace
        span, trace_id = tracing_manager.create_trace(
            name=f"judge_evaluation_case_{case_id}",
            input_data={
                "case_id": case_id,
                "input_preview": input_text[:100] + "..." if len(input_text) > 100 else input_text,
                "output_preview": output_text[:100] + "..." if len(output_text) > 100 else output_text
            },
            tags=["judge_evaluation", "poc2", f"case_{case_id}"]
        )
        
        start_time = time.time()

        try:
            # Execute function
            result = await func(*args, **kwargs)

            # Calculate metrics
            duration = time.time() - start_time

            # Finish trace
            if span:
                span.update(
                    output={
                        "case_id": case_id,
                        "final_score": result.weighted_final_score,
                        "passed": result.passed,
                        "duration_ms": int(duration * 1000)
                    }
                )
                span.update_trace(
                    output={
                        "case_id": case_id,
                        "final_score": result.weighted_final_score,
                        "passed": result.passed,
                        "duration_ms": int(duration * 1000)
                    },
                    tags=["completed", f"score_{result.weighted_final_score or 'failed'}"]
                )
                span.end()
                tracing_manager.langfuse.flush()

            return result

        except Exception as e:
            # Finish trace with error
            if span:
                span.update_trace(
                    output={"error": str(e)},
                    tags=["error", "failed"]
                )
                span.end()
                tracing_manager.langfuse.flush()

            raise e
    
    return wrapper


def trace_batch_evaluation(run_id: str, variant: str = "V1"):
    """Decorator voor batch evaluation met run vergelijking"""
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create batch trace
            span, trace_id = tracing_manager.create_trace(
                name=f"batch_evaluation_{variant}",
                input_data={
                    "run_id": run_id,
                    "variant": variant,
                    "batch_size": len(args[1]) if len(args) > 1 else 0
                },
                tags=["batch_evaluation", "poc2", f"variant_{variant}", f"run_{run_id}"]
            )
            
            start_time = time.time()
            
            try:
                # Execute batch
                results = await func(*args, **kwargs)
                
                # Calculate batch metrics
                duration = time.time() - start_time
                passed_count = len([r for r in results if r.passed])
                parse_failed_count = len([r for r in results if r.failed_judge_parse])
                valid_scores = [r.weighted_final_score for r in results if r.weighted_final_score is not None]
                avg_score = sum(valid_scores) / max(1, len(valid_scores))
                
                # Finish trace
                if span:
                    span.update(
                        output={
                            "run_id": run_id,
                            "variant": variant,
                            "total_cases": len(results),
                            "passed_cases": passed_count,
                            "parse_failed_cases": parse_failed_count,
                            "average_score": avg_score,
                            "duration_ms": int(duration * 1000)
                        }
                    )
                    span.update_trace(
                        output={
                            "run_id": run_id,
                            "variant": variant,
                            "total_cases": len(results),
                            "passed_cases": passed_count,
                            "parse_failed_cases": parse_failed_count,
                            "average_score": avg_score,
                            "duration_ms": int(duration * 1000)
                        },
                        tags=["completed", f"pass_rate_{passed_count}/{len(results)}"]
                    )
                    span.end()
                    tracing_manager.langfuse.flush()

                return results

            except Exception as e:
                # Finish trace with error
                if span:
                    span.update_trace(
                        output={"error": str(e)},
                        tags=["error", "batch_failed"]
                    )
                    span.end()
                    tracing_manager.langfuse.flush()
                raise e
        
        return wrapper
    return decorator


class RegressionTracer:
    """Trace helper voor PoC-3 regressieanalyses."""

    def __init__(self, frozen_dataset_path: str, variant_a: str, variant_b: str):
        self.dataset_path = Path(frozen_dataset_path)
        self.variant_a = variant_a
        self.variant_b = variant_b
        self.dataset_hash = self._compute_dataset_hash()

    def _compute_dataset_hash(self) -> Optional[str]:
        if not self.dataset_path.exists():
            return None

        hasher = hashlib.sha256()
        with self.dataset_path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _aggregate_scores(self, results: List[Dict[str, Any]]) -> Tuple[float, int, int]:
        scores: List[float] = []
        passed = 0
        parse_failed = 0

        for item in results:
            raw_score = item.get("final_score")
            if raw_score is None or raw_score == "":
                continue
            try:
                score = float(raw_score)
                scores.append(score)
            except (TypeError, ValueError):
                continue

            if str(item.get("passed", "")).lower() == "true":
                passed += 1
            if str(item.get("failed_judge_parse", "")).lower() == "true":
                parse_failed += 1

        avg_score = sum(scores) / len(scores) if scores else 0.0
        return avg_score, passed, parse_failed

    async def trace_regression_run(
        self,
        results_a: List[Dict[str, Any]],
        results_b: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        span, trace_id = tracing_manager.create_trace(
            name="poc3_regression",
            input_data={
                "dataset_path": str(self.dataset_path),
                "dataset_hash": self.dataset_hash,
                "variant_a": self.variant_a,
                "variant_b": self.variant_b,
                "cases_count": min(len(results_a), len(results_b))
            },
            tags=["poc3", "regression", f"{self.variant_a}_vs_{self.variant_b}"]
        )

        start_time = time.time()

        try:
            avg_a, passed_a, parse_failed_a = self._aggregate_scores(results_a)
            avg_b, passed_b, parse_failed_b = self._aggregate_scores(results_b)

            score_improvement = avg_b - avg_a
            improvement_pct = (score_improvement / avg_a * 100) if avg_a else 0.0
            parse_failure_delta = parse_failed_a - parse_failed_b

            meets_threshold = score_improvement >= 0.25 and parse_failed_b <= parse_failed_a

            summary = {
                "trace_id": trace_id,
                "dataset": {
                    "path": str(self.dataset_path),
                    "sha256": self.dataset_hash,
                },
                "variant_a": {
                    "name": self.variant_a,
                    "avg_score": round(avg_a, 3),
                    "passed": passed_a,
                    "parse_failed": parse_failed_a
                },
                "variant_b": {
                    "name": self.variant_b,
                    "avg_score": round(avg_b, 3),
                    "passed": passed_b,
                    "parse_failed": parse_failed_b
                },
                "score_improvement": round(score_improvement, 3),
                "improvement_percentage": round(improvement_pct, 2),
                "parse_failure_delta": parse_failure_delta,
                "meets_promotion_threshold": meets_threshold,
                "duration_ms": int((time.time() - start_time) * 1000)
            }

            if span:
                span.update(output=summary)
                span.update_trace(
                    output={
                        "score_improvement": summary["score_improvement"],
                        "improvement_percentage": summary["improvement_percentage"],
                        "meets_promotion_threshold": meets_threshold
                    },
                    tags=[
                        "completed",
                        "promotion_ready" if meets_threshold else "promotion_blocked"
                    ]
                )
                span.end()
                tracing_manager.langfuse.flush()

            return summary

        except Exception as exc:
            if span:
                span.update_trace(
                    output={"error": str(exc)},
                    tags=["error", "regression_failed"]
                )
                span.end()
                tracing_manager.langfuse.flush()
            raise
