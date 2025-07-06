from typing import Dict, Optional, List
from .msisdn_validator import MSISDNValidator
from .time_parser import TimeParser

class SmartCareQueryParser:
    """Parse natural language queries for SmartCare workflow"""
    
    def __init__(self):
        self.msisdn_validator = MSISDNValidator()
        self.time_parser = TimeParser()
        
        # Intent keywords for different query types
        self.intent_keywords = {
            'usage': ['usage', 'penggunaan', 'data', 'kuota', 'traffic', 'konsumsi'],
            'history': ['history', 'riwayat', 'histori', 'record', 'catatan'],
            'detail': ['detail', 'detil', 'info', 'informasi', 'lengkap'],
            'check': ['cek', 'check', 'lihat', 'tampilkan', 'show'],
            'status': ['status', 'kondisi', 'keadaan', 'situasi'],
            'chart': ['chart', 'grafik', 'graph', 'visualisasi', 'diagram']
        }
    
    def parse_query(self, query: str) -> Dict[str, any]:
        """Parse complete query for MSISDN, time, and intent"""
        result = {
            "success": False,
            "msisdn": None,
            "time_range": None,
            "intent": "check",  # default
            "original_query": query,
            "errors": [],
            "api_params": None
        }
        
        # Extract MSISDN
        msisdn = self.msisdn_validator.extract_msisdn(query)
        if msisdn:
            validation = self.msisdn_validator.validate_msisdn(msisdn)
            if validation["valid"]:
                result["msisdn"] = validation
            else:
                result["errors"].append(f"Invalid MSISDN: {validation['error']}")
        else:
            result["errors"].append("No valid MSISDN found in query")
        
        # Extract time range
        time_info = self.time_parser.parse_time_expression(query)
        if time_info["success"]:
            time_validation = self.time_parser.validate_time_range(
                time_info["startTime"], 
                time_info["endTime"]
            )
            if time_validation["valid"]:
                result["time_range"] = time_validation
                result["time_range"]["raw_expression"] = time_info["parsed_expression"]
            else:
                result["errors"].append(f"Invalid time range: {time_validation['error']}")
        else:
            # Use fallback time range
            result["time_range"] = {
                "valid": True,
                "start_time": time_info["startTime"],
                "end_time": time_info["endTime"],
                "fallback": time_info.get("fallback", "today"),
                "raw_expression": time_info["parsed_expression"]
            }
        
        # Detect intent
        result["intent"] = self._detect_intent(query)
        
        # Build API parameters if everything is valid
        if result["msisdn"] and result["time_range"]:
            result["api_params"] = self._build_api_params(result)
            result["success"] = len(result["errors"]) == 0
        
        return result
    
    def _detect_intent(self, query: str) -> str:
        """Detect query intent from keywords"""
        query_lower = query.lower()
        
        # Check for intent keywords
        for intent, keywords in self.intent_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return intent
        
        # Default intent based on query structure
        if any(word in query_lower for word in ['berapa', 'jumlah', 'total']):
            return 'usage'
        elif any(word in query_lower for word in ['tampilkan', 'lihat', 'show']):
            return 'chart'
        else:
            return 'check'
    
    def _build_api_params(self, parsed_result: Dict) -> Dict[str, str]:
        """Build API parameters from parsed results"""
        msisdn_info = parsed_result["msisdn"]
        time_info = parsed_result["time_range"]
        
        return {
            "numValue": msisdn_info["normalized"],
            "startTime": time_info["start_time"],
            "endTime": time_info["end_time"],
            "sceneComb": 1002,
            "roamComb": 1,
            "uuid": "FEKAKFMOJOZgFA7iNzKQJGMQ9JLZJ7mi",
            "templateCode": "CCH",
            "language": "en_US",
            "userName": "admin",
            "granularity": "1h",
            "serviceid": "10010"
        }
    
    def validate_query(self, query: str) -> Dict[str, any]:
        """Quick validation without full parsing"""
        has_msisdn = bool(self.msisdn_validator.extract_msisdn(query))
        has_time_keywords = any(
            keyword in query.lower() 
            for keyword in ['jam', 'hari', 'hour', 'day', 'lalu', 'ago', 'sekarang', 'today']
        )
        
        return {
            "is_smartcare_query": has_msisdn,
            "has_msisdn": has_msisdn,
            "has_time_expression": has_time_keywords,
            "confidence": 0.9 if has_msisdn else 0.1
        }
    
    def extract_examples(self) -> List[Dict[str, str]]:
        """Get example queries for testing"""
        return [
            {
                "query": "detil 08111992172 2 jam lalu",
                "expected_msisdn": "628111992172",
                "expected_intent": "detail"
            },
            {
                "query": "cek 08111992172 jam 10",
                "expected_msisdn": "628111992172", 
                "expected_intent": "check"
            },
            {
                "query": "usage 628111992172 hari ini",
                "expected_msisdn": "628111992172",
                "expected_intent": "usage"
            },
            {
                "query": "grafik 8111992172 kemarin",
                "expected_msisdn": "628111992172",
                "expected_intent": "chart"
            },
            {
                "query": "riwayat 08111992172 pagi tadi",
                "expected_msisdn": "628111992172",
                "expected_intent": "history"
            }
        ]