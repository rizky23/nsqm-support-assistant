import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from shared.utils.config import settings
from shared.utils.logger import log

class VectorStoreInterface(ABC):
    """Abstract interface for vector stores"""
    
    @abstractmethod
    async def add_documents(self, documents: List[str], metadatas: List[Dict], ids: List[str]) -> bool:
        pass
    
    @abstractmethod
    async def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def delete_documents(self, ids: List[str]) -> bool:
        pass

class ChromaDBStore(VectorStoreInterface):
    def __init__(self):
        self.client = None
        self.collection = None
        self.collection_name = "telecom_documents"
    
    async def initialize(self):
        """Initialize ChromaDB connection"""
        try:
            if settings.chroma_host == "localhost":
                # Local persistent storage
                self.client = chromadb.PersistentClient(path="./chroma_db")
            else:
                # Remote ChromaDB server
                self.client = chromadb.HttpClient(
                    host=settings.chroma_host,
                    port=settings.chroma_port
                )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Telecom documents and analysis results"}
            )
            
            log.info(f"ChromaDB initialized with collection: {self.collection_name}")
            return True
            
        except Exception as e:
            log.error(f"Failed to initialize ChromaDB: {e}")
            return False
    
    async def add_documents(self, documents: List[str], metadatas: List[Dict], ids: List[str]) -> bool:
        """Add documents to vector store"""
        try:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            log.info(f"Added {len(documents)} documents to vector store")
            return True
            
        except Exception as e:
            log.error(f"Failed to add documents: {e}")
            return False
    
    async def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                    "relevance_score": 1 - results["distances"][0][i]  # Convert distance to similarity
                })
            
            return formatted_results
            
        except Exception as e:
            log.error(f"Search failed: {e}")
            return []
    
    async def delete_documents(self, ids: List[str]) -> bool:
        """Delete documents by IDs"""
        try:
            self.collection.delete(ids=ids)
            log.info(f"Deleted {len(ids)} documents")
            return True
            
        except Exception as e:
            log.error(f"Failed to delete documents: {e}")
            return False
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection_name
            }
        except Exception as e:
            log.error(f"Failed to get stats: {e}")
            return {"error": str(e)}

class VectorStoreFactory:
    """Factory for creating vector store instances"""
    
    @staticmethod
    async def create_vector_store() -> VectorStoreInterface:
        provider = settings.vector_db_provider.lower()
        
        if provider == "chromadb":
            store = ChromaDBStore()
            await store.initialize()
            return store
        else:
            raise ValueError(f"Unsupported vector store provider: {provider}")