import re
from typing import Optional, List, Dict

class MSISDNValidator:
    """Validate and normalize MSISDN formats for API calls"""
    
    def __init__(self):
        # Indonesian mobile number patterns
        self.patterns = {
            'full_international': r'\b628\d{8,12}\b',           # 628111992172
            'local_format': r'\b08\d{8,12}\b',                  # 08111992172  
            'without_prefix': r'\b8\d{9,12}\b',                 # 8111992172
            'digits_only': r'\b\d{10,15}\b'                     # Fallback for any long number
        }
        
        # Valid Indonesian operator prefixes (after 628)
        self.valid_prefixes = [
            '811', '812', '813', '821', '822', '823', '851', '852', '853',  # Telkomsel
            '814', '815', '816', '855', '856', '857', '858',                 # Indosat
            '817', '818', '819', '859', '877', '878',                        # XL
            '838', '831', '832', '833',                                      # Axis
            '895', '896', '897', '898', '899'                                # Three
        ]
    
    def extract_msisdn(self, text: str) -> Optional[str]:
        """Extract MSISDN from text and normalize to international format"""
        text = str(text).strip()
        
        # Try patterns in order of preference
        for pattern_name, pattern in self.patterns.items():
            matches = re.findall(pattern, text)
            
            for match in matches:
                normalized = self._normalize_msisdn(match)
                if normalized and self._is_valid_operator(normalized):
                    return normalized
        
        return None
    
    def extract_all_msisdns(self, text: str) -> List[str]:
        """Extract all valid MSISDNs from text"""
        msisdns = []
        
        for pattern_name, pattern in self.patterns.items():
            matches = re.findall(pattern, text)
            
            for match in matches:
                normalized = self._normalize_msisdn(match)
                if normalized and self._is_valid_operator(normalized) and normalized not in msisdns:
                    msisdns.append(normalized)
        
        return msisdns
    
    def _normalize_msisdn(self, msisdn: str) -> Optional[str]:
        """Normalize MSISDN to international format (628xxxxxxxxx)"""
        text = str(msisdn).strip()
        
        # Remove + prefix if exists
        if text.startswith('+'):
            text = text[1:]
        
        # Remove all non-digits
        digits_only = re.sub(r'\D', '', text)
        
        if not digits_only:
            return None
        
        # Handle different input formats
        if digits_only.startswith('628'):
            clean_digits = digits_only[3:]  # Remove 628
        elif digits_only.startswith('62'):
            clean_digits = digits_only[2:]  # Remove 62  
        elif digits_only.startswith('08'):
            clean_digits = digits_only[1:]  # Remove '0' only -> '8111992172'
        elif digits_only.startswith('8'):
            clean_digits = digits_only      # Keep as is
        else:
            return None
        
        # Validate clean digits (should be 8xxxxxxxxx with 9-12 digits after 8)
        if not clean_digits.startswith('8') or len(clean_digits) < 10:
            return None
            
        # Build final normalized number
        normalized = '628' + clean_digits
        
        return normalized
    
    def normalize_for_api(self, msisdn: str) -> Optional[str]:
        """Normalize MSISDN for Telkomsel API (8xxxxxxxxx format)"""
        # Remove all non-digits
        digits_only = re.sub(r'\D', '', msisdn)
        
        if not digits_only:
            return None
        
        # Handle different formats
        if digits_only.startswith('628'):
            # Remove 62 prefix, keep 8xxxxxxxxx
            return digits_only[2:]
        elif digits_only.startswith('08'):
            # Remove 0 prefix, keep 8xxxxxxxxx  
            return digits_only[1:]
        elif digits_only.startswith('8') and len(digits_only) >= 10:
            # Already correct format
            return digits_only
        elif len(digits_only) >= 10:
            # Assume it's without leading 8
            return '8' + digits_only
        
        return None
    
    def _is_valid_operator(self, msisdn: str) -> bool:
        """Check if MSISDN belongs to valid Indonesian operator"""
        if not msisdn.startswith('628'):
            return False
        
        if len(msisdn) < 12 or len(msisdn) > 15:
            return False
        
        # Extract operator prefix (3 digits after 628)
        operator_prefix = msisdn[3:6]
        return operator_prefix in self.valid_prefixes
    
    def validate_msisdn(self, msisdn: str) -> Dict[str, any]:
        """Comprehensive MSISDN validation with details"""
        normalized = self._normalize_msisdn(msisdn)
        
        if not normalized:
            return {
                "valid": False,
                "normalized": None,
                "error": "Invalid MSISDN format"
            }
        
        if not self._is_valid_operator(normalized):
            return {
                "valid": False,
                "normalized": normalized,
                "error": "Invalid operator or number length"
            }
        
        # Determine operator
        operator_prefix = normalized[3:6]
        operator = self._get_operator_name(operator_prefix)
        
        return {
            "valid": True,
            "normalized": normalized,
            "original": msisdn,
            "operator": operator,
            "format": self._get_display_format(normalized)
        }
    
    def _get_operator_name(self, prefix: str) -> str:
        """Get operator name from prefix"""
        if prefix in ['811', '812', '813', '821', '822', '823', '851', '852', '853']:
            return "Telkomsel"
        elif prefix in ['814', '815', '816', '855', '856', '857', '858']:
            return "Indosat"
        elif prefix in ['817', '818', '819', '859', '877', '878']:
            return "XL Axiata"
        elif prefix in ['838', '831', '832', '833']:
            return "Axis"
        elif prefix in ['895', '896', '897', '898', '899']:
            return "Three"
        else:
            return "Unknown"
    
    def _get_display_format(self, msisdn: str) -> str:
        """Format MSISDN for display (628-xxx-xxx-xxx)"""
        if len(msisdn) >= 12:
            return f"{msisdn[:3]}-{msisdn[3:6]}-{msisdn[6:9]}-{msisdn[9:]}"
        return msisdn
    
    def is_telkomsel_number(self, msisdn: str) -> bool:
        """Check if MSISDN is Telkomsel number"""
        validation = self.validate_msisdn(msisdn)
        return validation.get("valid", False) and validation.get("operator") == "Telkomsel"