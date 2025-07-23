import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
from shared.utils.logger import log
from ..config.settings import mbb_settings

class MBBVectorStore:
    def __init__(self):
        self.client = None
        self.collection = None
        self.collection_name = mbb_settings.collection_name
    
    async def initialize(self):
        """Initialize ChromaDB connection for MBB"""
        try:
            if mbb_settings.chroma_host == "localhost":
                self.client = chromadb.PersistentClient(path="./mbb_chroma_db")
            else:
                self.client = chromadb.HttpClient(
                    host=mbb_settings.chroma_host,
                    port=mbb_settings.chroma_port
                )
            
            # Get or create MBB collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Mobile Broadband knowledge and documents"}
            )
            
            log.info(f"MBB ChromaDB initialized with collection: {self.collection_name}")
            return True
            
        except Exception as e:
            log.error(f"Failed to initialize MBB ChromaDB: {e}")
            return False
    
    async def add_documents(self, documents: List[str], metadatas: List[Dict], ids: List[str]) -> bool:
        """Add MBB documents to vector store"""
        try:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            log.info(f"Added {len(documents)} MBB documents to vector store")
            return True
            
        except Exception as e:
            log.error(f"Failed to add MBB documents: {e}")
            return False
    
    async def search(self, query: str, n_results: int = 5, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Search for similar MBB documents"""
        try:
            where_clause = filters if filters else {}
            
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                    "relevance_score": 1 - results["distances"][0][i]
                })
            
            return formatted_results
            
        except Exception as e:
            log.error(f"MBB search failed: {e}")
            return []
    
    async def search_device_compatibility(self, device_model: str, query: str) -> List[Dict[str, Any]]:
        """Search for device compatibility information"""
        try:
            # Search with device model filter
            device_query = f"{device_model} {query}"
            
            results = await self.search(
                query=device_query,
                n_results=3,
                filters={"category": "device_compatibility"}
            )
            
            # If no device-specific results, search general compatibility
            if not results:
                results = await self.search(
                    query=f"mobile device {query}",
                    n_results=3,
                    filters={"category": "general_mobile"}
                )
            
            return results
            
        except Exception as e:
            log.error(f"Device compatibility search failed: {e}")
            return []
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get MBB collection statistics"""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "domain": "Mobile Broadband"
            }
        except Exception as e:
            log.error(f"Failed to get MBB stats: {e}")
            return {"error": str(e)}