# 2. workflows/knowledge_workflow.py  
from typing import Dict, Any, Optional
from workflows.base_workflow import BaseWorkflow
from knowledge.rag_tool import RAGTool

class KnowledgeWorkflow(BaseWorkflow):
    """Workflow for handling knowledge-based queries using RAG"""
    
    def __init__(self, db_tool=None):
        """Initialize KnowledgeWorkflow - doesn't need db_tool but accepts for consistency"""
        super().__init__(db_tool)
        
        try:
            self.rag_tool = RAGTool()
            print("✅ KnowledgeWorkflow initialized with RAG")
        except Exception as e:
            print(f"❌ RAG initialization failed: {str(e)}")
            self.rag_tool = None
    
    def execute(self, user_query: str, enhanced_context: Optional[Dict] = None, session_id: str = "") -> Dict[str, Any]:
        """
        Execute knowledge workflow using RAG
        
        Handles:
        - Technical troubleshooting questions
        - Policy and procedure queries  
        - SOP knowledge requests
        - Best practices guidance
        """
        try:
            self._log_workflow_execution(session_id, "KnowledgeWorkflow", user_query, True)
            
            if not self.rag_tool:
                return self._create_error_response("RAG tool not available")
            
            # Check if knowledge base has content
            stats = self.rag_tool.get_knowledge_stats()
            if stats.get("total_documents", 0) == 0:
                return self._create_success_response(
                    "📚 **Knowledge base kosong.** Silakan upload dokumen terlebih dahulu melalui endpoint `/knowledge/upload`.",
                    metadata={"stats": stats}
                )
            
            # Search for relevant knowledge
            relevant_docs = self.rag_tool.search_knowledge(user_query, n_results=3)
            
            if not relevant_docs:
                return self._create_success_response(
                    f"🔍 **Tidak menemukan informasi yang relevan untuk:** \"{user_query}\"\n\nSilakan coba dengan kata kunci yang berbeda atau hubungi supervisor untuk informasi lebih lanjut.",
                    metadata={
                        "search_results": 0,
                        "query": user_query
                    }
                )
            
            # Filter results by minimum similarity threshold
            filtered_docs = [doc for doc in relevant_docs if doc['similarity'] > -1.0]
            
            if not filtered_docs:
                return self._create_success_response(
                    f"🔍 **Informasi ditemukan tapi kurang relevan untuk:** \"{user_query}\"\n\nCoba gunakan kata kunci yang lebih spesifik atau hubungi technical support.",
                    metadata={
                        "search_results": len(relevant_docs),
                        "filtered_results": 0,
                        "min_similarity": 0.3
                    }
                )
            
            # Generate RAG answer
            rag_answer = self.rag_tool.generate_rag_answer(user_query, filtered_docs)
            
            return self._create_success_response(
                rag_answer,
                metadata={
                    "search_results": len(relevant_docs),
                    "used_documents": len(filtered_docs),
                    "sources": [doc['metadata'].get('title', 'Unknown') for doc in filtered_docs],
                    "avg_similarity": sum(doc['similarity'] for doc in filtered_docs) / len(filtered_docs),
                    "knowledge_stats": stats
                }
            )
            
        except Exception as e:
            self._log_workflow_execution(session_id, "KnowledgeWorkflow", user_query, False)
            return self._create_error_response(f"Knowledge workflow execution failed: {str(e)}")
    
    def is_knowledge_query(self, user_query: str) -> bool:
        """Check if query is knowledge-related"""
        knowledge_keywords = [
            # Troubleshooting
            'troubleshoot', 'troubleshooting', 'cara mengatasi', 'cara handle', 'solusi',
            'langkah', 'prosedur', 'panduan', 'guide',
            
            # Technical  
            'parameter', 'rsrp', 'sinr', 'signal', 'coverage', 'antenna',
            'carrier aggregation', 'handover', 'optimization',
            
            # Policy/SOP
            'sop', 'policy', 'kebijakan', 'aturan', 'standar', 'procedure',
            'eskalasi', 'escalation', 'prioritas', 'priority',
            
            # Knowledge requests
            'bagaimana', 'gimana', 'cara', 'tutorial', 'manual',
            'best practice', 'best practices', 'rekomendasi'
        ]
        
        query_lower = user_query.lower()
        return any(keyword in query_lower for keyword in knowledge_keywords)