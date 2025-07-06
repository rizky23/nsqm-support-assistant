# enhanced_query_processor.py
import yaml
import re
import json
from typing import Dict, Any, List, Optional

class EnhancedQueryProcessor:
    def __init__(self):
        """Initialize with knowledge base and database support"""
        self.semantic_mapping = self.load_semantic_mapping()
        self.table_name = self.semantic_mapping.get('table_name', 'inap_ticketing_customer_complain')
        
        # Initialize knowledge base (ChromaDB)
        try:
            from tools.knowledge_base_tool import KnowledgeBaseTool
            self.kb_tool = KnowledgeBaseTool()
            self.has_knowledge_base = True
            print("✅ Knowledge Base Tool (ChromaDB) initialized")
        except ImportError:
            self.has_knowledge_base = False
            print("⚠️ Knowledge Base Tool not available")
        
        # Initialize database tool
        from tools.direct_database_tool import DirectDatabaseTool
        self.db_tool = DirectDatabaseTool()
        print("✅ Direct Database Tool initialized")
        
        # Similarity threshold for knowledge base relevance
        self.kb_similarity_threshold = 0.7  # Adjustable threshold
    
    def load_semantic_mapping(self):
        """Load semantic mapping from YAML file"""
        try:
            with open('config/semantic_mapping.yaml', 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                print("[LOG] semantic_mapping.yaml loaded successfully.")
                return data
        except Exception as e:
            print(f"Error loading semantic mapping: {e}")
            return {}

    def check_knowledge_base_relevance(self, user_query: str) -> Optional[Dict]:
        """Check if ChromaDB has relevant documents for the query"""
        if not self.has_knowledge_base:
            return None
        
        try:
            print(f"🔍 Checking ChromaDB relevance for: {user_query}")
            
            # Search ChromaDB with similarity scoring
            result = self.kb_tool.search(user_query, top_k=3)
            
            if result and result.get('success'):
                documents = result.get('data', [])
                
                if documents:
                    # Check if any document has high similarity
                    max_similarity = 0
                    best_result = None
                    
                    for doc in documents:
                        similarity = doc.get('similarity_score', 0)
                        if similarity > max_similarity:
                            max_similarity = similarity
                            best_result = doc
                    
                    print(f"📊 Best similarity score: {max_similarity}")
                    
                    if max_similarity >= self.kb_similarity_threshold:
                        print(f"✅ High relevance found in knowledge base (score: {max_similarity})")
                        return {
                            'success': True,
                            'source': 'knowledge_base',
                            'similarity_score': max_similarity,
                            'data': documents,
                            'best_match': best_result,
                            'answer': result.get('answer', ''),
                            'references': result.get('references', [])
                        }
                    else:
                        print(f"📉 Low relevance in knowledge base (score: {max_similarity})")
                        return None
                else:
                    print("📭 No documents found in knowledge base")
                    return None
            else:
                print("❌ ChromaDB search failed")
                return None
                
        except Exception as e:
            print(f"❌ Knowledge base relevance check error: {str(e)}")
            return None

    def has_specific_database_patterns(self, user_query: str) -> bool:
        """Check for specific patterns that should definitely go to database"""
        query_lower = user_query.lower()
        
        # Specific ID patterns that are definitely database queries
        database_patterns = [
            r'cc-\d{8}-\d{8}',  # Ticket ID
            r'\b628\d{8,12}\b',  # MSISDN
            r'\b08\d{8,12}\b',   # Local MSISDN
        ]
        
        for pattern in database_patterns:
            if re.search(pattern, query_lower):
                print(f"🎯 Specific database pattern detected: {pattern}")
                return True
        
        return False

    def search_database(self, user_query: str, enhanced_context: Dict = None) -> Dict:
        """Search in database using existing SmartQueryBuilder logic"""
        try:
            print(f"🗄️ Searching database for: {user_query}")
            
            # Use existing SmartQueryBuilder logic
            from tools.smart_query_builder import SmartQueryBuilder
            query_builder = SmartQueryBuilder()
            
            result = query_builder.build_and_execute_with_narrative(
                user_query, 
                enhanced_context=enhanced_context
            )
            
            result['source'] = 'database'
            return result
            
        except Exception as e:
            print(f"❌ Database search error: {str(e)}")
            return {
                'success': False,
                'source': 'database',
                'error': str(e)
            }

    def process_query(self, user_query: str, enhanced_context: Dict = None) -> Dict:
        """Main query processing with intelligent ChromaDB-first routing"""
        print(f"🚀 Processing query: {user_query}")
        
        # Step 1: Check for specific database patterns first
        if self.has_specific_database_patterns(user_query):
            print("🗄️ Specific database pattern detected, going straight to database")
            return self.search_database(user_query, enhanced_context)
        
        # Step 2: Check ChromaDB relevance for all other queries
        kb_result = self.check_knowledge_base_relevance(user_query)
        
        if kb_result and kb_result.get('success'):
            print(f"📚 Using knowledge base (similarity: {kb_result.get('similarity_score', 0)})")
            return kb_result
        else:
            print("🗄️ No relevant knowledge found, using database")
            return self.search_database(user_query, enhanced_context)

    def format_response(self, result: Dict) -> str:
        """Format response based on source"""
        if not result:
            return "❌ Tidak dapat memproses query."
        
        source = result.get('source', 'unknown')
        
        if source == 'knowledge_base':
            return self.format_knowledge_response(result)
        elif source == 'database':
            return self.format_database_response(result)
        else:
            return f"📊 Response: {result}"

    def format_knowledge_response(self, kb_result: Dict) -> str:
        """Format knowledge base response"""
        if not kb_result or not kb_result.get('success'):
            return "❌ Informasi tidak ditemukan di knowledge base."
        
        answer = kb_result.get('answer', '')
        similarity_score = kb_result.get('similarity_score', 0)
        references = kb_result.get('references', [])
        
        response = f"📚 **Knowledge Base Response** (Confidence: {similarity_score:.2f})\n\n"
        
        if answer:
            response += f"{answer}\n\n"
        
        if references:
            response += "📖 **Sumber:**\n"
            for ref in references[:3]:  # Show max 3 references
                doc_name = ref.get('document', 'Unknown Document')
                page = ref.get('page', 'N/A')
                response += f"• {doc_name} (Page {page})\n"
        
        return response

    def format_database_response(self, db_result: Dict) -> str:
        """Format database response"""
        if not db_result:
            return "❌ Tidak ada data ditemukan."
        
        if db_result.get('success') == False:
            return f"❌ Database error: {db_result.get('error', 'Unknown error')}"
        
        # Use existing narrative if available
        narrative = db_result.get('narrative', '')
        if narrative:
            return narrative
        
        # Fallback formatting
        data = db_result.get('execution_result', {}).get('data', [])
        if data:
            return f"🗄️ **Database Response**\n\nDitemukan {len(data)} record."
        else:
            return "📭 Tidak ada data ditemukan di database."

    def update_similarity_threshold(self, new_threshold: float):
        """Update similarity threshold for knowledge base relevance"""
        if 0.0 <= new_threshold <= 1.0:
            self.kb_similarity_threshold = new_threshold
            print(f"📊 Similarity threshold updated to: {new_threshold}")
        else:
            print("❌ Threshold must be between 0.0 and 1.0")

# Usage example
def main():
    processor = EnhancedQueryProcessor()
    
    # Test queries
    test_queries = [
        "apa itu DSC?",  # Should go to knowledge base
        "CC-20250625-00000141",  # Should go to database
        "keluhan di Jakarta minggu ini",  # Should go to database
        "bagaimana cara menggunakan Digital SmartCare?"  # Should check ChromaDB first
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        result = processor.process_query(query)
        formatted_response = processor.format_response(result)
        print(f"Query: {query}")
        print(f"Response: {formatted_response}")

if __name__ == "__main__":
    main()