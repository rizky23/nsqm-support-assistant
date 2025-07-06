# workflows/base_workflow.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from tools.direct_database_tool import DirectDatabaseTool
from tools.smart_query_builder import SmartQueryBuilder
from agents.story_agent import StoryAgentSummary

class BaseWorkflow(ABC):
    """Abstract base class for all workflows"""
    
    def __init__(self, db_tool=None):
        """Initialize common tools with optional shared db_tool"""
        # Use shared db_tool if provided, otherwise create new one
        if db_tool is not None:
            self.db_tool = db_tool
            print("✅ Using SHARED database connection")
        else:
            self.db_tool = DirectDatabaseTool()
            print("🆕 Created NEW database connection")
        
        self.query_builder = SmartQueryBuilder(use_direct_db=True)
        self.story_agent = StoryAgentSummary()
        
    @abstractmethod
    def execute(self, user_query: str, enhanced_context: Optional[Dict] = None, session_id: str = "") -> Dict[str, Any]:
        """
        Execute workflow
        
        Args:
            user_query: User's query string
            enhanced_context: Enhanced context from follow-up detection
            session_id: Session identifier for logging
            
        Returns:
            Dict with response, status, and metadata
        """
        pass
    
    def _create_success_response(self, narrative: str, metadata: Dict = None) -> Dict[str, Any]:
        """Create standardized success response"""
        return {
            "response": narrative,
            "status": "success",
            "metadata": metadata or {}
        }
    
    def _create_error_response(self, error_message: str, error_type: str = "execution_error") -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "response": f"❌ {error_message}",
            "status": "error",
            "error_type": error_type,
            "metadata": {}
        }
    
    def _extract_location_simple(self, entities: Dict) -> str:
        """Extract location from entities for narrative"""
        geo_entities = entities.get('geographic', [])
        if geo_entities:
            return geo_entities[0].get('value', 'lokasi yang diminta')
        return "lokasi yang diminta"
    
    def _extract_time_simple(self, entities: Dict) -> str:
        """Extract time period from entities for narrative"""
        temporal_entities = entities.get('temporal', [])
        if temporal_entities:
            value = temporal_entities[0].get('value', '').lower()
            if 'week' in value and 'interval' in value:
                return "minggu lalu"
            elif 'week' in value:
                return "minggu ini"
            elif 'month' in value and 'interval' in value:
                return "bulan lalu"
            elif 'month' in value:
                return "bulan ini"
            elif 'current_date' in value and 'interval' in value:
                if 'day' in value:
                    return "kemarin"
                return "periode lalu"
        return "periode yang diminta"
    
    def _log_workflow_execution(self, session_id: str, workflow_name: str, user_query: str, success: bool):
        """Log workflow execution for debugging"""
        status_emoji = "✅" if success else "❌"
        print(f"{status_emoji} [{session_id}] {workflow_name} - {user_query[:50]}...")
    
    def _validate_query_result(self, result) -> bool:
        """Validate query execution result"""
        try:
            # ✅ FIX: Handle tuple or other types
            if not isinstance(result, dict):
                print(f"🔧 _validate_query_result: Expected dict, got {type(result)}")
                return False
            
            # Check if execution_result exists and is dict
            if "execution_result" not in result:
                print("🔧 _validate_query_result: Missing 'execution_result' key")
                return False
                
            execution_result = result["execution_result"]
            if not isinstance(execution_result, dict):
                print(f"🔧 _validate_query_result: execution_result is {type(execution_result)}, expected dict")
                return False
                
            # Check if success key exists
            if "success" not in execution_result:
                print("🔧 _validate_query_result: Missing 'success' key in execution_result")
                return False
                
            print("✅ _validate_query_result: All checks passed")
            return True
            
        except Exception as e:
            print(f"❌ _validate_query_result error: {e}")
            return False