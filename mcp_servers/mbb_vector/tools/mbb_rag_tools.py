from typing import Dict, Any
from ..services.mbb_rag_service import MBBRAGService
from .mbb_search_tools import MBBSearchTools
from shared.utils.logger import log

class MBBRAGTools:
    def __init__(self):
        self.rag_service = MBBRAGService()
        self.search_tools = MBBSearchTools()
    
    async def initialize(self):
        """Initialize MBB RAG tools"""
        rag_init = await self.rag_service.initialize()
        search_init = await self.search_tools.initialize()
        return rag_init and search_init
    
    async def add_mbb_knowledge(self, title: str, content: str, category: str = "general_mobile") -> Dict[str, Any]:
        """Add MBB knowledge document"""
        try:
            success = await self.rag_service.add_mbb_knowledge(title, content, category)
            return {
                "success": success,
                "message": f"Knowledge '{title}' added successfully" if success else "Failed to add knowledge",
                "title": title,
                "category": category
            }
        except Exception as e:
            log.error(f"Failed to add MBB knowledge: {e}")
            return {"success": False, "error": str(e)}
    
    async def upload_excel_knowledge(self, file_path: str = None, file_content: bytes = None, filename: str = None) -> Dict[str, Any]:
        """Upload and process Excel knowledge file"""
        try:
            if file_path:
                return await self.search_tools.process_excel_knowledge(file_path=file_path, filename=filename)
            elif file_content:
                return await self.search_tools.process_excel_knowledge(file_content=file_content, filename=filename)
            else:
                return {"success": False, "error": "Either file_path or file_content required"}
        except Exception as e:
            log.error(f"Excel upload failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def search_mbb_parameters(self, query: str, parameter_name: str = None, scenario: str = None, max_results: int = 5) -> Dict[str, Any]:
        """Search MBB parameters with optional filters"""
        try:
            if parameter_name:
                return await self.search_tools.search_4g_parameters(
                    parameter_name=parameter_name,
                    scenario=scenario
                )
            elif scenario:
                return await self.search_tools.search_by_scenario(scenario)
            else:
                return await self.search_tools.search_mbb_knowledge(query)
        except Exception as e:
            log.error(f"MBB parameter search failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_optimization_recommendations(self, parameter_name: str, current_value: str = None) -> Dict[str, Any]:
        """Get parameter optimization recommendations"""
        try:
            return await self.search_tools.get_parameter_recommendations(parameter_name, current_value)
        except Exception as e:
            log.error(f"Optimization recommendations failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_mbb_stats(self) -> Dict[str, Any]:
        """Get MBB knowledge base statistics"""
        try:
            stats = await self.rag_service.vector_store.get_collection_stats()
            return {
                "success": True,
                "statistics": stats
            }
        except Exception as e:
            log.error(f"Failed to get MBB stats: {e}")
            return {"success": False, "error": str(e)}