from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx
from typing import List, Dict, Any
import uuid
from datetime import datetime
import logging

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
    
    # Jika streaming diminta, tolak untuk sementara
    if request.stream:
        raise HTTPException(status_code=400, detail="Streaming not supported")
    
    user_message = ""
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break
    
    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")
    
    orchestrator_payload = {
        "query": user_message,
        "session_id": f"openai-proxy-{uuid.uuid4().hex[:8]}"
    }
    
    logger.info(f"Sending to orchestrator: {orchestrator_payload}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://orchestrator:8000/chat",
                json=orchestrator_payload,
                timeout=30.0
            )
            response.raise_for_status()
            orchestrator_data = response.json()
            
            logger.info(f"Orchestrator response: {orchestrator_data}")
            
            if not orchestrator_data.get("success", False):
                raise HTTPException(status_code=500, detail="Orchestrator returned error")
            
            assistant_content = orchestrator_data.get("response", "")
            
            # Pastikan content tidak kosong
            if not assistant_content:
                assistant_content = "Maaf, tidak ada respons dari sistem."
            
            response_data = {
                "id": f"chatcmpl-{uuid.uuid4().hex}",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": assistant_content
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": len(user_message.split()),
                    "completion_tokens": len(assistant_content.split()),
                    "total_tokens": len(user_message.split()) + len(assistant_content.split())
                }
            }
            
            # Return JSONResponse with explicit headers
            return JSONResponse(
                content=response_data,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization",
                    "Content-Type": "application/json"
                }
            )
            
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Request timeout")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Connection error: {str(e)}")
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)