from fastapi import FastAPI, HTTPException, Response
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
                "description": "NSQM Telco Network Analysis Assistant"
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
    return {"status": "healthy", "service": "OpenAI Proxy for NSQM"}

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
async def chat_completions(request: ChatCompletionRequest):
    logger.info(f"Received request: {request}")
    
    # Get the latest user message
    user_message = ""
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break
    
    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")
    
    # Simple payload - let orchestrator handle conversation context
    orchestrator_payload = {
        "query": user_message
    }
    
    logger.info(f"Sending to orchestrator: {orchestrator_payload}")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            # Generate conversation ID from first message to maintain context
            first_message_content = request.messages[0].content if request.messages else "default"
            conversation_id = "openwebui_session"

            # Make call to orchestrator
            response = await client.post(
                f"http://telecom-mcp-ecosystem-orchestrator-1:8000/chat/{conversation_id}",
                json=orchestrator_payload
            )
            response.raise_for_status()
            orchestrator_data = response.json()
            
            logger.info(f"Orchestrator response: {orchestrator_data}")
            
            if not orchestrator_data.get("success", False):
                error_msg = orchestrator_data.get("error", "Orchestrator returned error")
                raise HTTPException(status_code=500, detail=f"Orchestrator error: {error_msg}")
            
            assistant_content = orchestrator_data.get("response", "")
            
            # Clean up response formatting - remove markdown artifacts
            if assistant_content:
                assistant_content = assistant_content.replace('**', '')  # Remove bold
                assistant_content = assistant_content.replace('*', '')   # Remove italics
                assistant_content = assistant_content.replace('###', '') # Remove headers
                assistant_content = assistant_content.replace('===', '') # Remove dividers
                assistant_content = assistant_content.strip()
            
            # Pastikan content tidak kosong after cleaning
            if not assistant_content:
                assistant_content = "Maaf, tidak ada respons dari sistem. Silakan coba lagi."
            
            # Always return streaming response for OpenWebUI compatibility
            def generate():
                try:
                    # First chunk dengan role
                    first_chunk = {
                        "id": f"chatcmpl-{uuid.uuid4().hex}",
                        "object": "chat.completion.chunk",
                        "created": int(datetime.now().timestamp()),
                        "model": request.model,
                        "choices": [{
                            "index": 0,
                            "delta": {"role": "assistant", "content": ""},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(first_chunk)}\n\n"
                    
                    # Stream content dengan chunk size yang optimal
                    chunk_size = 6  # Balance antara smoothness dan readability
                    words = assistant_content.split()
                    
                    for i in range(0, len(words), chunk_size):
                        chunk_words = words[i:i+chunk_size]
                        content_chunk = " ".join(chunk_words)
                        
                        if i + chunk_size < len(words):
                            content_chunk += " "
                        
                        chunk_response = {
                            "id": f"chatcmpl-{uuid.uuid4().hex}",
                            "object": "chat.completion.chunk",
                            "created": int(datetime.now().timestamp()),
                            "model": request.model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": content_chunk},
                                "finish_reason": None
                            }]
                        }
                        yield f"data: {json.dumps(chunk_response)}\n\n"
                        
                        # Natural typing speed
                        time.sleep(0.05)
                    
                    # Final chunk
                    finish_chunk = {
                        "id": f"chatcmpl-{uuid.uuid4().hex}",
                        "object": "chat.completion.chunk",
                        "created": int(datetime.now().timestamp()),
                        "model": request.model,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }]
                    }
                    yield f"data: {json.dumps(finish_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                    
                except Exception as e:
                    logger.error(f"Streaming error: {e}")
                    # Error chunk dengan Indonesian message
                    error_chunk = {
                        "id": f"chatcmpl-{uuid.uuid4().hex}",
                        "object": "chat.completion.chunk",
                        "created": int(datetime.now().timestamp()),
                        "model": request.model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": f"❌ Terjadi kesalahan: {str(e)}\n\nSilakan coba lagi atau hubungi administrator."},
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
            raise HTTPException(status_code=504, detail="Request timeout - sistem membutuhkan waktu lebih lama untuk memproses")
        except httpx.RequestError as e:
            logger.error(f"Connection error: {e}")
            raise HTTPException(status_code=503, detail=f"Tidak dapat terhubung ke sistem: {str(e)}")
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Kesalahan internal: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)