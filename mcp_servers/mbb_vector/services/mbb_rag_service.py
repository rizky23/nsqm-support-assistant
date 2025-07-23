from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from .mbb_vector_store import MBBVectorStore
from shared.utils.logger import log

class MBBRAGService:
    def __init__(self):
        self.vector_store = MBBVectorStore()
        # Remove embedding service - ChromaDB handles embeddings automatically
    
    async def initialize(self):
        """Initialize MBB RAG service components"""
        try:
            # Initialize vector store only
            await self.vector_store.initialize()
            
            log.info("MBB RAG Service initialized successfully")
            return True
            
        except Exception as e:
            log.error(f"Failed to initialize MBB RAG service: {e}")
            return False
    
    async def add_mbb_knowledge(self, title: str, content: str, category: str = "general_mobile") -> bool:
        """Add MBB knowledge document"""
        try:
            metadata = {
                "title": title,
                "category": category,
                "domain": "mobile_broadband",
                "timestamp": datetime.now().isoformat(),
                "content_length": len(content)
            }
            
            doc_id = f"mbb_{category}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            success = await self.vector_store.add_documents(
                documents=[f"Title: {title}\n\n{content}"],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            if success:
                log.info(f"Added MBB knowledge: {title}")
            
            return success
            
        except Exception as e:
            log.error(f"Failed to add MBB knowledge: {e}")
            return False
    
    async def search_mbb_knowledge(self, query: str, category: Optional[str] = None, max_results: int = 5) -> Dict[str, Any]:
        """Search MBB knowledge base"""
        try:
            filters = {"domain": "mobile_broadband"}
            if category:
                filters["category"] = category
            
            results = await self.vector_store.search(
                query=query,
                n_results=max_results,
                filters=filters
            )
            
            return {
                "success": True,
                "query": query,
                "results_found": len(results),
                "results": results,
                "domain": "Mobile Broadband"
            }
            
        except Exception as e:
            log.error(f"MBB knowledge search failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }