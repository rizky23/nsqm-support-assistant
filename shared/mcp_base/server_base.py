import json
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from fastapi import FastAPI
from ..utils.logger import log

class MCPServerBase(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.app = FastAPI(title=f"{name} MCP Server", description=description)
        self.tools: Dict[str, Any] = {}
        self._setup_routes()
    
    def _setup_routes(self):
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "server": self.name}
        
        @self.app.get("/tools")
        async def list_tools():
            return {"tools": list(self.tools.keys())}
        
        @self.app.post("/call")
        async def call_tool(request: dict):
            tool_name = request.get("tool")
            params = request.get("params", {})
            
            if tool_name not in self.tools:
                return {"error": f"Tool {tool_name} not found"}
            
            try:
                result = await self.tools[tool_name](**params)
                return {"success": True, "result": result}
            except Exception as e:
                log.error(f"Tool {tool_name} failed: {e}")
                return {"error": str(e)}
    
    def register_tool(self, name: str, func: callable, description: str = ""):
        self.tools[name] = func
        log.info(f"Registered tool: {name}")
    
    @abstractmethod
    async def initialize(self):
        """Initialize server-specific components"""
        pass
    
    async def start(self, host: str = "0.0.0.0", port: int = 8000):
        await self.initialize()
        import uvicorn
        await uvicorn.run(self.app, host=host, port=port)