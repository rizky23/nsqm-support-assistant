# workflows/detail_workflow.py
from typing import Dict, Any, Optional
from workflows.base_workflow import BaseWorkflow

class DetailWorkflow(BaseWorkflow):
    """Workflow for handling detail queries (ticket ID or MSISDN lookup)"""
    
    def __init__(self, db_tool=None):
        """Initialize DetailWorkflow with optional shared db_tool"""
        super().__init__(db_tool)
        # Additional initialization for DetailWorkflow if needed
    
    def execute(self, user_query: str, enhanced_context: Optional[Dict] = None, session_id: str = "") -> Dict[str, Any]:
        """
        Execute detail workflow
        
        Handles:
        - Ticket ID lookup (CC-YYYYMMDD-XXXXXXXX)
        - MSISDN lookup (628xxxxxxxxx)
        - Enhanced context from follow-up queries
        """
        try:
            self._log_workflow_execution(session_id, "DetailWorkflow", user_query, True)
            
            # Build and execute query with enhanced context
            result = self.query_builder.build_and_execute(user_query, enhanced_context)
            
            if not self._validate_query_result(result):
                return self._create_error_response("Invalid query result format")
            
            execution_result = result["execution_result"]
            
            if execution_result["success"]:
                data = execution_result["data"]
                entities = result.get("entities", {})
                
                if data and len(data) > 0:
                    # Generate detailed narrative from first record
                    narrative = self.story_agent.generate_detail_narrative(data[0])
                    
                    return self._create_success_response(
                        narrative,
                        metadata={
                            "sql_query": result.get("sql_query"),
                            "intent": result.get("intent"),
                            "entities": entities,
                            "record_found": True,
                            "ticket_data": data[0]
                        }
                    )
                else:
                    # No data found - generate appropriate not found message
                    not_found_message = self._generate_not_found_message(result.get("entities", {}))
                    
                    return self._create_success_response(
                        not_found_message,
                        metadata={
                            "sql_query": result.get("sql_query"),
                            "intent": result.get("intent"),
                            "entities": entities,
                            "record_found": False
                        }
                    )
            else:
                # Query execution failed
                error_msg = execution_result.get("error", "Unknown database error")
                return self._create_error_response(f"Database query failed: {error_msg}")
                
        except Exception as e:
            self._log_workflow_execution(session_id, "DetailWorkflow", user_query, False)
            return self._create_error_response(f"Detail workflow execution failed: {str(e)}")
    
    def _generate_not_found_message(self, entities: Dict) -> str:
        """Generate appropriate not found message based on search criteria"""
        detail_entities = entities.get('detail', [])
        
        if detail_entities:
            entity = detail_entities[0]
            search_value = entity.get('value', 'N/A')
            entity_type = entity.get('entity_type', 'item')
            
            if entity_type == 'ticket_id':
                return f"❌ **Ticket dengan ID {search_value} tidak ditemukan.**\n\nPastikan format ticket ID benar (contoh: CC-20250603-00000475)"
            
            elif 'msisdn' in entity_type:
                return f"❌ **Data untuk MSISDN {search_value} tidak ditemukan.**\n\nPastikan nomor yang dicari sudah benar dan terdaftar dalam sistem."
            
            else:
                return f"❌ **Data untuk {search_value} tidak ditemukan.**"
        
        # Fallback for enhanced context searches
        location = self._extract_location_simple(entities)
        time_period = self._extract_time_simple(entities)
        
        if location != "lokasi yang diminta":
            return f"❌ **Data detail tidak ditemukan di {location} {time_period}.**"
        
        return "❌ **Data tidak ditemukan untuk kriteria yang diminta.**"