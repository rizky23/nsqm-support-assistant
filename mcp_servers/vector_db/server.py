from shared.mcp_base.server_base import MCPServerBase
from .tools.rag_tools import RAGTools
from shared.utils.logger import log

class VectorDBMCPServer(MCPServerBase):
    def __init__(self):
        super().__init__("VectorDB", "MCP Server for Vector Database and RAG operations")
        self.rag_tools = None
    
    async def initialize(self):
        """Initialize vector DB specific components"""
        log.info("Initializing Vector DB MCP Server...")
        
        # Initialize RAG tools
        self.rag_tools = RAGTools()
        init_success = await self.rag_tools.initialize()
        
        if not init_success:
            raise RuntimeError("Failed to initialize RAG tools")
        
        # Register tools
        self.register_tool(
            "search_knowledge_base",
            self.rag_tools.search_knowledge_base,
            "Search the knowledge base for relevant information and similar cases"
        )
        
        self.register_tool(
            "get_issue_recommendations",
            self.rag_tools.get_issue_recommendations,
            "Get recommendations for a specific issue based on historical analysis"
        )
        
        self.register_tool(
            "add_analysis_to_knowledge",
            self.rag_tools.add_analysis_to_knowledge,
            "Add telco analysis results to the knowledge base for future reference"
        )
        
        self.register_tool(
            "add_document",
            self.rag_tools.add_document,
            "Add a general document to the knowledge base"
        )
        
        self.register_tool(
            "get_knowledge_stats",
            self.rag_tools.get_knowledge_stats,
            "Get statistics about the knowledge base"
        )
        
        log.info("Vector DB MCP Server initialized successfully")