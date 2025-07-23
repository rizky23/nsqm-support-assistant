import asyncio
from .server import VectorDBMCPServer
from shared.utils.logger import log
import uvicorn

async def main():
    server = VectorDBMCPServer()
    await server.initialize()
    log.info("Starting Vector DB MCP Server on port 8002...")
    
    config = uvicorn.Config(server.app, host="0.0.0.0", port=8002)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())