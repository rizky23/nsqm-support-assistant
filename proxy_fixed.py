from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import httpx
from typing import List, Dict, Any
import uuid
from datetime import datetime
import logging
import json
import time
import hashlib

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Tambahkan CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Dalam production, ganti dengan domain Open-WebUI
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    max_tokens: int = 1000
    temperature: float = 0.7
    stream: bool = False

def get_client_identifier(request: Request) -> str:
    """
    Robust client identification for session management
    Handles various deployment scenarios (direct, behind proxy, localhost)
    """
    
    # Method 1: Check proxy headers (most common in production)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip and client_ip not in ["unknown", ""]:
            logger.info(f"Client IP from X-Forwarded-For: {client_ip}")
            return client_ip
    
    # Method 2: Check other proxy headers
    real_ip = request.headers.get("X-Real-IP")
    if real_ip and real_ip not in ["unknown", ""]:
        logger.info(f"Client IP from X-Real-IP: {real_ip}")
        return real_ip
    
    # Method 3: Check Cloudflare header
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip and cf_ip not in ["unknown", ""]:
        logger.info(f"Client IP from CF-Connecting-IP: {cf_ip}")
        return cf_ip
    
    # Method 4: Direct connection IP
    direct_ip = request.client.host if request.client else None
    if direct_ip and direct_ip not in ["unknown", None]:
        # Handle localhost development
        if direct_ip in ["127.0.0.1", "::1", "localhost"]:
            # Create unique identifier for localhost using User-Agent
            user_agent = request.headers.get("User-Agent", "unknown")[:50]
            browser_fingerprint = f"localhost_{hashlib.md5(user_agent.encode()).hexdigest()[:8]}"
            logger.info(f"Localhost detected, using browser fingerprint: {browser_fingerprint}")
            return browser_fingerprint
        
        logger.info(f"Client IP from direct connection: {direct_ip}")
        return direct_ip
    
    # Method 5: Ultimate fallback - browser fingerprint
    user_agent = request.headers.get("User-Agent", "unknown")
    accept_language = request.headers.get("Accept-Language", "")
    accept_encoding = request.headers.get("Accept-Encoding", "")
    
    fingerprint = f"{user_agent[:20]}_{accept_language[:10]}_{accept_encoding[:10]}"
    fingerprint_id = f"fingerprint_{hashlib.md5(fingerprint.encode()).hexdigest()[:8]}"
    logger.warning(f"Using browser fingerprint fallback: {fingerprint_id}")
    
    return fingerprint_id

def generate_conversation_id(request: Request) -> str:
    """
    Generate time window-based conversation ID
    Same user dalam 30 menit = same session
    """
    
    try:
        # Get robust client identifier
        client_id = get_client_identifier(request)
        
        # Create 30-minute time window (1800 seconds)
        time_window = int(time.time()) // 1800
        
        # Hash client ID for privacy and consistency
        client_hash = hashlib.md5(client_id.encode()).hexdigest()[:8]
        
        # Generate session ID: session_<client_hash>_<time_window>
        conversation_id = f"session_{client_hash}_{time_window}"
        
        logger.info(f"Generated conversation ID: {conversation_id}")
        logger.info(f"Client: {client_id}, Time window: {time_window}")
        
        return conversation_id
        
    except Exception as e:
        # Ultimate fallback
        fallback_id = f"fallback_{uuid.uuid4().hex[:8]}"
        logger.error(f"Conversation ID generation failed: {e}, using fallback: {fallback_id}")
        return fallback_id

def analyze_conversation_type(messages: List[Message]) -> Dict[str, Any]:
    """
    Analyze conversation to provide context info
    """
    
    analysis = {
        "is_new_conversation": len(messages) == 1,
        "message_count": len(messages),
        "conversation_length": "short" if len(messages) <= 3 else "long",
        "has_context": len(messages) > 1
    }
    
    if len(messages) > 1:
        # Extract some context from previous messages
        user_messages = [msg.content for msg in messages if msg.role == "user"]
        analysis["previous_topics"] = [msg[:50] + "..." if len(msg) > 50 else msg for msg in user_messages[:-1]]
    
    return analysis

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "nsqm-support-assistant",
                "object": "model",
                "created": int(datetime.now().timestamp()),
                "owned_by": "nsqm",
                "permission": [],
                "root": "nsqm-support-assistant",
                "parent": None,
                "description": "NSQM Telco Network Analysis Assistant with Time Window Session Management"
            }
        ]
    }

@app.options("/v1/models")
async def models_options():
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
    )

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "OpenAI Proxy for NSQM",
        "features": [
            "time_window_sessions", 
            "multi_user_support", 
            "context_preservation",
            "robust_ip_detection"
        ],
        "session_duration": "30 minutes"
    }

@app.options("/v1/chat/completions")
async def chat_completions_options():
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
            "Access-Control-Max-Age": "86400"
        }
    )

@app.post("/v1/chat/completions")
async def chat_completions(request_body: ChatCompletionRequest, request: Request):
    
    # Generate time window-based conversation ID
    conversation_id = generate_conversation_id(request)
    
    # Analyze conversation type
    conversation_analysis = analyze_conversation_type(request_body.messages)

    # ADD HERE: Limit messages to prevent context overload
    if len(request_body.messages) > 6:  # Max 5 exchanges
        # Keep only recent messages
        request_body.messages = request_body.messages[-6:]
        logger.info(f"Limited messages to last 6 (3 exchanges)")

    # Get the latest user message
    user_message = ""
    for msg in reversed(request_body.messages):
        if msg.role == "user":
            user_message = msg.content
            break
    
    # Log conversation details
    logger.info(f"Session: {conversation_id}")
    logger.info(f"Conversation type: {'New' if conversation_analysis['is_new_conversation'] else 'Continuing'}")
    logger.info(f"Message count: {conversation_analysis['message_count']}")
    
    # Get the latest user message
    user_message = ""
    for msg in reversed(request_body.messages):
        if msg.role == "user":
            user_message = msg.content
            break

    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    # Filter out OpenWebUI follow-up templates
    if "### Task:" in user_message and "follow-up" in user_message.lower():
        # Use the actual query based on context or default
        if conversation_analysis.get("previous_topics"):
            # Get the last real user query from previous topics
            last_topic = conversation_analysis["previous_topics"][-1]
            user_message = last_topic if not last_topic.startswith("###") else "Jelaskan parameter 4G/LTE untuk optimasi jaringan"
        else:
            user_message = "Jelaskan parameter 4G/LTE untuk optimasi jaringan"
        
        logger.info(f"Blocked follow-up template, using query: {user_message[:50]}...")
    
    # Prepare payload for orchestrator
    orchestrator_payload = {
        "query": user_message
    }
    
    # Add context information if this is a continuing conversation
    if conversation_analysis["has_context"]:
        logger.info(f"Continuing conversation with context: {conversation_analysis['previous_topics']}")
    
    logger.info(f"Sending to orchestrator - Session: {conversation_id}, Query: '{user_message[:50]}...'")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            # Make call to orchestrator with time window-based conversation ID
            response = await client.post(
                f"http://telecom-mcp-ecosystem-orchestrator-1:8000/chat/{conversation_id}",
                json=orchestrator_payload
            )
            response.raise_for_status()
            orchestrator_data = response.json()
            
            logger.info(f"Orchestrator response - Session: {conversation_id}, Success: {orchestrator_data.get('success', False)}")
            
            if not orchestrator_data.get("success", False):
                error_msg = orchestrator_data.get("error", "Orchestrator returned error")
                raise HTTPException(status_code=500, detail=f"Orchestrator error: {error_msg}")
            
            assistant_content = orchestrator_data.get("response", "")
            tools_used = orchestrator_data.get("tools_used", [])
            
            # Clean up response formatting
            assistant_content = assistant_content.strip()
            
            # Remove stray parentheses that might appear
            import re
            assistant_content = re.sub(r'\n\(\s*\)\n', '\n', assistant_content)  # \n( )\n
            assistant_content = re.sub(r'\(\s*\)', '', assistant_content)        # ( )
            assistant_content = assistant_content.replace('\n(\n', '\n')
            assistant_content = assistant_content.replace(' ( ', ' ')
            assistant_content = assistant_content.replace('(\n', '\n')
            
            # Ensure content is not empty
            if not assistant_content:
                assistant_content = "Maaf, tidak ada respons dari sistem. Silakan coba lagi."
            
            # Log tools used for debugging
            if tools_used:
                logger.info(f"Tools used in session {conversation_id}: {tools_used}")
            
            # Return streaming response for OpenWebUI compatibility
            def generate():
                try:
                    # Verify content exists and is complete
                    nonlocal assistant_content  # Important: access outer scope variable
                    
                    if not assistant_content or len(assistant_content.strip()) < 10:
                        assistant_content = "❌ Response tidak lengkap. Silakan coba lagi."
                        logger.warning("Assistant content too short or empty")
                    
                    # Log full content for debugging
                    logger.info(f"✅ Full response length: {len(assistant_content)} characters")
                    logger.info(f"📝 Full response preview: {assistant_content[:300]}...")
                    
                    # First chunk with role
                    first_chunk = {
                        "id": f"chatcmpl-{uuid.uuid4().hex}",
                        "object": "chat.completion.chunk", 
                        "created": int(datetime.now().timestamp()),
                        "model": request_body.model,
                        "choices": [{
                            "index": 0,
                            "delta": {"role": "assistant", "content": ""},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(first_chunk)}\n\n"
                    
                    # Stream content with smaller chunks
                    chunk_size = 30
                    logger.info(f"🚀 Starting streaming {len(assistant_content)} chars in chunks of {chunk_size}")
                    
                    for i in range(0, len(assistant_content), chunk_size):
                        content_chunk = assistant_content[i:i+chunk_size]
                        
                        chunk_response = {
                            "id": f"chatcmpl-{uuid.uuid4().hex}",
                            "object": "chat.completion.chunk",
                            "created": int(datetime.now().timestamp()),
                            "model": request_body.model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": content_chunk},
                                "finish_reason": None
                            }]
                        }
                        
                        yield f"data: {json.dumps(chunk_response)}\n\n"
                        
                        # Log progress for long responses
                        if i % 500 == 0:  # Every 500 chars
                            progress = (i / len(assistant_content)) * 100
                            logger.info(f"📊 Streaming progress: {progress:.1f}%")
                        
                        time.sleep(0.03)
                    
                    # Final chunk
                    finish_chunk = {
                        "id": f"chatcmpl-{uuid.uuid4().hex}",
                        "object": "chat.completion.chunk",
                        "created": int(datetime.now().timestamp()),
                        "model": request_body.model,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }]
                    }
                    yield f"data: {json.dumps(finish_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                    
                    logger.info("✅ Streaming completed successfully")
                    
                except Exception as e:
                    logger.error(f"❌ Streaming error: {e}")
                    error_chunk = {
                        "id": f"chatcmpl-{uuid.uuid4().hex}",
                        "object": "chat.completion.chunk",
                        "created": int(datetime.now().timestamp()),
                        "model": request_body.model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": f"\n\n❌ Streaming error: {str(e)}\nSilakan coba lagi."},
                            "finish_reason": "error"
                        }]
                    }
                    yield f"data: {json.dumps(error_chunk)}\n\n"
                    yield "data: [DONE]\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                }
            )
            
        except httpx.TimeoutException:
            logger.error(f"Timeout for session {conversation_id}")
            raise HTTPException(status_code=504, detail="Request timeout - sistem membutuhkan waktu lebih lama untuk memproses")
        except httpx.RequestError as e:
            logger.error(f"Connection error for session {conversation_id}: {e}")
            raise HTTPException(status_code=503, detail=f"Tidak dapat terhubung ke sistem: {str(e)}")
        except Exception as e:
            logger.error(f"Error for session {conversation_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Kesalahan internal: {str(e)}")

# Debug endpoint for testing session management
@app.get("/debug/session-info")
async def debug_session_info(request: Request):
    """Debug endpoint untuk testing session management"""
    
    client_id = get_client_identifier(request)
    conversation_id = generate_conversation_id(request)
    time_window = int(time.time()) // 1800
    
    return {
        "client_identifier": client_id,
        "conversation_id": conversation_id,
        "time_window": time_window,
        "session_expires_in_seconds": 1800 - (int(time.time()) % 1800),
        "headers": dict(request.headers),
        "client_host": request.client.host if request.client else None
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting OpenAI Proxy with Time Window Session Management...")
    print("📊 Features: Multi-user sessions, 30-min context windows, Production-ready")
    print("🔧 Session format: session_<client_hash>_<time_window>")
    uvicorn.run(app, host="0.0.0.0", port=8005)