from shared.mcp_base.server_base import MCPServerBase
from .tools.api_tools import TelcoAPITools
from shared.utils.logger import log

class TelcoMCPServer(MCPServerBase):
    def __init__(self):
        super().__init__("TelcoAPI", "MCP Server for Telco API Integration and Analysis")
        self.tools_handler = None
    
    async def initialize(self):
        """Initialize telco-specific components"""
        log.info("Initializing Telco MCP Server...")
        
        # Initialize tools
        self.tools_handler = TelcoAPITools()
        
        # Register tools
        self.register_tool(
            "get_comprehensive_analysis",
            self.tools_handler.get_comprehensive_analysis,
            "Get comprehensive analysis from all telco APIs with insights and recommendations"
        )
        
        self.register_tool(
            "get_user_info",
            self.tools_handler.get_user_info_only,
            "Get user and device information"
        )
        
        self.register_tool(
            "get_quality_metrics",
            self.tools_handler.get_quality_metrics_only,
            "Get network quality metrics"
        )
        
        self.register_tool(
            "get_history_data",
            self.tools_handler.get_history_data_only,
            "Get historical traffic and performance data"
        )
        
        self.register_tool(
            "analyze_network_issues",
            self.tools_handler.analyze_network_issues,
            "Focused analysis for network performance issues and troubleshooting"
        )

        self.register_tool(
            "generate_traffic_chart",
            self.tools_handler.generate_traffic_chart,
            "Generate interactive chart for traffic and score analysis with dual-axis visualization"
        )

        self.register_tool(
            "perform_root_cause_analysis",
            self.tools_handler.perform_root_cause_analysis,
            "Perform detailed root cause analysis using demarcation data and network diagnostics"
        )
        
        self.register_tool(
            "handle_follow_up_command", 
            self.tools_handler.handle_follow_up_command,
            "Handle follow-up commands like 'ya rca', 'ya chart', 'ya network' for continued analysis"
        )
        
        log.info("Telco MCP Server initialized successfully")
