import asyncio
from .server import TelcoMCPServer
from shared.utils.logger import log
import uvicorn

async def main():
    server = TelcoMCPServer()
    await server.initialize()
    log.info("Starting Telco MCP Server on port 8001...")
    
    # Use uvicorn directly instead of server.start()
    config = uvicorn.Config(server.app, host="0.0.0.0", port=8001)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())