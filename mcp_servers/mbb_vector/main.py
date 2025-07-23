import asyncio
from .server import MBBVectorMCPServer
from shared.utils.logger import log
import uvicorn

async def main():
    server = MBBVectorMCPServer()
    await server.initialize()
    log.info("Starting MBB Vector MCP Server on port 8003...")
    
    config = uvicorn.Config(server.app, host="0.0.0.0", port=8003)
    uvicorn_server = uvicorn.Server(config)
    await uvicorn_server.serve()

if __name__ == "__main__":
    asyncio.run(main())