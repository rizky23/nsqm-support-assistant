# memory/session_manager.py
import json
import time
from typing import Dict, List, Any
# import chromadb
# from tools.chromadb_tool import ChromaDBTool

class SessionManager:
    """Session management for conversation memory with ChromaDB"""
    
    def __init__(self):
        # TEMPORARY DISABLE ChromaDB
        self.chroma_tool = None
        self.sessions = {}  # Use in-memory only
        self.max_session_age = 3600
        print("✅ SessionManager initialized (in-memory mode)")

    def get_session(self, session_id: str) -> Dict:
        """Get session data with cleanup"""
        if self.chroma_tool:
            # Use ChromaDB
            try:
                results = self.chroma_tool.search_documents(
                    query=f"session_id:{session_id}",
                    collection_name=self.collection_name,
                    n_results=1
                )
                
                if results and len(results.get('documents', [])) > 0:
                    session_data = json.loads(results['documents'][0])
                    # Check if expired
                    if time.time() - session_data.get("last_activity", 0) > self.max_session_age:
                        return self._create_new_session(session_id)
                    return session_data
                else:
                    return self._create_new_session(session_id)
            except Exception as e:
                print(f"ChromaDB session error: {e}")
                return self._create_new_session(session_id)
        else:
            # Fallback to in-memory
            self._cleanup_expired_sessions()
            
            if session_id not in self.sessions:
                self.sessions[session_id] = self._create_new_session(session_id)
            
            return self.sessions[session_id]
    
    def _create_new_session(self, session_id: str) -> Dict:
        """Create new session data"""
        return {
            "session_id": session_id,
            "created_at": time.time(),
            "last_activity": time.time(),
            "conversation_history": [],
            "context": {},
            "last_query_type": None,
            "last_response": None
        }
    
    def save_interaction(self, session_id: str, query: str, response: str, query_type: str, entities=None):
        """Save query-response pair to session"""
        session = self.get_session(session_id)
        
        interaction = {
            "timestamp": time.time(),
            "query": query,
            "response": response,
            "query_type": query_type,
            "entities": entities or {}  # Store entities for context
        }
        
        session["conversation_history"].append(interaction)
        session["last_activity"] = time.time()
        session["last_query_type"] = query_type
        session["last_response"] = response
        
        # Keep only last 10 interactions
        if len(session["conversation_history"]) > 10:
            session["conversation_history"] = session["conversation_history"][-10:]
        
        # Save to storage
        if self.chroma_tool:
            # Save to ChromaDB
            try:
                self.chroma_tool.add_documents(
                    documents=[json.dumps(session)],
                    metadatas=[{"session_id": session_id, "last_activity": session["last_activity"]}],
                    ids=[f"session_{session_id}"],
                    collection_name=self.collection_name
                )
            except Exception as e:
                print(f"ChromaDB save error: {e}")
        else:
            # Save to in-memory
            self.sessions[session_id] = session
    
    def get_context_for_followup(self, session_id: str, current_query: str) -> Dict:
        """Get relevant context for follow-up queries"""
        session = self.get_session(session_id)
        
        # Enhanced follow-up patterns
        followup_patterns = [
            'contoh', 'contohnya', 'yang belum', 'yg belum', 'yang masih', 'yg masih',  # ✅ ADD: contohnya
            'detail', 'jelaskan', 'bagaimana', 'yang mana', 'tersebut', 'itu', 'tadi', 
            'diatas', 'belum solve', 'masih pending', 'salah satu', 'dari sana',
            'lokasi sama', 'tempat itu', 'disitu', 'yang tadi', 'seperti apa',
            'gimana', 'mana aja', 'ada yang', 'bisa kasih', 'tolong tunjukkan'
        ]
        
        is_followup = any(pattern in current_query.lower() for pattern in followup_patterns)
        
        if is_followup and session["conversation_history"]:
            last_interaction = session["conversation_history"][-1]
            return {
                "is_followup": True,
                "previous_query": last_interaction["query"],
                "previous_response": last_interaction["response"],
                "previous_query_type": last_interaction["query_type"],
                "previous_entities": last_interaction.get("entities", {})
            }
        
        return {"is_followup": False}
    
    def get_last_context(self, session_id: str) -> Dict:
        """Get context from last interaction for follow-up"""
        session = self.get_session(session_id)
        
        if session["conversation_history"]:
            last_interaction = session["conversation_history"][-1]
            entities = last_interaction.get("entities", {})
            
            # Extract useful context
            context = {}
            
            # Geographic context
            if "geographic" in entities:
                geo_entity = entities["geographic"][0] if entities["geographic"] else {}
                context["last_location"] = geo_entity.get("value", "")
            
            # Temporal context  
            if "temporal" in entities:
                temp_entity = entities["temporal"][0] if entities["temporal"] else {}
                context["last_timeframe"] = temp_entity.get("value", "")
            
            # Query type context
            context["last_workflow"] = last_interaction.get("query_type", "")
            context["last_query"] = last_interaction.get("query", "")
            
            return context
        
        return {}
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions"""
        if self.chroma_tool:
            # ChromaDB cleanup would be more complex, skip for now
            # Can implement periodic cleanup job if needed
            pass
        else:
            # In-memory cleanup
            current_time = time.time()
            expired_sessions = [
                sid for sid, data in self.sessions.items()
                if current_time - data["last_activity"] > self.max_session_age
            ]
            
            for sid in expired_sessions:
                del self.sessions[sid]
    
    def is_followup_query(self, query: str) -> bool:
        """Simple check if query looks like follow-up"""
        followup_indicators = [
            'yang', 'tersebut', 'itu', 'tadi', 'diatas', 'sebelumnya',
            'contoh', 'detail', 'jelaskan', 'bagaimana', 'dari sana',
            'belum solve', 'masih pending', 'yang masih', 'yang belum'
        ]
        
        return any(indicator in query.lower() for indicator in followup_indicators)