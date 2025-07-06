# workflows/summary_workflow.py
from typing import Dict, Any, Optional
from workflows.base_workflow import BaseWorkflow

class SummaryWorkflow(BaseWorkflow):
    """Workflow for handling summary queries with aggregated data analysis"""

    def __init__(self, db_tool=None):
        """Initialize SummaryWorkflow with optional shared db_tool"""
        super().__init__(db_tool)
    
    def execute(self, user_query: str, enhanced_context: Optional[Dict] = None, session_id: str = "") -> Dict[str, Any]:
        """
        Execute summary workflow
        
        Handles:
        - Geographic summary (Jakarta, Bandung, etc.)
        - Temporal summary (bulan ini, minggu lalu, etc.)
        - Enhanced context from follow-up queries
        """
        try:
            self._log_workflow_execution(session_id, "SummaryWorkflow", user_query, True)
            
            # Build and execute query with enhanced context
            result = self.query_builder.build_and_execute(user_query, enhanced_context)
            
            if not self._validate_query_result(result):
                return self._create_error_response("Invalid query result format")
            
            execution_result = result["execution_result"]
            
            if execution_result["success"]:
                data = execution_result["data"]
                entities = result.get("entities", {})
                
                # Extract location and time period for narrative context
                location = self.story_agent.extract_location_from_entities(entities)
                time_period = self.story_agent.extract_time_period_from_entities(entities)
                
                if data and len(data) > 0:
                    # Generate comprehensive summary narrative
                    narrative = self.story_agent.generate_summary_narrative(data, location, time_period)
                    
                    return self._create_success_response(
                        narrative,
                        metadata={
                            "sql_query": result.get("sql_query"),
                            "intent": result.get("intent"),
                            "entities": entities,
                            "location": location,
                            "time_period": time_period,
                            "data_points": len(data),
                            "total_complaints": self._calculate_total_complaints(data)
                        }
                    )
                else:
                    # No data found for summary
                    no_data_message = self._generate_no_data_summary(location, time_period)
                    
                    return self._create_success_response(
                        no_data_message,
                        metadata={
                            "sql_query": result.get("sql_query"),
                            "intent": result.get("intent"),
                            "entities": entities,
                            "location": location,
                            "time_period": time_period,
                            "data_points": 0,
                            "total_complaints": 0
                        }
                    )
            else:
                # Query execution failed
                error_msg = execution_result.get("error", "Unknown database error")
                return self._create_error_response(f"Database query failed: {error_msg}")
                
        except Exception as e:
            self._log_workflow_execution(session_id, "SummaryWorkflow", user_query, False)
            return self._create_error_response(f"Summary workflow execution failed: {str(e)}")
    
    def _calculate_total_complaints(self, data: list) -> int:
        """Calculate total complaints from aggregated data"""
        total = 0
        for row in data:
            complaint_count = row.get('total_keluhan', 0)
            if isinstance(complaint_count, (int, float)):
                total += complaint_count
        return int(total)
    
    def _generate_no_data_summary(self, location: str, time_period: str) -> str:
        """Generate message when no summary data is found"""
        if location == "lokasi yang diminta" and time_period == "periode yang diminta":
            return "📊 **Tidak ditemukan data keluhan untuk kriteria yang diminta.**\n\nSilakan coba dengan lokasi atau periode waktu yang lebih spesifik."
        
        elif location != "lokasi yang diminta" and time_period != "periode yang diminta":
            return f"📊 **Tidak ditemukan keluhan di {location} {time_period}.**\n\nKemungkinan tidak ada keluhan yang tercatat pada periode dan lokasi tersebut."
        
        elif location != "lokasi yang diminta":
            return f"📊 **Tidak ditemukan keluhan di {location}.**\n\nLokasi mungkin tidak memiliki keluhan yang tercatat atau nama lokasi perlu disesuaikan."
        
        else:
            return f"📊 **Tidak ditemukan keluhan {time_period}.**\n\nKemungkinan tidak ada keluhan pada periode waktu tersebut."