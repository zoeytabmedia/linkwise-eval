"""
Synchrone guardrails implementatie voor PoC-1

Bevat:
- PII detectie (email, telefoon NL/EU, IBAN, LinkedIn URLs)
- No-go tokens en woordlimiet checks  
- Policy string validatie
- JSON schema validatie
"""

import re
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import jsonschema
from jsonschema import validate, ValidationError
import time

from .pii_patterns import PIIPatterns


@dataclass
class GuardrailResult:
    """Result van een guardrail check"""
    passed: bool
    violations: List[str]
    details: Dict[str, Any]
    latency_ms: float


class PIIDetector:
    """PII detectie voor Nederlandse/EU context"""
    
    def __init__(self):
        self.patterns = PIIPatterns()
        
    def detect_pii(self, text: str) -> Dict[str, List[str]]:
        """Detecteer alle PII in tekst"""
        matches = self.patterns.find_all_pii(text)
        
        # Group by type
        result = {}
        for match in matches:
            if match.type not in result:
                result[match.type] = []
            result[match.type].append(match.match)
        
        return result
        
    def mask_pii(self, text: str) -> str:
        """Vervang PII met masked versies"""
        return self.patterns.mask_pii(text)


class SyncChecks:
    """Hoofdklasse voor alle synchrone checks"""
    
    def __init__(self):
        self.pii_detector = PIIDetector()
        
        # No-go patterns volgens checklist
        self.no_go_patterns = {
            "garantie": re.compile(r"\bgarantie(s|vrij)?\b|\bgegarandeerd\b", re.IGNORECASE),
            "garanderen": re.compile(r"\bgarandeer(t|en|de|den)?\b", re.IGNORECASE),
            "risicoloos": re.compile(r"\brisicoloos\b|\brisk[-\s]?free\b", re.IGNORECASE),
            "zeker_weten": re.compile(r"\bzeker\s+weten\b|\b100%|\b100\s?procent\b", re.IGNORECASE),
            "we_beloven": re.compile(r"\b(we|wij|ik)\s+beloof\b|\bbeloofd\b|\bwe\s+beloven\b", re.IGNORECASE),
            "geld_terug": re.compile(r"\bgeld[-\s]?terug\b|\bmoney[-\s]?back\b", re.IGNORECASE),
            "hey": re.compile(r"\bhey\b|\bhoi\b|\byo\b", re.IGNORECASE),
            "emoji": re.compile(r"[😀-🙏🚀✨🔥👍👏🙂😉😊😅😂🥳❤️💪]"),
            "excess_exclam": re.compile(r"!{2,}")
        }
        
        # CTA patterns voor CTA detection (uitgebreid)
        self.cta_patterns = [
            re.compile(r"\b(plan|plannen|inplannen|afspreken|afspraak|spreken|bellen|call|overleg)\b", re.IGNORECASE),
            re.compile(r"\b(kennismakingsgesprek|sparren|sparring|kennismaking|kort gesprek)\b", re.IGNORECASE),
            re.compile(r"\b(graag uw reactie|uw reactie|reageer|neem contact|contact op)\b", re.IGNORECASE),
            re.compile(r"\b(voorkeurstijd|voorkeursmoment|voorkeur|beschikbaar)\b", re.IGNORECASE),
            re.compile(r"\b(kunt u|zou u|past (u|het)|wat (zijn|zijn uw) voorkeurstijden)\b", re.IGNORECASE),
            re.compile(r"\b(dinsdag|woensdag|donderdag|vrijdag|maandag)\b.*\b(om|tussen|van)\b", re.IGNORECASE),
            re.compile(r"\b(stuur(?:t)? u|laat (u|het) weten|geef.*door)\b", re.IGNORECASE),
            re.compile(r"\b(heeft u tijd|tijd voor|20 minuten|15 minuten|minuutje)\b", re.IGNORECASE),
            re.compile(r"\b(bevestig|bevestigt u|plan.*in|stel.*voor)\b", re.IGNORECASE)
        ]
        
    def check_pii(self, text: str) -> GuardrailResult:
        """Check voor PII en mask indien nodig"""
        start_time = time.perf_counter()
        
        pii_found = self.pii_detector.detect_pii(text)
        violations = []
        
        # Check elke PII type
        for pii_type, matches in pii_found.items():
            if matches:
                violations.append(f"PII {pii_type} gevonden: {len(matches)} instances")
        
        details = {
            "pii_found": pii_found,
            "total_pii_instances": sum(len(matches) for matches in pii_found.values()),
            "masked_text": self.pii_detector.mask_pii(text) if pii_found else text
        }
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
            details=details,
            latency_ms=latency_ms
        )
        
    def check_no_go_tokens(self, text: str) -> GuardrailResult:
        """Check voor verboden tokens"""
        start_time = time.perf_counter()
        
        violations = []
        found_tokens = []
        
        for key, pattern in self.no_go_patterns.items():
            matches = pattern.findall(text)
            if matches:
                for match in matches:
                    found_tokens.append({"key": key, "match": match})
                    violations.append(f"No-go token '{key}' gevonden: {match}")
        
        details = {"found_tokens": found_tokens}
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
            details=details,
            latency_ms=latency_ms
        )
        
    def check_cta_present(self, text: str) -> GuardrailResult:
        """Check voor aanwezigheid van CTA"""
        start_time = time.perf_counter()
        
        cta_found = False
        matched_patterns = []
        
        for pattern in self.cta_patterns:
            if pattern.search(text):
                cta_found = True
                matched_patterns.append(pattern.pattern)
        
        violations = [] if cta_found else ["Geen CTA gevonden in tekst"]
        details = {
            "cta_present": cta_found,
            "matched_patterns": matched_patterns
        }
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        return GuardrailResult(
            passed=cta_found,
            violations=violations,
            details=details,
            latency_ms=latency_ms
        )
        
    def check_word_limit(self, text: str, max_words: int) -> GuardrailResult:
        """Check woordlimiet"""
        start_time = time.perf_counter()
        
        word_count = len(text.split())
        violations = []
        
        if word_count > max_words:
            violations.append(f"Tekst heeft {word_count} woorden, max {max_words}")
            
        details = {"word_count": word_count, "max_words": max_words}
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
            details=details,
            latency_ms=latency_ms
        )
        
    def validate_json_schema(self, json_text: str, schema: Dict[str, Any]) -> GuardrailResult:
        """Valideer JSON tegen schema"""
        start_time = time.perf_counter()
        
        violations = []
        details = {}
        
        try:
            # Parse JSON
            data = json.loads(json_text)
            
            # Valideer tegen schema
            validate(instance=data, schema=schema)
            details["valid_json"] = True
            
        except json.JSONDecodeError as e:
            violations.append(f"Ongeldige JSON: {str(e)}")
            details["json_error"] = str(e)
            
        except ValidationError as e:
            violations.append(f"Schema validatie fout: {str(e)}")
            details["schema_error"] = str(e)
            
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
            details=details,
            latency_ms=latency_ms
        )
        
    def run_all_checks(
        self, 
        text: str, 
        case_id: str = "",
        phase: str = "unknown",
        max_words: Optional[int] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        cta_required: bool = True,
        output_mode: str = "text"
    ) -> Dict[str, Any]:
        """Run alle checks en geef output volgens contract"""
        
        start_total = time.perf_counter()
        
        # Run individual checks
        pii_result = self.check_pii(text)
        nogo_result = self.check_no_go_tokens(text)
        cta_result = self.check_cta_present(text) if cta_required else None
        
        # Word count
        words = text.split()
        word_count = len(words)
        length_result = None
        if max_words:
            length_result = self.check_word_limit(text, max_words)
        
        # JSON validation
        json_result = None
        if json_schema:
            json_result = self.validate_json_schema(text, json_schema)
        
        total_latency = (time.perf_counter() - start_total) * 1000
        
        # Build output volgens contract spec
        result = {
            "case_id": case_id,
            "phase": phase,
            "output_mode": output_mode,
            "word_count": word_count,
            "checks": {
                "json_valid": json_result.passed if json_result else True,
                "json_errors": json_result.violations if json_result else [],
                "length_ok": length_result.passed if length_result else True,
                "length_over_by": max(0, word_count - max_words) if max_words else 0,
                "nogo_hits": nogo_result.details.get("found_tokens", []),
                "pii_hits": [{"type": pii_type, "matches": matches} 
                           for pii_type, matches in pii_result.details.get("pii_found", {}).items()],
                "cta_present": cta_result.passed if cta_result else True,
                "policy_claims": nogo_result.details.get("found_tokens", [])  # Same as nogo for now
            },
            "timings_ms": {
                "pii": pii_result.latency_ms,
                "nogo": nogo_result.latency_ms,
                "schema": json_result.latency_ms if json_result else 0,
                "length": length_result.latency_ms if length_result else 0,
                "cta": cta_result.latency_ms if cta_result else 0,
                "total": total_latency
            }
        }
        
        # Determine severity
        has_json_invalid = json_result and not json_result.passed
        has_pii = len(result["checks"]["pii_hits"]) > 0
        has_policy_claims = len(result["checks"]["policy_claims"]) > 0
        has_missing_cta = cta_required and not result["checks"]["cta_present"]
        has_length_violation = result["checks"]["length_over_by"] > 0
        
        if has_json_invalid or has_pii or has_policy_claims or has_missing_cta or has_length_violation:
            result["severity"] = "fail"
        elif len(result["checks"]["nogo_hits"]) > 0:
            result["severity"] = "warn"
        else:
            result["severity"] = "pass"
            
        return result