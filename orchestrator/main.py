# orchestrator/main.py - CLEANED VERSION

import sys
import os

# Add app directory to Python path
sys.path.append('/app')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Path
from typing import Dict, Any, Optional, List
import httpx
import re
import json
import uuid
import time
from datetime import datetime, timedelta

# Single imports - no duplicates
from pydantic import BaseModel
from shared.storage.conversation_store import ConversationStore
from shared.utils.context_manager import OllamaContextManager, ConversationAnalyzer, SimpleSessionManager
from shared.utils.logger import log

# Pydantic models
class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    success: bool
    response: str
    query: str
    conversation_id: str
    timestamp: datetime
    tools_used: list = []

class OpenAIChatRequest(BaseModel):
    model: str
    messages: List[dict]
    temperature: Optional[float] = 0.7

# ✅ SINGLE INITIALIZATION - Remove duplicates
app = FastAPI(title="MCP Orchestrator - Enhanced Context Awareness")

# Initialize components ONCE
conversation_store = ConversationStore(redis_host="redis", redis_port=6379)
context_manager = OllamaContextManager()
session_manager = SimpleSessionManager(timeout_minutes=30)

# MCP Server endpoints
MCP_SERVERS = {
    "telco": "http://telecom-mcp-ecosystem-telco-mcp-1:8001",
    "vector_db": "http://telecom-mcp-ecosystem-vector-mcp-1:8002", 
    "mbb": "http://telecom-mcp-ecosystem-mbb-mcp-1:8003"
}

# ADD THIS TO orchestrator/main.py after MCP_SERVERS definition:

# Query Analysis Functions
async def enhanced_parse_user_query(query: str, conversation_id: str, conversation_history: List[Dict]) -> Dict[str, Any]:
    """Enhanced query parsing with session context and smart analysis"""
    
    # Get session context
    session_context = session_manager.get_session_context(conversation_id)
    
    # Enhanced entity extraction
    entities = ConversationAnalyzer.enhanced_extract_entities(conversation_history + [{"content": query}])
    
    # Intent detection with context
    intent = ConversationAnalyzer.detect_intent(query, session_context)
    
    # Get conversation context
    conversation_context = ConversationAnalyzer.get_conversation_context(conversation_history)
    
    # Get MSISDN from entities or session
    msisdn = None
    if entities.get('msisdns'):
        msisdn = entities['msisdns'][0]
    elif session_context.get('entities', {}).get('msisdns'):
        msisdn = session_context['entities']['msisdns'][0]
        log.info(f"Using MSISDN from session context: {msisdn}")
    
    # Check if historical analysis needed
    needs_history = any(keyword in query.lower() for keyword in [
        'history', 'historical', 'trend', 'compare', 'comparison', 'minggu', 'week', 
        'hari ini vs', 'bandingkan', '7 hari', 'seminggu', 'kemarin vs'
    ])
    
    # Update session context
    topics = entities.get('topics', [])
    session_manager.update_session_context(conversation_id, entities, intent, topics)
    
    return {
        "msisdn": msisdn,
        "intent": intent,
        "entities": entities,
        "topics": topics,
        "needs_history": needs_history,
        "session_context": session_context,
        "conversation_context": conversation_context
    }

async def enhanced_should_use_mbb_knowledge(query: str, parsed_context: Dict) -> bool:
    """Enhanced MBB knowledge routing decision using LLM classification"""
    
    conversation_context = {
        "active_topics": parsed_context.get('topics', []),
        "entities": parsed_context.get('entities', {})
    }
    
    return await ConversationAnalyzer.should_use_mbb_knowledge(query, conversation_context)

# Tool Execution Functions
async def execute_telco_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute telco MCP tool"""
    try:
        # Determine timeout based on tool type
        if tool_name == "perform_root_cause_analysis":
            timeout_seconds = 300.0  # 5 minutes for RCA (butuh 2-3 menit)
            log.info(f"🕐 RCA tool call - using extended timeout: {timeout_seconds}s")
        else:
            timeout_seconds = 60.0   # 1 minute for other tools
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MCP_SERVERS['telco']}/call",
                json={"tool": tool_name, "params": params},
                timeout=timeout_seconds  # Dynamic timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
    except httpx.TimeoutError:
        error_msg = f"Timeout executing {tool_name} after {timeout_seconds}s"
        log.error(error_msg)
        return {"success": False, "error": error_msg}
    except Exception as e:
        log.error(f"Telco tool call failed: {e}")
        return {"success": False, "error": str(e)}

async def execute_mbb_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute MBB MCP tool"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MCP_SERVERS['mbb']}/call",
                json={"tool": tool_name, "params": params},
                timeout=60.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        log.error(f"MBB tool call failed: {e}")
        return {"success": False, "error": str(e)}

def detect_date_from_query(query: str) -> datetime:
    """Smart date detection from query"""
    import re
    from datetime import datetime, timedelta
    
    # Relative dates
    today_keywords = ['hari ini', 'today', 'sekarang', 'saat ini']
    yesterday_keywords = ['kemarin', 'yesterday']
    
    if any(keyword in query.lower() for keyword in today_keywords):
        return datetime.now()
    elif any(keyword in query.lower() for keyword in yesterday_keywords):
        return datetime.now() - timedelta(days=1)
    else:
        return datetime.now()  # Default to yesterday
    
def extract_msisdn_from_conversation(conversation_history: List[Dict]) -> Optional[str]:
    """Extract MSISDN from previous conversation messages"""
    import re
    
    # MSISDN patterns
    msisdn_patterns = [
        r'\b(08\d{8,11})\b',   # 08xxxxxxxxx
        r'\b(81\d{8,11})\b',   # 81xxxxxxxxx  
        r'\b(82\d{9,12})\b',   # 82xxxxxxxxx
        r'\b(\d{10,13})\b'     # Generic 10-13 digits
    ]
    
    # Search in reverse order (latest messages first)
    for message in reversed(conversation_history):
        content = message.get("content", "")
        
        # Check message content for MSISDN
        for pattern in msisdn_patterns:
            matches = re.findall(pattern, content)
            if matches:
                return matches[0]  # Return first valid MSISDN found
        
        # Check metadata if available
        metadata = message.get("metadata", {})
        entities = metadata.get("entities", {})
        msisdns = entities.get("msisdns", [])
        if msisdns:
            return msisdns[0]
    
    return None


# Main Chat Endpoint
@app.post("/chat/{conversation_id}")
async def chat_endpoint(
    conversation_id: str = Path(..., description="Unique conversation identifier"),
    request: ChatRequest = None
):
    """Enhanced Claude-style conversation endpoint"""
    
    start_time = time.time()
    log.info(f"🚀 REQUEST START: {request.query[:50]}...")
    
    # Load full conversation history
    load_start = time.time()
    conversation_history = conversation_store.load_conversation(conversation_id)
    log.info(f"⏱️ LOAD CONVERSATION: {time.time() - load_start:.3f}s")

    # Limit conversation history
    if len(conversation_history) > 10:
        original_length = len(conversation_history)
        conversation_history = conversation_history[-10:]
        log.info(f"LIMITED conversation history from {original_length} to {len(conversation_history)} messages")
    else:
        log.info(f"No limiting needed - conversation has {len(conversation_history)} messages (≤10)")

    # ADD NEW: Topic change detection
    topic_start = time.time()
    is_new_topic = await ConversationAnalyzer.classify_topic_change(
        request.query, conversation_history
    )
    log.info(f"⏱️ TOPIC DETECTION: {time.time() - topic_start:.3f}s - Result: {is_new_topic}")

    if is_new_topic:
        log.info("New topic detected - resetting context")
        conversation_history = []  # Fresh start
        session_manager.update_session_context(conversation_id, {}, "general", [])
    
    # Enhanced query parsing
    parse_start = time.time()
    parsed_context = await enhanced_parse_user_query(request.query, conversation_id, conversation_history)
    log.info(f"⏱️ QUERY PARSING: {time.time() - parse_start:.3f}s")
    
    msisdn = parsed_context.get("msisdn")
    intent = parsed_context.get("intent")
    entities = parsed_context.get("entities", {})
    topics = parsed_context.get("topics", [])
    needs_history = parsed_context.get("needs_history", False)
    
    tools_used = []
    raw_data = None
    
    # Route query based on enhanced analysis
    try:
        log.info(f"CONVERSATION DEBUG: Loaded {len(conversation_history)} messages for session {conversation_id}")


        # TAMBAH DI SINI ← RCA DETECTION
        # Detect RCA request
        rca_patterns = [
            "ya rca",
            "rca",  
            "root cause analysis",
            "analisis root cause",
            "analisa mendalam",
            "investigate deeper"
        ]

        is_rca_request = any(pattern in request.query.lower() for pattern in rca_patterns)

        if is_rca_request:
            # Try to find MSISDN from multiple sources
            target_msisdn = None
            
            # 1. Check if MSISDN in current query
            if msisdn:
                target_msisdn = msisdn
            
            # 2. Check conversation history
            elif conversation_history:
                target_msisdn = extract_msisdn_from_conversation(conversation_history)
            
            # 3. Check session context
            elif parsed_context.get('session_context', {}).get('entities', {}).get('msisdns'):
                target_msisdn = parsed_context['session_context']['entities']['msisdns'][0]
            
            # 4. Extract from current query with relaxed pattern
            else:
                import re
                msisdn_match = re.search(r'\b(8\d{9,12})\b', request.query)
                if msisdn_match:
                    target_msisdn = msisdn_match.group(1)
            
            if target_msisdn:
                tool_start = time.time()
                
                # Add progress message for user
                log.info(f"🔍 RCA Analysis triggered for MSISDN: {target_msisdn}")
                log.info(f"⏱️ Expected completion: 2-3 minutes")
                
                target_date = detect_date_from_query(request.query)
                params = {
                    "msisdn": target_msisdn,
                    "start_time": target_date.strftime("%Y-%m-%d 00:00"),
                    "end_time": target_date.strftime("%Y-%m-%d 23:55")
                }
                
                # Execute RCA with extended timeout
                tool_result = await execute_telco_tool("perform_root_cause_analysis", params)
                tools_used.append("perform_root_cause_analysis")
                
                execution_time = time.time() - tool_start
                log.info(f"⏱️ RCA TOOL EXECUTION: {execution_time:.3f}s")
                
                # Enhanced RCA response processing
                llm_start = time.time()
                
                # Initialize response_text variable
                response_text = ""
                
                try:
                    if tool_result.get("success"):
                        rca_data = tool_result.get("result", {}).get("root_cause_analysis", {})
                        
                        # Build complete response step by step using list approach
                        response_lines = [
                            f"🔍 **Root Cause Analysis - MSISDN {target_msisdn}**",
                            "",
                            f"🚨 **Severity Level:** {rca_data.get('severity', 'unknown').upper()}",
                            "",
                            "🔧 **Root Causes Identified:**"
                        ]
                        
                        # Add root causes with proper formatting
                        root_causes = rca_data.get("root_causes", [])
                        if root_causes:
                            for cause in root_causes:
                                response_lines.append(f"• {cause}")
                        else:
                            response_lines.append("• No specific root causes identified")
                        
                        response_lines.extend([
                            "",
                            "💡 **Recommendations:**"
                        ])
                        
                        # Add recommendations with proper formatting
                        recommendations = rca_data.get("recommendations", [])
                        if recommendations:
                            for rec in recommendations:
                                response_lines.append(f"• {rec}")
                        else:
                            response_lines.append("• No specific recommendations available")
                        
                        # Add summary section
                        summary = rca_data.get('summary', 'RCA analysis completed')
                        response_lines.extend([
                            "",
                            "📋 **Summary:**",
                            summary,
                            "",
                            f"⏱️ **Analysis completed in {execution_time:.1f} seconds**"
                        ])
                        
                        # Join all lines with proper line breaks
                        response_text = "\n".join(response_lines)
                        
                        # Validation and logging
                        if len(response_text) < 100:
                            response_text += "\n\n⚠️ **Note:** Response may be incomplete. Please retry if needed."
                        
                        log.info(f"✅ RCA response generated - Length: {len(response_text)} chars")
                        log.info(f"📝 Content preview: {response_text[:300]}...")
                        
                    else:
                        # Enhanced error handling
                        error = tool_result.get('error', 'Unknown error')
                        
                        error_lines = [
                            "🚨 **Root Cause Analysis Failed**",
                            "",
                            f"**MSISDN:** {target_msisdn}",
                            f"**Error:** {error}",
                            "",
                            "**Kemungkinan penyebab:**",
                            "• API timeout (butuh lebih dari 5 menit)",
                            "• Network connectivity issues", 
                            "• MSISDN tidak valid atau tidak ada data",
                            "",
                            "**Solusi:**",
                            "• Coba lagi dalam beberapa menit",
                            "• Pastikan MSISDN format benar (contoh: 8111992172)",
                            "• Gunakan summary report terlebih dahulu untuk verifikasi data"
                        ]
                        
                        response_text = "\n".join(error_lines)
                        log.error(f"❌ RCA failed for {target_msisdn}: {error}")
                
                except Exception as e:
                    # Fallback error handling
                    log.error(f"❌ RCA processing error: {e}")
                    response_text = f"""🚨 **RCA Processing Error**
                    
        **MSISDN:** {target_msisdn}
        **Error:** {str(e)}

        **Please try again or contact support.**"""
                
                # Single return statement
                log.info(f"⏱️ RCA RESPONSE FORMATTING: {time.time() - llm_start:.3f}s")
                
                return ChatResponse(
                    success=True,
                    response=response_text,
                    query=request.query,
                    conversation_id=conversation_id,
                    timestamp=datetime.now(),
                    tools_used=tools_used
                )
            
            else:
                # No MSISDN found - give helpful message
                helpful_message = """🔍 **Root Cause Analysis memerlukan MSISDN**

        Untuk melakukan RCA, silakan:
        1. Berikan MSISDN terlebih dahulu dengan format: `buatkan summary report msisdn 8111992172`
        2. Kemudian ketik `ya rca` untuk analisis mendalam

        Atau langsung ketik: `rca 8111992172` untuk analisis langsung."""
                
                return ChatResponse(
                    success=False,
                    response=helpful_message,
                    query=request.query,
                    conversation_id=conversation_id,
                    timestamp=datetime.now(),
                    tools_used=[]
                )
            

        # ADD THIS to orchestrator/main.py around line 400 (after RCA detection, before MBB routing)

        # CHART DETECTION - ADD THIS SECTION
        chart_patterns = [
            "chart",
            "ya chart", 
            "generate chart",
            "traffic chart",
            "visualisasi",
            "grafik"
        ]

        is_chart_request = any(pattern in request.query.lower() for pattern in chart_patterns)

        if is_chart_request:
            # Try to find MSISDN from multiple sources
            target_msisdn = None
            
            # 1. Check if MSISDN in current query
            if msisdn:
                target_msisdn = msisdn
            
            # 2. Check conversation history
            elif conversation_history:
                target_msisdn = extract_msisdn_from_conversation(conversation_history)
            
            # 3. Check session context
            elif parsed_context.get('session_context', {}).get('entities', {}).get('msisdns'):
                target_msisdn = parsed_context['session_context']['entities']['msisdns'][0]
            
            if target_msisdn:
                tool_start = time.time()
                
                log.info(f"📊 Chart Generation triggered for MSISDN: {target_msisdn}")
                
                # Use current date with proper format
                from datetime import datetime
                current_date = datetime.now()
                params = {
                    "msisdn": target_msisdn,
                    "start_time": current_date.strftime("%Y-%m-%d 00:00:00"),
                    "end_time": current_date.strftime("%Y-%m-%d 23:59:59")
                }
                
                # Execute chart generation
                tool_result = await execute_telco_tool("generate_traffic_chart", params)
                tools_used.append("generate_traffic_chart")
                
                execution_time = time.time() - tool_start
                log.info(f"⏱️ CHART TOOL EXECUTION: {execution_time:.3f}s")
                
                llm_start = time.time()
                
                if tool_result.get("success"):
                    chart_data = tool_result.get("result", {})
                    
                    if chart_data.get("success") and chart_data.get("chart_image"):
                        # Chart generation successful
                        response_text = f"""📊 **Traffic Chart Generated**

                        **MSISDN:** {target_msisdn}
                        **Period:** {params['start_time']} to {params['end_time']}
                        **Chart Type:** Traffic vs KQI Analysis

                        ![Traffic Chart](data:image/png;base64,{chart_data.get('chart_image').split(',')[1]})


                        **Insights from chart:**
                        - Peak traffic periods and KQI correlation
                        - Network performance visualization  
                        - Hourly traffic patterns
                        - Quality trends analysis

                        **Follow-up Options:**
                        - Ketik **`rca {target_msisdn}`** untuk Root Cause Analysis
                        - Ketik **`network analysis`** untuk detailed network issues"""
                        
                        log.info(f"✅ Chart generated successfully - Image size: {len(chart_data.get('chart_image', ''))//1000}KB")
                        
                    else:
                        response_text = f"""❌ **Chart Generation Failed**

        **MSISDN:** {target_msisdn}
        **Error:** {chart_data.get('error', 'Unknown error')}

        **Kemungkinan penyebab:**
        • Tidak ada data historical untuk periode tersebut
        • Format date tidak sesuai
        • API connectivity issues

        **Solusi:**
        • Coba lagi dalam beberapa menit
        • Pastikan MSISDN valid dan ada traffic data
        • Gunakan summary report terlebih dahulu"""
                else:
                    response_text = f"""❌ **Chart Tool Error**

        **MSISDN:** {target_msisdn}  
        **Error:** {tool_result.get('error', 'Unknown error')}

        **Please try again or contact support.**"""
                
                log.info(f"⏱️ CHART RESPONSE FORMATTING: {time.time() - llm_start:.3f}s")
                
                return ChatResponse(
                    success=True,
                    response=response_text,
                    query=request.query,
                    conversation_id=conversation_id,
                    timestamp=datetime.now(),
                    tools_used=tools_used
                )
            
            else:
                # No MSISDN found
                helpful_message = """📊 **Chart Generation memerlukan MSISDN**

        Untuk generate traffic chart, silakan:
        1. Berikan MSISDN terlebih dahulu dengan format: `summary report msisdn 8111689032`
        2. Kemudian ketik `chart` untuk visualisasi

        Atau langsung ketik: `chart 8111689032` untuk generate langsung."""
                
                return ChatResponse(
                    success=False,
                    response=helpful_message,
                    query=request.query,
                    conversation_id=conversation_id,
                    timestamp=datetime.now(),
                    tools_used=[]
                )


        # Enhanced MBB routing
        routing_start = time.time()
        route_to_mbb = await enhanced_should_use_mbb_knowledge(request.query, parsed_context)
        log.info(f"⏱️ ROUTING DECISION: {time.time() - routing_start:.3f}s - MBB: {route_to_mbb}")

        if route_to_mbb:
            tool_start = time.time()
            log.info("Enhanced routing to MBB knowledge base")
            
            # Context-aware parameter search
            if entities.get('parameters'):
                param_name = entities['parameters'][0]
                tool_result = await execute_mbb_tool("search_4g_parameters", {
                    "parameter_name": param_name
                })
                tools_used.append("search_4g_parameters")
            else:
                tool_result = await execute_mbb_tool("search_mbb_knowledge", {
                    "query": request.query,
                    "max_results": 2
                })
                tools_used.append("search_mbb_knowledge")
            
            log.info(f"⏱️ MBB TOOL EXECUTION: {time.time() - tool_start:.3f}s")
            
            llm_start = time.time()
            if tool_result.get("success"):
                results = tool_result.get("result", {}).get("results", [])
                
                if results:
                    param_data = results[0]
                    mbb_prompt = f"""
Berdasarkan knowledge base dan konteks percakapan:

Knowledge Base:
Parameter: {param_data.get('metadata', {}).get('parameter_name', 'Unknown')}
Deskripsi: {param_data.get('metadata', {}).get('parameter_description', '')}

Konteks: Intent={intent}, Topics={', '.join(topics)}
Query: "{request.query}"

Berikan penjelasan dalam bahasa Indonesia yang sesuai konteks.
"""
                else:
                    mbb_prompt = f"Query: {request.query}\nKonteks: Intent={intent}, Topics={topics}\nBerikan penjelasan umum."
                
                response_text = await context_manager.call_ollama_with_context(
                    mbb_prompt, conversation_history,
                    """Anda adalah expert parameter 4G/LTE yang SELALU menjawab dalam bahasa Indonesia yang natural dan mudah dipahami. 
WAJIB gunakan bahasa Indonesia untuk semua penjelasan teknis.

FORMAT RESPONSE:
- Gunakan line breaks (\n) setelah setiap poin
- Pisahkan setiap parameter dengan baris baru
- Buat struktur yang mudah dibaca"""
                )
                raw_data = tool_result
            else:
                response_text = f"Maaf, terjadi kesalahan: {tool_result.get('error')}"
            
            log.info(f"⏱️ MBB LLM RESPONSE: {time.time() - llm_start:.3f}s")
        
        elif msisdn:
            tool_start = time.time()
            # Enhanced Telco API routing
            target_date = detect_date_from_query(request.query)
            params = {
                "msisdn": msisdn,
                "start_time": target_date.strftime("%Y-%m-%d 00:00"),
                "end_time": target_date.strftime("%Y-%m-%d 23:55")
            }
            
            tool_name = "get_comprehensive_analysis"
            tools_used.append(tool_name)
            
            log.info(f"Telco analysis: {tool_name} for MSISDN: {msisdn}")
            tool_result = await execute_telco_tool(tool_name, params)
            log.info(f"⏱️ TELCO TOOL EXECUTION: {time.time() - tool_start:.3f}s")
            
            llm_start = time.time()
            if tool_result.get("success"):
                # 🎯 DIRECT USE: formatted_response sudah perfect dari telco MCP
                formatted_response = tool_result.get("result", {}).get("formatted_response")
                
                if formatted_response:
                    # Use as-is, sudah dalam format yang diinginkan
                    response_text = formatted_response
                    
                    # Enhanced follow-up instructions untuk OpenWebUI compatibility
                    response_text += "\n\n" + "="*50
                    response_text += "\n**💡 ANALISIS LANJUTAN TERSEDIA:**"
                    response_text += "\n"
                    response_text += f"\n🔍 **Root Cause Analysis:** Ketik **`rca {msisdn}`**"
                    response_text += "\n⏱️ **Waktu proses:** 2-3 menit untuk analisis mendalam"
                    response_text += "\n"
                    response_text += "\n📊 **Traffic Chart:** Ketik **`chart`** untuk visualisasi data"
                    response_text += "\n🔧 **Network Issues:** Ketik **`network analysis`** untuk troubleshooting"
                    
                    log.info("✅ Using formatted_response from telco MCP directly")
                    
                else:
                    # Fallback only if formatted_response not available
                    log.warning("⚠️ No formatted_response available, using fallback")
                    analysis_data = tool_result.get("result", {}).get("analysis", {})
                    
                    response_text = f"**Analisis MSISDN {msisdn}**\n\n"
                    
                    if analysis_data.get("insights"):
                        response_text += "**Insights:**\n"
                        for insight in analysis_data.get("insights", [])[:10]:  # Limit insights
                            response_text += f"• {insight}\n"
                        response_text += "\n"
                    
                    if analysis_data.get("metrics"):
                        response_text += "**Key Metrics:**\n"
                        for key, value in analysis_data.get("metrics", {}).items():
                            if key in ["device_model", "total_traffic_mb", "response_delay_percent", "average_rtt_ms"]:
                                formatted_key = key.replace("_", " ").title()
                                response_text += f"• {formatted_key}: {value}\n"
                        response_text += "\n"
                    
                    if analysis_data.get("recommendations"):
                        response_text += "**Rekomendasi:**\n"
                        for rec in analysis_data.get("recommendations", []):
                            response_text += f"• {rec}\n"
                    
                    # Add follow-up for fallback too
                    response_text += f"\n\n💡 Ketik **`ya rca`** untuk Root Cause Analysis mendalam"
                
                raw_data = tool_result
                
            else:
                response_text = f"❌ **Gagal menganalisis data untuk MSISDN {msisdn}**\n\nError: {tool_result.get('error')}\n\nSilakan coba dengan MSISDN yang berbeda."
            
            log.info(f"⏱️ TELCO RESPONSE READY: {time.time() - llm_start:.3f}s - Length: {len(response_text)} chars")

        else:
            llm_start = time.time()
            # General response
            general_prompt = f"""
            Konteks: Intent={intent}, Topics={', '.join(topics)}
            Pertanyaan: "{request.query}"

            Sebagai asisten NSQM telco, berikan response yang membantu dalam bahasa Indonesia.
            """
            
            response_text = await context_manager.call_ollama_with_context(
                general_prompt, conversation_history,
                """Anda adalah asisten telekomunikasi NSQM yang SELALU menjawab dalam bahasa Indonesia yang ramah dan professional. 
            WAJIB gunakan bahasa Indonesia untuk semua respons.

            FORMAT RESPONSE:
            - Gunakan line breaks (\n) setelah setiap poin
            - Pisahkan setiap parameter dengan baris baru
            - Buat struktur yang mudah dibaca"""
            )
            log.info(f"⏱️ GENERAL LLM RESPONSE: {time.time() - llm_start:.3f}s")
        
        # Save conversation
        save_start = time.time()
        processing_time = time.time() - start_time
        
        conversation_store.save_message(conversation_id, "user", request.query, {
            "intent": intent,
            "entities": entities,
            "topics": topics,
            "processing_time_ms": int(processing_time * 1000)
        })
        
        conversation_store.save_message(conversation_id, "assistant", response_text, {
            "tools_used": tools_used,
            "context_aware": True,
            "processing_time_ms": int(processing_time * 1000)
        })
        log.info(f"⏱️ SAVE CONVERSATION: {time.time() - save_start:.3f}s")
        
        total_time = time.time() - start_time
        log.info(f"🏁 TOTAL REQUEST TIME: {total_time:.3f}s")
        
        return ChatResponse(
            success=True,
            response=response_text,
            query=request.query,
            conversation_id=conversation_id,
            timestamp=datetime.now(),
            tools_used=tools_used
        )
    
    except Exception as e:
        log.error(f"Chat processing error: {str(e)}")
        error_response = f"Maaf, terjadi kesalahan: {str(e)}"
        
        conversation_store.save_message(conversation_id, "assistant", error_response, {
            "error": True,
            "error_message": str(e)
        })
        
        return ChatResponse(
            success=False,
            response=error_response,
            query=request.query,
            conversation_id=conversation_id,
            timestamp=datetime.now(),
            tools_used=[]
        )

# ✅ FIX: OpenAI endpoint function call
@app.post("/v1/chat/completions")
async def chat_completions(request: OpenAIChatRequest):
    """OpenAI compatible chat completions endpoint with conversation support"""
    
    # Extract user message
    user_message = ""
    for message in request.messages:
        if message.role == "user":
            user_message = message.content
            break
    
    if not user_message:
        user_message = "Hello"
    
    # Generate conversation ID for OpenAI compatible mode
    conversation_id = f"openai_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    try:
        # ✅ FIX: Call correct function name
        chat_request = ChatRequest(query=user_message)
        result = await chat_endpoint(conversation_id, chat_request)
        
        response_content = result.response if result.success else "Sorry, I couldn't process your request."
        tools_used = result.tools_used if hasattr(result, 'tools_used') else []
        
        # Add context about tools used
        if tools_used:
            response_content += f"\n\n*Analysis performed using: {', '.join(tools_used)}*"
        
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
        
    except Exception as e:
        log.error(f"OpenAI chat completion error: {str(e)}")
        error_content = f"An error occurred: {str(e)}"
        
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

# Keep all other endpoints exactly as they are...

# Conversation Management Endpoints
@app.get("/conversations")
async def list_conversations(limit: int = 50):
    """List recent conversations"""
    conversations = conversation_store.list_conversations(limit)
    return {
        "conversations": conversations,
        "total": len(conversations)
    }

@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get full conversation history"""
    messages = conversation_store.load_conversation(conversation_id)
    summary = conversation_store.get_conversation_summary(conversation_id)
    
    return {
        "conversation_id": conversation_id,
        "summary": summary,
        "messages": messages,
        "message_count": len(messages)
    }

@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete conversation thread"""
    success = conversation_store.delete_conversation(conversation_id)
    if success:
        return {"message": f"Conversation {conversation_id} deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Conversation not found or deletion failed")

@app.get("/conversations/{conversation_id}/summary")
async def get_conversation_summary(conversation_id: str):
    """Get conversation summary and analytics"""
    summary = conversation_store.get_conversation_summary(conversation_id)
    messages = conversation_store.load_conversation(conversation_id)
    
    if messages:
        context = ConversationAnalyzer.get_conversation_context(messages)
        summary.update(context)
    
    return summary

# Health and Status Endpoints
@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    health_status = {
        "orchestrator": "healthy",
        "conversation_mode": True,
        "timestamp": datetime.now().isoformat(),
        "conversation_store": conversation_store.get_health_status(),
        "context_manager": context_manager.get_cache_stats(),
        "servers": {},
        "active_conversations": len(conversation_store.list_conversations(1000))
    }
    
    # Check Redis connection
    try:
        conversation_store.redis_client.ping()
        health_status["redis"] = "connected"
    except:
        health_status["redis"] = "disconnected"
    
    # Check Ollama connectivity
    try:
        test_response = await context_manager.call_ollama_with_context("Test", [])
        health_status["ollama_service"] = len(test_response) > 0
    except:
        health_status["ollama_service"] = False
    
    # Check MCP servers
    for server_name, server_url in MCP_SERVERS.items():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{server_url}/health", timeout=5.0)
                health_status["servers"][server_name] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            health_status["servers"][server_name] = "unreachable"
    
    return health_status


@app.post("/conversations/{conversation_id}/analyze")
async def analyze_conversation(conversation_id: str):
    """Analyze conversation patterns and extract insights"""
    messages = conversation_store.load_conversation(conversation_id)
    
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    analysis = ConversationAnalyzer.get_conversation_context(messages)
    return {
        "conversation_id": conversation_id,
        "analysis": analysis,
        "recommendations": await _get_conversation_recommendations(messages)
    }

async def _get_conversation_recommendations(messages: List[Dict]) -> List[str]:
    """Generate recommendations based on conversation analysis"""
    recommendations = []
    
    # Analyze conversation patterns
    context = ConversationAnalyzer.get_conversation_context(messages)
    
    if "telco_analysis" in context.get("active_topics", []):
        recommendations.append("Consider setting up automated monitoring for the analyzed MSISDN")
    
    if "4g_optimization" in context.get("active_topics", []):
        recommendations.append("Review parameter optimization impact after implementation")
    
    if context.get("message_count", 0) > 20:
        recommendations.append("Long conversation detected - consider summarizing key findings")
    
    return recommendations

@app.get("/")
async def root():
    return {
        "message": "MCP Orchestrator - Conversation Mode",
        "version": "2.0.0",
        "features": ["claude_style_conversations", "full_context_awareness", "ollama_integration"],
        "endpoints": {
            "chat": "/chat/{conversation_id}",
            "conversations": "/conversations",
            "health": "/health",
            "openai_compatible": "/v1/chat/completions"
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("Starting MCP Orchestrator - Conversation Mode on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)