# 1. workflows/followup_workflow.py
from typing import Dict, Any, Optional
from workflows.base_workflow import BaseWorkflow

class FollowupWorkflow(BaseWorkflow):
    """Workflow for handling follow-up queries with enhanced context"""
    
    def __init__(self, db_tool=None):
        """Initialize FollowupWorkflow with shared db_tool"""
        super().__init__(db_tool)
        
        # Import here to avoid circular imports
        from workflows.detail_workflow import DetailWorkflow
        from workflows.summary_workflow import SummaryWorkflow
        
        # Pass the SAME shared db_tool to sub-workflows
        self.detail_workflow = DetailWorkflow(self.db_tool)
        self.summary_workflow = SummaryWorkflow(self.db_tool)
    
    def execute(self, user_query: str, enhanced_context: Optional[Dict] = None, session_id: str = "") -> Dict[str, Any]:
        """
        Execute follow-up workflow
        
        Routes to appropriate sub-workflow based on enhanced context intent:
        - detail: Route to DetailWorkflow
        - summary: Route to SummaryWorkflow  
        - list/count: Execute list workflow with narrative
        """
        try:
            self._log_workflow_execution(session_id, "FollowupWorkflow", user_query, True)
            
            if not enhanced_context:
                return self._create_error_response("Enhanced context is required for follow-up workflow")
            
            # Extract intent from enhanced context
            intent = enhanced_context.get("intent", "list")
            print(f"[{session_id}] Follow-up intent: {intent}")
            
            # Route to appropriate workflow based on enhanced intent
            if intent == "detail":
                return self.detail_workflow.execute(user_query, enhanced_context, session_id)
            
            elif intent == "summary":
                return self.summary_workflow.execute(user_query, enhanced_context, session_id)
            
            else:
                # Handle list/count with enhanced context
                return self._execute_list_workflow(user_query, enhanced_context, session_id)
                
        except Exception as e:
            self._log_workflow_execution(session_id, "FollowupWorkflow", user_query, False)
            return self._create_error_response(f"Follow-up workflow execution failed: {str(e)}")
    
    def _execute_list_workflow(self, user_query: str, enhanced_context: Dict, session_id: str) -> Dict[str, Any]:
        """Execute list workflow with enhanced context for follow-up queries"""
        try:
            # Build and execute query with enhanced context and narrative
            result = self.query_builder.build_and_execute_with_narrative(user_query, enhanced_context)
            
            # ✅ FIX: Handle tuple or invalid result types
            print(f"🐛 FollowupWorkflow result type: {type(result)}")
            print(f"🐛 FollowupWorkflow result preview: {str(result)[:200]}...")
            
            # Convert tuple to dict if needed
            if isinstance(result, tuple):
                print("🔧 Converting tuple to dict in FollowupWorkflow")
                result = {
                    "success": False,
                    "execution_result": {"success": False, "error": "Received tuple from build_and_execute_with_narrative"},
                    "entities": {},
                    "narrative": "Error: Received unexpected data format"
                }
            elif not isinstance(result, dict):
                print(f"🔧 Converting {type(result)} to dict in FollowupWorkflow")
                result = {
                    "success": False,
                    "execution_result": {"success": False, "error": f"Unexpected result type: {type(result)}"},
                    "entities": {},
                    "narrative": "Error: Unexpected data format"
                }
            
            # Ensure required keys exist
            if "execution_result" not in result:
                result["execution_result"] = {"success": False, "error": "Missing execution_result"}
            
            if not self._validate_query_result(result):
                return self._create_error_response("Invalid query result format")
            
            execution_result = result["execution_result"]
            
            if execution_result.get("success", False):
                # Use narrative if available, otherwise format data
                if "narrative" in result and result["narrative"]:
                    narrative = result["narrative"]
                else:
                    # Fallback: format data manually
                    data = execution_result.get("data", [])
                    entities = result.get("entities", {})
                    narrative = self._format_list_narrative(data, entities, enhanced_context)
                
                return self._create_success_response(
                    narrative,
                    metadata={
                        "sql_query": result.get("sql_query"),
                        "intent": result.get("intent"),
                        "entities": result.get("entities", {}),
                        "enhanced_context": enhanced_context,
                        "record_count": len(execution_result.get("data", [])),
                        "is_followup": True
                    }
                )
            else:
                error_msg = execution_result.get("error", "Unknown database error")
                return self._create_error_response(f"List query failed: {error_msg}")
                
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"❌ _execute_list_workflow error: {str(e)}")
            print(f"❌ Full traceback: {error_trace}")
            return self._create_error_response(f"List workflow execution failed: {str(e)}")
    
    def _format_list_narrative(self, data: list, entities: Dict, enhanced_context: Dict) -> str:
        """Format narrative for list results when auto-narrative fails"""
        location = self._extract_location_simple(entities)
        time_period = self._extract_time_simple(entities)
        
        # Check for status filters from enhanced context
        filters = enhanced_context.get('filters', '')
        status_entities = entities.get('status', [])
        
        if len(data) > 0:
            # Format examples
            examples = []
            for i, complaint in enumerate(data[:5], 1):  # Show max 5 examples
                examples.append(self._format_complaint_example(complaint, i))
            
            # Determine header based on filters
            if status_entities or 'belum solve' in filters.lower():
                header = f"📋 **Contoh Keluhan yang Belum Selesai di {location} {time_period}:**"
            else:
                header = f"📋 **Contoh Keluhan di {location} {time_period}:**"
            
            return f"{header}\n\n" + "\n\n".join(examples)
        else:
            # No data found
            if status_entities or 'belum solve' in filters.lower():
                return f"📋 **Keluhan yang Belum Selesai di {location} {time_period}**\n\n✅ Tidak ada keluhan yang masih dalam proses penyelesaian."
            else:
                return f"📋 **Tidak ada keluhan ditemukan di {location} {time_period}.**"
    
    def _format_complaint_example(self, complaint: Dict, index: int) -> str:
        """Format single complaint as detailed example"""
        order_id = complaint.get('order_id', 'N/A')
        create_time = complaint.get('create_time', 'N/A')
        description = complaint.get('description', 'N/A')
        location = complaint.get('kabupaten_kota_create_ticket', 'N/A')
        customer_type = complaint.get('customer_type_create_ticket', 'N/A')
        status = complaint.get('business_status', 'N/A')
        
        # Format date
        formatted_date = self._format_date(create_time)
        
        # Format status with emoji
        status_emoji, status_text = self._format_status(status)
        
        # Format customer type emoji
        customer_emoji = "👤" if "Consumer" in customer_type else "🏢"
        
        # Clean and truncate description
        short_desc = self._clean_description(description)
        
        return f"""**{index}. {order_id}**
📅 {formatted_date}
📍 {location}
📋 {short_desc}
{customer_emoji} {customer_type}
{status_emoji} {status_text}"""
    
    def _format_date(self, create_time) -> str:
        """Format datetime for display"""
        if create_time == 'N/A':
            return 'N/A'
        
        try:
            from datetime import datetime
            if isinstance(create_time, str):
                date_str = create_time.replace('Z', '').replace('+00:00', '')
                if 'T' in date_str:
                    dt = datetime.fromisoformat(date_str)
                else:
                    dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            else:
                dt = create_time
            return dt.strftime('%d %b %Y, %H:%M')
        except:
            return str(create_time)
    
    def _format_status(self, status: str) -> tuple:
        """Format status with appropriate emoji and text"""
        if "Progress" in status or "InProgress" in status:
            return "🔄", "Dalam Proses"
        elif "Complete" in status or "Resolved" in status or "Closed" in status:
            return "✅", "Selesai"
        elif "Open" in status:
            return "🆕", "Baru"
        else:
            return "📌", status
    
    def _clean_description(self, description: str) -> str:
        """Clean and truncate description"""
        if description and description != 'N/A':
            clean_desc = description.replace('\n', ' ').replace('\r', ' ').strip()
            return clean_desc[:120] + "..." if len(clean_desc) > 120 else clean_desc
        return "Tidak ada deskripsi keluhan"