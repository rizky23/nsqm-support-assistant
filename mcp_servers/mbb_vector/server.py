from shared.mcp_base.server_base import MCPServerBase
from .tools.mbb_rag_tools import MBBRAGTools
from .tools.mbb_search_tools import MBBSearchTools
from shared.utils.logger import log

class MBBVectorMCPServer(MCPServerBase):
    def __init__(self):
        super().__init__("MBB_Vector", "MCP Server for Mobile Broadband Knowledge Base and RAG")
        self.rag_tools = None
        self.search_tools = None
    
    async def initialize(self):


        # Auto-load Excel files from docs folder
        await self._load_excel_files_from_docs()


        """Initialize MBB Vector MCP server"""
        log.info("Initializing MBB Vector MCP Server...")
        
        # Initialize tools
        self.rag_tools = MBBRAGTools()
        self.search_tools = MBBSearchTools()
        
        rag_init = await self.rag_tools.initialize()
        search_init = await self.search_tools.initialize()
        
        if not (rag_init and search_init):
            raise RuntimeError("Failed to initialize MBB tools")
        
        # Register MBB-specific tools
        self.register_tool(
            "search_mbb_knowledge",
            self.rag_tools.search_mbb_parameters,
            "Search mobile broadband knowledge base and parameters"
        )
        
        self.register_tool(
            "search_4g_parameters",
            self.search_tools.search_4g_parameters,
            "Search specific 4G/LTE parameters from Huawei knowledge base"
        )
        
        self.register_tool(
            "get_parameter_optimization",
            self.rag_tools.get_optimization_recommendations,
            "Get optimization recommendations for network parameters"
        )
        
        self.register_tool(
            "search_by_scenario",
            self.search_tools.search_by_scenario,
            "Search parameters by optimization scenario (e.g., accessibility, mobility)"
        )
        
        self.register_tool(
            "add_mbb_knowledge",
            self.rag_tools.add_mbb_knowledge,
            "Add new mobile broadband knowledge document"
        )
        
        self.register_tool(
            "upload_excel_knowledge",
            self.rag_tools.upload_excel_knowledge,
            "Upload and process Excel knowledge files (e.g., parameter sheets)"
        )
        
        self.register_tool(
            "get_mbb_stats",
            self.rag_tools.get_mbb_stats,
            "Get statistics about MBB knowledge base"
        )
        
        log.info("MBB Vector MCP Server initialized successfully")

    async def _load_excel_files_from_docs(self):
        """Auto-load all Excel files from docs folder"""
        import os
        docs_path = "/app/docs"
        
        if not os.path.exists(docs_path):
            log.warning(f"Docs folder not found: {docs_path}")
            return
        
        excel_files = [f for f in os.listdir(docs_path) if f.endswith(('.xlsx', '.xls'))]
        
        for excel_file in excel_files:
            file_path = os.path.join(docs_path, excel_file)
            log.info(f"Auto-loading Excel file: {excel_file}")
            
            try:
                result = await self.search_tools.process_excel_knowledge(file_path=file_path)
                if result.get("success"):
                    log.info(f"Successfully loaded {excel_file}: {result.get('parameters_processed', 0)} parameters")
                else:
                    log.error(f"Failed to load {excel_file}: {result.get('error')}")
            except Exception as e:
                log.error(f"Error loading {excel_file}: {e}")