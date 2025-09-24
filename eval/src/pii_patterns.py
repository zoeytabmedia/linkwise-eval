"""
PII detection patterns for Nederlandse/EU context

Bevat regex patterns voor:
- Email addresses
- Nederlandse telefoonnummers (diverse formaten)  
- EU IBAN codes
- LinkedIn profile URLs
- Nederlandse postcodes en adressen
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class PIIMatch:
    """Gevonden PII met positie en type"""
    type: str
    match: str
    start: int
    end: int
    masked_replacement: str


class PIIPatterns:
    """PII detection patterns voor Nederlandse/EU context"""
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compileer alle regex patterns"""
        
        # Email addresses (RFC 5322 compliant but simplified)
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            re.IGNORECASE
        )
        
        # Nederlandse telefoonnummers (verschillende formaten)
        phone_patterns = [
            r'\b06[-\s]?[0-9]{8}\b',                    # 06-12345678, 06 12345678
            r'\b\+31[-\s]?6[-\s]?[0-9]{8}\b',          # +31-6-12345678, +31 6 12345678
            r'\b0031[-\s]?6[-\s]?[0-9]{8}\b',          # 0031-6-12345678
            r'\b0[0-9]{2,3}[-\s]?[0-9]{6,7}\b',        # 020-1234567, 0123-456789
            r'\b\+31[-\s]?[0-9]{2,3}[-\s]?[0-9]{6,7}\b', # +31-20-1234567
        ]
        self.phone_pattern = re.compile('|'.join(phone_patterns), re.IGNORECASE)
        
        # IBAN codes (Nederlandse en EU formaten)
        # NL: 4 letters + 14 digits, andere EU landen variëren
        self.iban_pattern = re.compile(
            r'\b[A-Z]{2}[0-9]{2}[A-Z0-9]{4,30}\b',
            re.IGNORECASE
        )
        
        # LinkedIn profile URLs
        linkedin_patterns = [
            r'https?://(?:www\.)?linkedin\.com/in/[A-Za-z0-9._-]+/?',
            r'https?://(?:www\.)?linkedin\.com/company/[A-Za-z0-9._-]+/?',
            r'linkedin\.com/in/[A-Za-z0-9._-]+/?',
            r'linkedin\.com/company/[A-Za-z0-9._-]+/?',
        ]
        self.linkedin_pattern = re.compile('|'.join(linkedin_patterns), re.IGNORECASE)
        
        # Nederlandse postcodes (DISABLED - te veel false positives voor productie)
        # self.postcode_pattern = re.compile(r'\b[1-9][0-9]{3}\s?[A-Z]{2}\b', re.IGNORECASE)
        
        # BSN (Burgerservicenummer) - 9 digits with checksum
        self.bsn_pattern = re.compile(r'\b[0-9]{9}\b')
        
        # Rijbewijs nummers (AB-123-CD format)
        self.rijbewijs_pattern = re.compile(
            r'\b[A-Z]{2}[-]?[0-9]{3}[-]?[A-Z]{2}\b',
            re.IGNORECASE
        )
        
        # Credit card numbers (basic pattern)
        self.creditcard_pattern = re.compile(
            r'\b(?:[0-9]{4}[-\s]?){3}[0-9]{4}\b'
        )
        
        # IP addresses
        self.ip_pattern = re.compile(
            r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        )
        
        # API keys en tokens (common patterns)
        self.api_key_pattern = re.compile(
            r'\b(?:sk-|pk-|api[_-]?key)[A-Za-z0-9_-]{20,}\b',
            re.IGNORECASE
        )
    
    def find_all_pii(self, text: str) -> List[PIIMatch]:
        """Vind alle PII matches in tekst"""
        matches = []
        
        # Email addresses
        for match in self.email_pattern.finditer(text):
            matches.append(PIIMatch(
                type="email",
                match=match.group(),
                start=match.start(),
                end=match.end(),
                masked_replacement="[EMAIL_MASKED]"
            ))
        
        # Phone numbers
        for match in self.phone_pattern.finditer(text):
            matches.append(PIIMatch(
                type="phone",
                match=match.group(),
                start=match.start(),
                end=match.end(),
                masked_replacement="[PHONE_MASKED]"
            ))
        
        # IBAN codes
        for match in self.iban_pattern.finditer(text):
            # Extra validatie: moet beginnen met landcode
            if len(match.group()) >= 15:  # Minimale IBAN lengte
                matches.append(PIIMatch(
                    type="iban",
                    match=match.group(),
                    start=match.start(),
                    end=match.end(),
                    masked_replacement="[IBAN_MASKED]"
                ))
        
        # LinkedIn URLs
        for match in self.linkedin_pattern.finditer(text):
            matches.append(PIIMatch(
                type="linkedin",
                match=match.group(),
                start=match.start(),
                end=match.end(),
                masked_replacement="[LINKEDIN_MASKED]"
            ))
        
        # Nederlandse postcodes (DISABLED voor productie)
        # for match in self.postcode_pattern.finditer(text):
        #     matches.append(PIIMatch(
        #         type="postcode",
        #         match=match.group(),
        #         start=match.start(),
        #         end=match.end(),
        #         masked_replacement="[POSTAL_MASKED]"
        #     ))
        
        # BSN (sensitive)
        for match in self.bsn_pattern.finditer(text):
            if self._validate_bsn(match.group()):
                matches.append(PIIMatch(
                    type="bsn",
                    match=match.group(),
                    start=match.start(),
                    end=match.end(),
                    masked_replacement="[BSN_MASKED]"
                ))
        
        # Rijbewijs
        for match in self.rijbewijs_pattern.finditer(text):
            matches.append(PIIMatch(
                type="rijbewijs",
                match=match.group(),
                start=match.start(),
                end=match.end(),
                masked_replacement="[ID_MASKED]"
            ))
        
        # Credit cards
        for match in self.creditcard_pattern.finditer(text):
            matches.append(PIIMatch(
                type="credit_card",
                match=match.group(),
                start=match.start(),
                end=match.end(),
                masked_replacement="[CC_MASKED]"
            ))
        
        # IP addresses
        for match in self.ip_pattern.finditer(text):
            matches.append(PIIMatch(
                type="ip_address",
                match=match.group(),
                start=match.start(),
                end=match.end(),
                masked_replacement="[IP_MASKED]"
            ))
        
        # API keys
        for match in self.api_key_pattern.finditer(text):
            matches.append(PIIMatch(
                type="api_key",
                match=match.group(),
                start=match.start(),
                end=match.end(),
                masked_replacement="[API_KEY_MASKED]"
            ))
        
        # Sort by start position for consistent masking
        matches.sort(key=lambda x: x.start)
        
        return matches
    
    def mask_pii(self, text: str, matches: List[PIIMatch] = None) -> str:
        """Vervang alle PII met masked versies"""
        
        if matches is None:
            matches = self.find_all_pii(text)
        
        if not matches:
            return text
        
        # Replace from end to start to maintain positions
        masked_text = text
        for match in reversed(matches):
            masked_text = (
                masked_text[:match.start] + 
                match.masked_replacement + 
                masked_text[match.end:]
            )
        
        return masked_text
    
    def _validate_bsn(self, bsn: str) -> bool:
        """Valideer BSN checksum (11-proef)"""
        if len(bsn) != 9 or not bsn.isdigit():
            return False
        
        # 11-proef algoritme
        total = 0
        for i, digit in enumerate(bsn[:8]):
            total += int(digit) * (9 - i)
        
        # Laatste cijfer controle
        remainder = total % 11
        if remainder < 2:
            return int(bsn[8]) == remainder
        else:
            return int(bsn[8]) == (11 - remainder)
    
    def get_pii_summary(self, text: str) -> Dict[str, int]:
        """Krijg overzicht van aantal PII per type"""
        matches = self.find_all_pii(text)
        
        summary = {}
        for match in matches:
            summary[match.type] = summary.get(match.type, 0) + 1
        
        return summary