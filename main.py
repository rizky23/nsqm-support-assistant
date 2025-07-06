# main.py - Flask Entry Point with Direct Database Access
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from crews.simplified_crew import SimplifiedCrew
from memory.session_manager import SessionManager
from tools.direct_database_tool import DirectDatabaseTool
from knowledge.document_processor import DocumentProcessor
from knowledge.rag_tool import RAGTool
import time
import json
import hashlib
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration for Docker
if os.getenv('CLICKHOUSE_HOST'):
    CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', 'localhost')
    CLICKHOUSE_PORT = os.getenv('CLICKHOUSE_PORT', '9443')
    CLICKHOUSE_DB = os.getenv('CLICKHOUSE_DB', 'default')
    CLICKHOUSE_USER = os.getenv('CLICKHOUSE_USER', 'default')
    CLICKHOUSE_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', '')
    CLICKHOUSE_SECURE = os.getenv('CLICKHOUSE_SECURE', 'false')
    
    print(f"🔗 Using ClickHouse: {CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}")

# Configuration
SESSION_CLEANUP_TIME = 3600  # 1 hour in seconds

class DatabaseManager:
    """Singleton Database Manager - 1 connection untuk semua"""
    _instance = None
    _db_tool = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def get_db_tool(self):
        if not self._initialized:
            try:
                # FIX: Use same SSL parameters as manual test
                import clickhouse_connect
                client = clickhouse_connect.get_client(
                    host=os.getenv('CLICKHOUSE_HOST', 'localhost'),
                    port=int(os.getenv('CLICKHOUSE_PORT', 9443)),
                    username=os.getenv('CLICKHOUSE_USER', 'default'),
                    password=os.getenv('CLICKHOUSE_PASSWORD', ''),
                    database=os.getenv('CLICKHOUSE_DB', 'default'),
                    secure=os.getenv('CLICKHOUSE_SECURE', 'false').lower() == 'true',
                    verify=os.getenv('CLICKHOUSE_VERIFY', 'false').lower() == 'true',
                    ca_cert=None  # ← KEY FIX
                )
                
                # Create DirectDatabaseTool with working client
                from tools.direct_database_tool import DirectDatabaseTool
                self._db_tool = DirectDatabaseTool()
                self._db_tool.client = client  # Override with working client
                
                self._initialized = True
                print("✅ SINGLETON: Shared database connection created")
            except Exception as e:
                print(f"❌ SINGLETON: Database connection failed: {e}")
                self._db_tool = None
        return self._db_tool

# Initialize Flask app
app = Flask(__name__)
CORS(app)

simplified_crew = SimplifiedCrew()

# Initialize components
db_manager = DatabaseManager()
db_tool = db_manager.get_db_tool()

if db_tool:
    print("✅ Singleton database tool initialized")
else:
    print("⚠️ Singleton database tool failed")

doc_processor = DocumentProcessor()

# Initialize RAG tool (optional)
try:
    rag_tool = RAGTool()
    print("✅ RAG tool initialized")
except Exception as e:
    print(f"⚠️  RAG tool initialization failed: {str(e)}")
    rag_tool = None

# Initialize SimplifiedCrew
try:
    # Pass shared database tool ke SimplifiedCrew
    simplified_crew = SimplifiedCrew(shared_db_tool=db_tool)
    print("✅ SimplifiedCrew initialized with shared DB connection")
except Exception as e:
    print(f"❌ SimplifiedCrew failed: {e}")
    simplified_crew = None

# Session storage - maps session_id to session data
chat_sessions = {}

def generate_consistent_session_id(messages):
    """Generate session ID yang konsisten berdasarkan first user message"""
    first_user_content = ""
    
    # Cari first user message
    for msg in messages:
        if msg.get('role') == 'user':
            first_user_content = msg.get('content', '')
            break
    
    if first_user_content:
        # Bersihkan content untuk hash yang stabil
        clean_content = first_user_content.strip().lower()[:100]  # Max 100 chars
        today = time.strftime('%Y-%m-%d')  # Tambah date untuk uniqueness
        seed = f"{clean_content}_{today}"
        
        session_hash = hashlib.md5(seed.encode()).hexdigest()[:12]
        return f"session_direct_{session_hash}"
    
    # Fallback jika tidak ada user message
    return f"session_direct_fallback_{int(time.time())}"

def get_or_create_session(session_id, chat_id):
    """Get existing session or create new one"""
    if session_id not in chat_sessions:
        chat_sessions[session_id] = {
            "chat_id": chat_id,
            "created_at": time.time(),
            "history": [], 
            "context": {},
            "message_count": 0
        }
        print(f"[SESSION] New session created: {session_id}")
    else:
        print(f"[SESSION] Existing session found: {session_id}")
    
    session = chat_sessions[session_id]
    session["message_count"] += 1
    session["last_activity"] = time.time()
    
    return session

def store_conversation(session, user_query, response, intent, sql_query=None, entities=None):
    """Store conversation entry in session history"""
    conversation_entry = {
        "message_id": session["message_count"],
        "query": user_query,
        "intent": intent,
        "sql": sql_query or "handled_by_simplified_crew",
        "response": response,
        "timestamp": time.time(),
        "entities": entities or []
    }
    session["history"].append(conversation_entry)

@app.route('/v1/chat/completions', methods=['POST', 'OPTIONS'])
@app.route('/chat/completions', methods=['POST', 'OPTIONS'])
def openai_compatible():
    """Main OpenAI-compatible endpoint with SimplifiedCrew"""
    if request.method == 'OPTIONS':
        response = make_response('', 200)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Session-ID'
        return response
        
    data = request.json or {}
    is_streaming = data.get('stream', False)
    
    messages = data.get('messages', [])
    if not messages:
        return _error_response("No messages provided", is_streaming, 400)
    
    last_message = messages[-1]
    user_query = last_message.get('content', '')
    
    # Enhanced session ID generation
    provided_session_id = (
        request.headers.get('X-Session-ID') or 
        data.get('session_id') or 
        request.headers.get('x-session-id')
    )
    
    if provided_session_id:
        session_id = provided_session_id if provided_session_id.startswith('session_') else f"session_{provided_session_id}"
        chat_id = provided_session_id.replace('session_', '')
    else:
        session_id = generate_consistent_session_id(messages)
        chat_id = session_id.replace('session_direct_', 'direct_')
    
    # Get or create session
    session = get_or_create_session(session_id, chat_id)
    
    try:
        # Check if SimplifiedCrew is available
        if simplified_crew is None:
            return _error_response("SimplifiedCrew not initialized", is_streaming, 500)
        
        # Process with SimplifiedCrew
        crew_input = {
            "user_query": user_query,
            "session_id": session_id,
            "context": session.get("context", {}),
            "chat_history": session.get("history", [])
        }
        
        print(f"DEBUG: About to call execute_query with: {user_query}")
        crew_result = simplified_crew.execute_query(crew_input)
        print(f"DEBUG: crew_result keys: {crew_result.keys()}")
        print(f"DEBUG: crew_result status: {crew_result.get('status')}")
        print(f"DEBUG: crew_result workflow: {crew_result.get('workflow')}")
        
        result = crew_result.get("response", "No response generated")
        status = crew_result.get("status", "unknown")
        workflow = crew_result.get("workflow", "unknown")
        
        print(f"DEBUG: Extracted result preview: {result[:100]}...")
        print(f"DEBUG: Extracted status: {status}")
        print(f"DEBUG: Extracted workflow: {workflow}")
        
        # Handle based on status
        if status in ["off_topic", "off_topic_fallback", "system_inquiry", "system_prompt"]:
            print(f"DEBUG: Entering off_topic/system branch")
            store_conversation(session, user_query, result, status)
            return _format_response(result, session_id, is_streaming, crew_result)
        
        elif status == "error":
            print(f"DEBUG: Entering error branch")
            return _error_response(result, is_streaming, 500)
        
        else:
            print(f"DEBUG: Entering else branch (success case)")
            # Update session context if available
            if crew_result.get("debug", {}).get("raw_result", {}).get("metadata", {}).get("entities"):
                entities = crew_result["debug"]["raw_result"]["metadata"]["entities"]
                geo_entities = entities.get("geographic", [])
                if geo_entities:
                    session["context"]["last_location"] = geo_entities[0].get("value", "")
            
            session["context"]["last_query_type"] = workflow
            session["context"]["last_query"] = user_query
            
            print(f"DEBUG: About to call store_conversation")
            store_conversation(session, user_query, result, workflow)
            
            print(f"DEBUG: About to call _format_response")
            print(f"DEBUG: Final result being passed: {result[:100]}...")
            
            return _format_response(result, session_id, is_streaming, crew_result)
            
    except Exception as e:
        print(f"[{session_id}] Endpoint error: {str(e)}")
        import traceback
        traceback.print_exc()
        return _error_response(str(e), is_streaming)

def _format_response(result, session_id, is_streaming, debug_info=None):
    """Format response untuk streaming atau non-streaming"""
    try:
        if is_streaming:
            def generate():
                chunk_response = {
                    "id": f"chatcmpl-{int(time.time())}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "NSQM Support Assistant",
                    "choices": [{
                        "index": 0,
                        "delta": {"role": "assistant", "content": result},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(chunk_response)}\n\n"
                
                finish_chunk = {
                    "id": f"chatcmpl-{int(time.time())}",
                    "object": "chat.completion.chunk", 
                    "created": int(time.time()),
                    "model": "NSQM Support Assistant",
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                }
                yield f"data: {json.dumps(finish_chunk)}\n\n"
                yield "data: [DONE]\n\n"
            
            return app.response_class(
                generate(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Content-Type': 'text/event-stream',
                    'Access-Control-Allow-Origin': '*',
                    'X-Session-ID': session_id
                }
            )
        
        else:
            response_data = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "NSQM Support Assistant",
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": result},
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": len(result.split()) if result else 0,
                    "completion_tokens": len(result.split()) if result else 0,
                    "total_tokens": len(result.split()) * 2 if result else 0
                }
            }
            
            response = make_response(jsonify(response_data))
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['X-Session-ID'] = session_id
            if debug_info:
                response.headers['X-Debug-Status'] = debug_info.get("status", "unknown")
                response.headers['X-Debug-Workflow'] = debug_info.get("workflow", "unknown")
            
            return response
            
    except Exception as e:
        print(f"[{session_id}] Format response error: {str(e)}")
        return _error_response(str(e), is_streaming)

def _error_response(error_msg, is_streaming, status_code=500):
    """Generate error response"""
    error_response = {
        "error": {
            "message": error_msg,
            "type": "internal_error", 
            "code": str(status_code)
        }
    }
    
    if is_streaming:
        def generate_error():
            yield f"data: {json.dumps(error_response)}\n\n"
            yield "data: [DONE]\n\n"
        
        return app.response_class(
            generate_error(),
            mimetype='text/event-stream',
            headers={'Access-Control-Allow-Origin': '*'}
        )
    else:
        response = make_response(jsonify(error_response), status_code)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint - GUNAKAN SHARED CONNECTION"""
    # Test SHARED database connection - BUKAN buat connection baru
    if db_tool:
        db_status = db_tool.test_connection()
    else:
        db_status = {"success": False, "error": "No shared DB connection"}
    
    return jsonify({
        "status": "healthy" if db_status["success"] else "unhealthy", 
        "service": "Telkomsel AI Labs - Shared Database Connection",
        "database": db_status,
        "active_sessions": len(chat_sessions),
        "shared_connection": "✅ Using singleton DB manager" if db_tool else "❌ No shared connection",
        "endpoints": ["/v1/chat/completions", "/chat/completions"],
        "features": ["Shared PostgreSQL Connection", "SimplifiedCrew", "Follow-up Context"],
        "ollama_url": os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    })

@app.route('/v1/models', methods=['GET'])
def list_models():
    return jsonify({
        "object": "list",
        "data": [
            {
                "id": "NSQM Support Assistant",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "telkomsel"
            }
        ]
    })

@app.route('/db/test', methods=['GET'])
def test_database():
    """Test SHARED database connection"""
    try:
        if not db_tool:
            return jsonify({
                "error": "No shared database connection available"
            }), 500
        
        # Test SHARED connection - BUKAN buat baru
        connection_result = db_tool.test_connection()
        
        if connection_result["success"]:
            table_info = db_tool.get_table_info()
            return jsonify({
                "connection": connection_result,
                "table_info": table_info,
                "connection_type": "shared_singleton"
            })
        else:
            return jsonify({
                "connection": connection_result,
                "table_info": {"success": False, "error": "Connection failed"},
                "connection_type": "shared_singleton"
            }), 500
            
    except Exception as e:
        return jsonify({
            "error": str(e),
            "connection": {"success": False, "error": str(e)},
            "connection_type": "shared_singleton"
        }), 500

@app.route('/sessions', methods=['GET'])
def list_sessions():
    """List all active chat sessions"""
    sessions_info = {}
    for session_id, session_data in chat_sessions.items():
        sessions_info[session_id] = {
            "chat_id": session_data.get("chat_id"),
            "created_at": session_data.get("created_at"),
            "message_count": session_data.get("message_count", 0),
            "last_activity": session_data.get("last_activity"),
            "has_context": bool(session_data.get("context", {}))
        }
    
    return jsonify({
        "total_sessions": len(chat_sessions),
        "sessions": sessions_info
    })

@app.route('/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get specific session details"""
    if session_id in chat_sessions:
        return jsonify(chat_sessions[session_id])
    return jsonify({"error": "Session not found"}), 404

@app.route('/session/<session_id>', methods=['DELETE'])
def clear_session(session_id):
    """Clear specific session"""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
        return jsonify({"success": True, "message": f"Session {session_id} cleared"})
    return jsonify({"success": False, "message": "Session not found"}), 404

@app.route('/knowledge/upload', methods=['POST'])
def upload_knowledge():
    """Upload and process documents for knowledge base"""
    try:
        if not rag_tool:
            return jsonify({"error": "RAG tool not available"}), 500
        
        # Create sample documents
        doc_processor.create_sample_documents()
        
        # Process documents
        docs = doc_processor.process_directory("./docs")
        
        if not docs:
            return jsonify({
                "message": "No documents found to process",
                "processed": 0
            })
        
        # Add to knowledge base
        added_count = 0
        for doc in docs:
            rag_tool.add_document(doc['content'], doc['metadata'])
            added_count += 1
        
        return jsonify({
            "message": f"Successfully processed and added {added_count} document chunks",
            "processed_files": len(set(doc['metadata']['title'] for doc in docs)),
            "total_chunks": added_count,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/knowledge/search', methods=['POST'])
def search_knowledge():
    """Search knowledge base"""
    try:
        if not rag_tool:
            return jsonify({"error": "RAG tool not available"}), 500
        
        data = request.json or {}
        query = data.get('query', '')
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        results = rag_tool.search_knowledge(query, n_results=5)
        
        return jsonify({
            "query": query,
            "results": results,
            "count": len(results)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/knowledge/stats', methods=['GET'])
def knowledge_stats():
    """Get knowledge base statistics"""
    try:
        if not rag_tool:
            return jsonify({"error": "RAG tool not available"}), 500
        
        stats = rag_tool.get_knowledge_stats()
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/sessions/cleanup', methods=['POST'])
def cleanup_old_sessions():
    """Cleanup sessions older than configured time"""
    current_time = time.time()
    cutoff_time = current_time - SESSION_CLEANUP_TIME
    
    old_sessions = [
        session_id for session_id, session_data in chat_sessions.items()
        if session_data.get("last_activity", 0) < cutoff_time
    ]
    
    for session_id in old_sessions:
        del chat_sessions[session_id]
    
    return jsonify({
        "cleaned_sessions": len(old_sessions),
        "remaining_sessions": len(chat_sessions),
        "cleaned_session_ids": old_sessions
    })

if __name__ == "__main__":
    print("🚀 Starting Telkomsel AI Labs - Direct Database Server")
    print("📊 Available endpoints:")
    print("   - POST /v1/chat/completions (OpenAI compatible)")
    print("   - POST /chat/completions (Direct DB specific)")
    print("   - GET /health (health check)")
    print("   - GET /db/test (database test)")
    print("   - GET /sessions (list sessions)")
    print("")
    print("🔧 Features:")
    print("   - Direct PostgreSQL access (bypassing MCP)")
    print("   - SimplifiedCrew workflow routing")
    print("   - Ollama Llama3 integration")
    print("   - Follow-up context detection")
    print("")
    
    # Get configuration
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 8002))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    
    app.run(host=host, port=port, debug=debug)