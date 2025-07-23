#!/usr/bin/env python3
"""
Telecom MCP Ecosystem Main Entry Point
OpenAI Compatible API for NSQM Support Assistant
"""

import asyncio
import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import httpx
import uuid
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="NSQM Telco Analysis Platform",
    description="Telecom MCP Ecosystem with OpenAI Compatible API",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
ORCHESTRATOR_URL = "http://orchestrator:8000"
TELCO_MCP_URL = "http://telco-mcp:8001"
VECTOR_MCP_URL = "http://vector-mcp:8002"
MBB_MCP_URL = "http://mbb-mcp:8003"

# OpenAI Compatible Models
class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]

class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "nsqm"

# Legacy chat models for backward compatibility
class ChatRequest(BaseModel):
    query: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    success: bool
    response: str
    query: str
    tools_used: list = []

# OpenAI Compatible Endpoints
@app.get("/v1/models")
async def list_models():
    """OpenAI compatible models endpoint"""
    return {
        "object": "list",
        "data": [
            {
                "id": "nsqm-support-assistant",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "nsqm",
                "permission": [],
                "root": "nsqm-support-assistant",
                "parent": None,
                "description": "NSQM Telco Network Analysis Assistant"
            }
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI compatible chat completions endpoint"""
    
    # Extract user message
    user_message = ""
    system_message = ""
    
    for message in request.messages:
        if message.role == "user":
            user_message = message.content
        elif message.role == "system":
            system_message = message.content
    
    if not user_message:
        user_message = "Hello"
    
    # Create session ID for tracking
    session_id = f"openwebui_{int(time.time())}"
    
    try:
        # Call orchestrator service
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/chat",
                json={
                    "query": user_message,
                    "session_id": session_id
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                response_content = result.get("response", "I'm ready to help with telecom analysis!")
                tools_used = result.get("tools_used", [])
                success = result.get("success", True)
                
                # Add context about tools used if any
                if tools_used:
                    response_content += f"\n\n*Analysis performed using: {', '.join(tools_used)}*"
                
            else:
                logger.error(f"Orchestrator error: {response.status_code}")
                response_content = "Sorry, I'm having trouble connecting to the telco analysis system. Please try again."
        
        # Format as OpenAI compatible response
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_content
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(response_content.split()),
                "total_tokens": len(user_message.split()) + len(response_content.split())
            }
        }
        
    except httpx.TimeoutException:
        error_content = "The telco analysis system is taking longer than expected. Please try a simpler query."
    except httpx.ConnectError:
        error_content = "Cannot connect to telco analysis system. Please check if the system is running."
    except Exception as e:
        logger.error(f"Chat completion error: {str(e)}")
        error_content = f"An error occurred while processing your request: {str(e)}"
    
    # Error response in OpenAI format
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": error_content
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": len(user_message.split()),
            "completion_tokens": len(error_content.split()),
            "total_tokens": len(user_message.split()) + len(error_content.split())
        }
    }

# Legacy chat endpoint for backward compatibility
@app.post("/chat")
async def legacy_chat_endpoint(request: ChatRequest):
    """Legacy chat endpoint for direct API access"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/chat",
                json={
                    "query": request.query,
                    "session_id": request.session_id
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                return ChatResponse(
                    success=True,
                    response=result.get("response", "Analysis completed"),
                    query=request.query,
                    tools_used=result.get("tools_used", [])
                )
            else:
                return ChatResponse(
                    success=False,
                    response=f"Error: {response.status_code}",
                    query=request.query,
                    tools_used=[]
                )
                
    except Exception as e:
        return ChatResponse(
            success=False,
            response=f"System error: {str(e)}",
            query=request.query,
            tools_used=[]
        )

# Health check endpoints
@app.get("/health")
async def health_check():
    """System health check"""
    health_status = {
        "nsqm_platform": "healthy",
        "timestamp": int(time.time()),
        "services": {}
    }
    
    # Check orchestrator
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ORCHESTRATOR_URL}/health")
            health_status["services"]["orchestrator"] = "healthy" if response.status_code == 200 else "unhealthy"
    except:
        health_status["services"]["orchestrator"] = "unreachable"
    
    # Check MCP servers
    mcp_services = {
        "telco_mcp": TELCO_MCP_URL,
        "vector_mcp": VECTOR_MCP_URL,
        "mbb_mcp": MBB_MCP_URL
    }
    
    for service_name, service_url in mcp_services.items():
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{service_url}/health")
                health_status["services"][service_name] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            health_status["services"][service_name] = "unreachable"
    
    return health_status

@app.get("/v1/models/{model_id}")
async def get_model_info(model_id: str):
    """Get specific model information"""
    if model_id == "nsqm-support-assistant":
        return {
            "id": "nsqm-support-assistant",
            "object": "model",
            "created": int(time.time()),
            "owned_by": "nsqm",
            "description": "NSQM Telco Network Analysis Assistant - Specialized in telecom network analysis, troubleshooting, and 4G/5G parameter optimization",
            "capabilities": [
                "Network performance analysis",
                "MSISDN traffic analysis", 
                "Historical trend analysis",
                "4G/LTE parameter optimization",
                "Device compatibility analysis",
                "Network troubleshooting"
            ],
            "supported_queries": [
                "Analyze MSISDN performance",
                "Check network quality",
                "Historical traffic trends",
                "4G parameter optimization",
                "Device information lookup"
            ]
        }
    else:
        raise HTTPException(status_code=404, detail="Model not found")

# CORS preflight handler
@app.options("/v1/{path:path}")
async def options_handler():
    """Handle CORS preflight requests"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
    )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "platform": "NSQM Telco Analysis Platform",
        "version": "1.0.0",
        "description": "Telecom MCP Ecosystem with OpenAI Compatible API",
        "endpoints": {
            "models": "/v1/models",
            "chat": "/v1/chat/completions",
            "legacy_chat": "/chat",
            "health": "/health"
        },
        "features": [
            "Network performance analysis",
            "MSISDN traffic analysis",
            "Historical trend analysis", 
            "4G/LTE parameter optimization",
            "OpenAI compatible API"
        ],
        "model": "nsqm-support-assistant"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("🚀 NSQM Telco Analysis Platform starting...")
    logger.info("📡 OpenAI compatible API enabled")
    logger.info("🤖 Model: nsqm-support-assistant")
    logger.info("🔗 Orchestrator URL: %s", ORCHESTRATOR_URL)

# Main execution
if __name__ == "__main__":
    logger.info("Starting NSQM Telco Analysis Platform...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )