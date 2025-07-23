from typing import Dict, Any, List
from ..services.rag_service import RAGService
from shared.utils.logger import log

class RAGTools:
    def __init__(self):
        self.rag_service = RAGService()
    
    async def initialize(self):
        """Initialize RAG tools"""
        return await self.rag_service.initialize()
    
    async def search_knowledge_base(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search the knowledge base for relevant information"""
        try:
            results = await self.rag_service.search_similar_cases(query, max_results)
            
            return {
                "success": True,
                "query": query,
                "results_found": len(results),
                "results": results,
                "best_match": results[0] if results else None
            }
            
        except Exception as e:
            log.error(f"Knowledge base search failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_issue_recommendations(self, issue_description: str) -> Dict[str, Any]:
        """Get recommendations for a specific issue based on historical data"""
        try:
            return await self.rag_service.get_recommendations_for_issue(issue_description)
            
        except Exception as e:
            log.error(f"Failed to get recommendations: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def add_analysis_to_knowledge(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add telco analysis results to the knowledge base"""
        try:
            success = await self.rag_service.add_telco_analysis(analysis_data)
            
            return {
                "success": success,
                "message": "Analysis added to knowledge base" if success else "Failed to add analysis",
                "msisdn": analysis_data.get("msisdn", "unknown")
            }
            
        except Exception as e:
            log.error(f"Failed to add analysis to knowledge base: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def add_document(self, title: str, content: str, doc_type: str = "general") -> Dict[str, Any]:
        """Add a general document to the knowledge base"""
        try:
            success = await self.rag_service.add_knowledge_document(title, content, doc_type)
            
            return {
                "success": success,
                "message": f"Document '{title}' added to knowledge base" if success else "Failed to add document",
                "document_type": doc_type
            }
            
        except Exception as e:
            log.error(f"Failed to add document: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base"""
        try:
            stats = await self.rag_service.vector_store.get_collection_stats()
            
            return {
                "success": True,
                "statistics": stats
            }
            
        except Exception as e:
            log.error(f"Failed to get knowledge base stats: {e}")
            return {
                "success": False,
                "error": str(e)
            }