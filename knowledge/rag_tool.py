# knowledge/rag_tool.py
import chromadb
import os
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import requests

class RAGTool:
    """RAG tool for document knowledge retrieval with external ChromaDB"""
    
    def __init__(self):
        # Get ChromaDB connection details from environment
        chromadb_host = os.getenv('CHROMADB_HOST', 'localhost')
        chromadb_port = int(os.getenv('CHROMADB_PORT', '8000'))
        
        print(f"🔗 Connecting to ChromaDB at {chromadb_host}:{chromadb_port}")
        
        # Connect to external ChromaDB service
        try:
            self.chroma_client = chromadb.HttpClient(
                host=chromadb_host,
                port=chromadb_port
            )
            
            # Test connection
            self.chroma_client.heartbeat()
            print(f"✅ Connected to ChromaDB at {chromadb_host}:{chromadb_port}")
            
        except Exception as e:
            print(f"❌ Failed to connect to ChromaDB: {e}")
            # Fallback to local ChromaDB for development
            self.chroma_client = chromadb.PersistentClient(path="./chromadb_knowledge")
            print("⚠️ Using local ChromaDB as fallback")
        
        self.collection_name = "complaint_knowledge"
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Get or create collection
        try:
            self.collection = self.chroma_client.get_collection(name=self.collection_name)
            print(f"✅ Connected to existing knowledge collection: {self.collection.count()} documents")
        except:
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"description": "Complaint handling knowledge base"}
            )
            print("🆕 Created new knowledge collection")
    
    def __init__(self):
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(path="./chromadb_knowledge")
        self.collection_name = "complaint_knowledge"
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Get or create collection
        try:
            self.collection = self.chroma_client.get_collection(name=self.collection_name)
            print(f"✅ Connected to existing knowledge collection: {self.collection.count()} documents")
        except:
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"description": "Complaint handling knowledge base"}
            )
            print("🆕 Created new knowledge collection")
    
    def add_document(self, content: str, metadata: Dict[str, Any]) -> None:
        """Add document to knowledge base"""
        try:
            # Generate embedding
            embedding = self.embedding_model.encode(content).tolist()
            
            # Generate unique ID
            doc_id = f"doc_{hash(content[:100])}_{len(content)}"
            
            # Add to collection
            self.collection.add(
                documents=[content],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            print(f"✅ Added document: {metadata.get('title', 'Untitled')}")
            
        except Exception as e:
            print(f"❌ Error adding document: {str(e)}")
    
    def search_knowledge(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Search for relevant knowledge"""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Search in collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'similarity': 1 - results['distances'][0][i]  # Convert distance to similarity
                })
            
            print(f"🔍 Found {len(formatted_results)} relevant documents for: {query[:50]}...")
            return formatted_results
            
        except Exception as e:
            print(f"❌ Error searching knowledge: {str(e)}")
            return []
    
    def generate_rag_answer(self, user_query: str, relevant_docs: List[Dict]) -> str:
        """Generate answer using LLM with RAG context"""
        
        # Build context from relevant documents
        context_parts = []
        for i, doc in enumerate(relevant_docs[:3], 1):
            title = doc['metadata'].get('title', f'Document {i}')
            content = doc['content'][:500]  # Limit content length
            similarity = doc['similarity']
            
            context_parts.append(f"**Dokumen {i}: {title}** (Relevance: {similarity:.2f})\n{content}\n")
        
        context = "\n---\n".join(context_parts)
        
        # Create prompt for LLM
        prompt = f"""
Anda adalah AI assistant untuk customer service Telkomsel. Jawab pertanyaan berdasarkan dokumen knowledge base yang disediakan.

KNOWLEDGE BASE CONTEXT:
{context}

PERTANYAAN USER: "{user_query}"

INSTRUCTIONS:
- Jawab SELALU dalam Bahasa Indonesia
- Jawab berdasarkan informasi dari dokumen yang relevan
- Jika tidak ada informasi yang cukup, katakan "Informasi tidak tersedia dalam knowledge base"
- Berikan jawaban yang praktis dan mudah dipahami
- Format dengan emoji dan struktur yang jelas
- Sebutkan sumber dokumen jika membantu
- Jangan gunakan bahasa Inggris kecuali untuk istilah teknis

JAWABAN (BAHASA INDONESIA):
"""

        try:
            # Call Ollama LLM
            response = requests.post("http://localhost:11434/api/generate", 
                json={
                    "model": "llama3",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3}
                })
            
            if response.status_code == 200:
                llm_response = response.json()["response"].strip()
                
                # Add source information
                sources = [doc['metadata'].get('title', 'Unknown') for doc in relevant_docs[:3]]
                source_text = f"\n\n📚 **Sumber:** {', '.join(sources)}"
                
                return llm_response + source_text
            else:
                return "❌ Error generating response from LLM"
                
        except Exception as e:
            print(f"❌ LLM generation error: {str(e)}")
            return f"❌ Error generating answer: {str(e)}"
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "embedding_model": "all-MiniLM-L6-v2",
                "status": "active" if count > 0 else "empty"
            }
        except Exception as e:
            return {
                "error": str(e),
                "status": "error"
            }