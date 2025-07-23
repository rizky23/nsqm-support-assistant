from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from .vector_store import VectorStoreFactory
from .embeddings import EmbeddingService
from shared.utils.logger import log

class RAGService:
    def __init__(self):
        self.vector_store = None
        self.embedding_service = EmbeddingService()
    
    async def initialize(self):
        """Initialize RAG service components"""
        try:
            # Initialize vector store
            self.vector_store = await VectorStoreFactory.create_vector_store()
            
            # Initialize embedding service
            await self.embedding_service.initialize()
            
            log.info("RAG Service initialized successfully")
            return True
            
        except Exception as e:
            log.error(f"Failed to initialize RAG service: {e}")
            return False
    
    async def add_telco_analysis(self, analysis_data: Dict[str, Any]) -> bool:
        """Add telco analysis results to knowledge base"""
        try:
            # Extract relevant information for vectorization
            msisdn = analysis_data.get("msisdn", "unknown")
            analysis = analysis_data.get("analysis", {})
            insights = analysis.get("insights", [])
            recommendations = analysis.get("recommendations", [])
            metrics = analysis.get("metrics", {})
            
            # Create document text from analysis
            document_text = f"""
            MSISDN: {msisdn}
            Analysis Date: {datetime.now().isoformat()}
            
            Key Insights:
            {chr(10).join(f"- {insight}" for insight in insights)}
            
            Recommendations:
            {chr(10).join(f"- {rec}" for rec in recommendations)}
            
            Key Metrics:
            {json.dumps(metrics, indent=2)}
            """
            
            # Metadata for filtering and retrieval
            metadata = {
                "msisdn": msisdn,
                "analysis_type": analysis.get("analysis_type", "comprehensive"),
                "timestamp": datetime.now().isoformat(),
                "metrics": json.dumps(metrics),
                "insight_count": len(insights),
                "recommendation_count": len(recommendations)
            }
            
            # Generate unique ID
            doc_id = f"analysis_{msisdn}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Add to vector store
            success = await self.vector_store.add_documents(
                documents=[document_text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            if success:
                log.info(f"Added analysis for {msisdn} to knowledge base")
            
            return success
            
        except Exception as e:
            log.error(f"Failed to add telco analysis: {e}")
            return False
    
    async def search_similar_cases(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for similar telco cases and issues"""
        try:
            results = await self.vector_store.search(query, n_results)
            
            # Enhance results with structured information
            enhanced_results = []
            for result in results:
                metadata = result.get("metadata", {})
                
                enhanced_result = {
                    "relevance_score": result.get("relevance_score", 0),
                    "msisdn": metadata.get("msisdn", "unknown"),
                    "analysis_type": metadata.get("analysis_type", "unknown"),
                    "timestamp": metadata.get("timestamp", ""),
                    "insight_count": metadata.get("insight_count", 0),
                    "recommendation_count": metadata.get("recommendation_count", 0),
                    "document_snippet": result.get("document", "")[:500] + "..." if len(result.get("document", "")) > 500 else result.get("document", ""),
                    "full_document": result.get("document", "")
                }
                
                enhanced_results.append(enhanced_result)
            
            return enhanced_results
            
        except Exception as e:
            log.error(f"Search failed: {e}")
            return []
    
    async def get_recommendations_for_issue(self, issue_description: str) -> Dict[str, Any]:
        """Get recommendations based on similar historical issues"""
        try:
            # Search for similar cases
            similar_cases = await self.search_similar_cases(issue_description, n_results=3)
            
            if not similar_cases:
                return {
                    "success": False,
                    "message": "No similar cases found in knowledge base"
                }
            
            # Extract recommendations from similar cases
            all_recommendations = []
            case_summaries = []
            
            for case in similar_cases:
                # Parse recommendations from document
                doc = case["full_document"]
                if "Recommendations:" in doc:
                    rec_section = doc.split("Recommendations:")[1]
                    if "Key Metrics:" in rec_section:
                        rec_section = rec_section.split("Key Metrics:")[0]
                    
                    recommendations = [line.strip("- ").strip() for line in rec_section.split("\n") if line.strip().startswith("-")]
                    all_recommendations.extend(recommendations)
                
                case_summaries.append({
                    "msisdn": case["msisdn"],
                    "relevance": case["relevance_score"],
                    "timestamp": case["timestamp"]
                })
            
            # Remove duplicates and rank recommendations
            unique_recommendations = list(set(all_recommendations))
            
            return {
                "success": True,
                "issue_query": issue_description,
                "similar_cases_found": len(similar_cases),
                "recommendations": unique_recommendations[:5],  # Top 5 recommendations
                "similar_cases": case_summaries,
                "confidence": similar_cases[0]["relevance_score"] if similar_cases else 0
            }
            
        except Exception as e:
            log.error(f"Failed to get recommendations: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def add_knowledge_document(self, title: str, content: str, doc_type: str = "general") -> bool:
        """Add general knowledge document to the knowledge base"""
        try:
            metadata = {
                "title": title,
                "doc_type": doc_type,
                "timestamp": datetime.now().isoformat(),
                "content_length": len(content)
            }
            
            doc_id = f"doc_{doc_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            success = await self.vector_store.add_documents(
                documents=[f"Title: {title}\n\n{content}"],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            if success:
                log.info(f"Added knowledge document: {title}")
            
            return success
            
        except Exception as e:
            log.error(f"Failed to add knowledge document: {e}")
            return False