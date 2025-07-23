import httpx
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from shared.utils.logger import log
from shared.utils.config import settings

class vLLMService:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.model_name = "Qwen/Qwen2.5-7B-Instruct"
        self.available_tools = {}
        self.conversation_history = []
    
    def register_tools(self, tools: Dict[str, Dict[str, Any]]):
        """Register available MCP tools"""
        self.available_tools = tools
        log.info(f"Registered {len(tools)} tools for LLM")
    
    async def chat_with_tools(self, user_query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Main entry point for natural language queries with tool usage"""
        try:
            # Step 1: Parse and understand the query
            parsed_query = self._parse_user_query(user_query)
            log.info(f"Parsed query: {parsed_query}")
            
            # Step 2: Select appropriate tools
            selected_tools = await self._select_tools(parsed_query, user_query)
            
            # Step 3: Execute tools if needed
            tool_results = {}
            if selected_tools:
                tool_results = await self._execute_tools(selected_tools, parsed_query)
            
            # Step 4: Generate natural language response
            response = await self._generate_response(user_query, parsed_query, tool_results)
            
            return {
                "success": True,
                "user_query": user_query,
                "parsed_query": parsed_query,
                "tools_used": list(tool_results.keys()),
                "response": response,
                "raw_data": tool_results
            }
            
        except Exception as e:
            log.error(f"Chat with tools failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": "Maaf, terjadi kesalahan saat memproses permintaan Anda."
            }
    
    def _parse_user_query(self, query: str) -> Dict[str, Any]:
        """Extract entities and intent from user query"""
        parsed = {
            "msisdn": None,
            "date_range": None,
            "intent": "general",
            "keywords": [],
            "entities": {}
        }
        
        # Extract MSISDN (Indonesian phone numbers)
        msisdn_patterns = [
            r'\b(08\d{8,11})\b',  # 08xxxxxxxxxx
            r'\b(62\d{9,12})\b',  # 62xxxxxxxxxx
            r'\b(\+62\d{9,12})\b'  # +62xxxxxxxxxx
        ]
        
        for pattern in msisdn_patterns:
            match = re.search(pattern, query)
            if match:
                parsed["msisdn"] = match.group(1)
                break
        
        # Extract date references
        date_keywords = {
            "hari ini": 0,
            "kemarin": -1,
            "lusa": -2,
            "minggu lalu": -7,
            "bulan lalu": -30
        }
        
        for keyword, days_offset in date_keywords.items():
            if keyword in query.lower():
                end_date = datetime.now() + timedelta(days=days_offset)
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_time = end_date.replace(hour=23, minute=59, second=59, microsecond=0)
                
                parsed["date_range"] = {
                    "start_time": start_date.strftime("%Y-%m-%d %H:%M"),
                    "end_time": end_time.strftime("%Y-%m-%d %H:%M")
                }
                break
        
        # Detect intent based on keywords
        intent_keywords = {
            "troubleshoot": ["lambat", "bermasalah", "error", "tidak bisa", "gagal", "lemot", "lag"],
            "analysis": ["analisis", "cek", "lihat", "periksa", "bagaimana", "berapa"],
            "comparison": ["bandingkan", "compare", "vs", "versus", "beda"],
            "history": ["riwayat", "history", "sejarah", "pola", "trend"],
            "recommendation": ["saran", "rekomendasi", "solusi", "perbaikan", "cara"]
        }
        
        query_lower = query.lower()
        for intent, keywords in intent_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                parsed["intent"] = intent
                parsed["keywords"].extend([kw for kw in keywords if kw in query_lower])
                break
        
        # Extract technical terms
        tech_keywords = ["traffic", "latency", "throughput", "signal", "device", "network", "quality"]
        parsed["keywords"].extend([kw for kw in tech_keywords if kw in query_lower])
        
        return parsed
    
    async def _select_tools(self, parsed_query: Dict[str, Any], original_query: str) -> List[Dict[str, Any]]:
        """Select appropriate tools based on parsed query"""
        selected_tools = []
        
        msisdn = parsed_query.get("msisdn")
        date_range = parsed_query.get("date_range")
        intent = parsed_query.get("intent")
        
        # If no MSISDN and no specific intent, search knowledge base
        if not msisdn and intent in ["general", "recommendation"]:
            selected_tools.append({
                "server": "vector_db",
                "tool": "search_knowledge_base",
                "params": {
                    "query": original_query,
                    "max_results": 5
                }
            })
            return selected_tools
        
        # If MSISDN provided, prepare for API calls
        if msisdn and date_range:
            base_params = {
                "msisdn": msisdn,
                "start_time": date_range["start_time"],
                "end_time": date_range["end_time"]
            }
            
            # Select tools based on intent
            if intent == "troubleshoot":
                selected_tools.extend([
                    {
                        "server": "telco",
                        "tool": "analyze_network_issues",
                        "params": base_params
                    },
                    {
                        "server": "vector_db",
                        "tool": "get_issue_recommendations",
                        "params": {
                            "issue_description": original_query
                        }
                    }
                ])
            
            elif intent == "analysis":
                selected_tools.append({
                    "server": "telco",
                    "tool": "get_comprehensive_analysis",
                    "params": base_params
                })
            
            elif intent == "comparison":
                selected_tools.extend([
                    {
                        "server": "telco",
                        "tool": "get_comprehensive_analysis",
                        "params": base_params
                    },
                    {
                        "server": "vector_db",
                        "tool": "search_knowledge_base",
                        "params": {
                            "query": f"analisis {msisdn}",
                            "max_results": 3
                        }
                    }
                ])
            
            else:  # Default comprehensive analysis
                selected_tools.append({
                    "server": "telco",
                    "tool": "get_comprehensive_analysis",
                    "params": base_params
                })
        
        elif msisdn and not date_range:
            # Default to yesterday if no date specified
            yesterday = datetime.now() - timedelta(days=1)
            start_time = yesterday.replace(hour=0, minute=0, second=0).strftime("%Y-%m-%d %H:%M")
            end_time = yesterday.replace(hour=23, minute=59, second=59).strftime("%Y-%m-%d %H:%M")
            
            selected_tools.append({
                "server": "telco",
                "tool": "get_comprehensive_analysis",
                "params": {
                    "msisdn": msisdn,
                    "start_time": start_time,
                    "end_time": end_time
                }
            })
        
        return selected_tools
    
    async def _execute_tools(self, tools: List[Dict[str, Any]], parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """Execute selected tools and collect results"""
        results = {}
        
        for tool_config in tools:
            server = tool_config["server"]
            tool_name = tool_config["tool"]
            params = tool_config["params"]
            
            try:
                # Determine server URL
                if server == "telco":
                    url = "http://localhost:8001/call"
                elif server == "vector_db":
                    url = "http://localhost:8002/call"
                else:
                    continue
                
                # Execute tool
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, json={
                        "tool": tool_name,
                        "params": params
                    })
                    
                    if response.status_code == 200:
                        result = response.json()
                        results[f"{server}_{tool_name}"] = result.get("result", {})
                        log.info(f"Tool {server}.{tool_name} executed successfully")
                    else:
                        log.error(f"Tool {server}.{tool_name} failed with status {response.status_code}")
                        results[f"{server}_{tool_name}"] = {"error": f"HTTP {response.status_code}"}
            
            except Exception as e:
                log.error(f"Tool execution failed {server}.{tool_name}: {e}")
                results[f"{server}_{tool_name}"] = {"error": str(e)}
        
        return results
    
    async def _generate_response(self, original_query: str, parsed_query: Dict[str, Any], tool_results: Dict[str, Any]) -> str:
        """Generate natural language response using vLLM"""
        try:
            # Prepare context for LLM
            context = self._prepare_context(original_query, parsed_query, tool_results)
            
            # Create prompt for response generation
            prompt = self._create_response_prompt(original_query, context)
            
            # Call vLLM for response generation
            response = await self._call_vllm(prompt)
            
            return response
            
        except Exception as e:
            log.error(f"Response generation failed: {e}")
            return self._generate_fallback_response(parsed_query, tool_results)
    
    def _prepare_context(self, original_query: str, parsed_query: Dict[str, Any], tool_results: Dict[str, Any]) -> str:
        """Prepare context from tool results"""
        context_parts = []
        
        # Add query context
        msisdn = parsed_query.get("msisdn")
        if msisdn:
            context_parts.append(f"MSISDN: {msisdn}")
        
        date_range = parsed_query.get("date_range")
        if date_range:
            context_parts.append(f"Periode: {date_range['start_time']} - {date_range['end_time']}")
        
        # Add tool results
        for tool_name, result in tool_results.items():
            if isinstance(result, dict) and "error" not in result:
                context_parts.append(f"\n--- {tool_name.upper()} ---")
                
                if "telco" in tool_name:
                    # Format telco analysis results
                    analysis = result.get("analysis", {})
                    insights = analysis.get("insights", [])
                    recommendations = analysis.get("recommendations", [])
                    metrics = analysis.get("metrics", {})
                    
                    if insights:
                        context_parts.append("Insights:")
                        for insight in insights[:5]:  # Limit to top 5
                            context_parts.append(f"- {insight}")
                    
                    if recommendations:
                        context_parts.append("Rekomendasi:")
                        for rec in recommendations[:3]:  # Limit to top 3
                            context_parts.append(f"- {rec}")
                    
                    if metrics:
                        context_parts.append("Metrics penting:")
                        for key, value in list(metrics.items())[:5]:
                            context_parts.append(f"- {key}: {value}")
                
                elif "vector_db" in tool_name:
                    # Format knowledge base results
                    if "search" in tool_name:
                        results = result.get("results", [])
                        if results:
                            context_parts.append("Kasus serupa ditemukan:")
                            for res in results[:3]:
                                score = res.get("relevance_score", 0)
                                snippet = res.get("document_snippet", "")
                                context_parts.append(f"- (Relevance: {score:.2f}) {snippet[:200]}...")
                    
                    elif "recommendations" in tool_name:
                        recs = result.get("recommendations", [])
                        if recs:
                            context_parts.append("Rekomendasi berdasarkan kasus serupa:")
                            for rec in recs[:3]:
                                context_parts.append(f"- {rec}")
        
        return "\n".join(context_parts)
    
    def _create_response_prompt(self, original_query: str, context: str) -> str:
        """Create prompt for natural language response generation"""
        prompt = f"""Anda adalah asisten analisis telekomunikasi yang membantu menganalisis data jaringan dan memberikan insight.

Pertanyaan pengguna: "{original_query}"

Data dan analisis yang tersedia:
{context}

Tugas Anda:
1. Jawab pertanyaan pengguna dengan bahasa yang natural dan mudah dipahami
2. Gunakan data yang tersedia untuk memberikan insight yang akurat
3. Berikan rekomendasi praktis jika diperlukan
4. Sebutkan metrics penting dalam bentuk yang mudah dibaca
5. Jika ada masalah, jelaskan kemungkinan penyebab dan solusinya

Format jawaban:
- Gunakan bahasa Indonesia
- Ringkas tapi informatif
- Highlight poin-poin penting
- Berikan action items jika perlu

Jawaban:"""

        return prompt
    
    async def _call_vllm(self, prompt: str) -> str:
        """Call Ollama API for text generation"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False
                    },
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["response"].strip()
                else:
                    log.error(f"Ollama API error: {response.status_code}")
                    return "Maaf, terjadi kesalahan saat memproses respons."
        
        except Exception as e:
            log.error(f"Ollama call failed: {e}")
            return "Maaf, layanan AI sedang tidak tersedia."
    
    def _generate_fallback_response(self, parsed_query: Dict[str, Any], tool_results: Dict[str, Any]) -> str:
        """Generate simple fallback response without LLM"""
        response_parts = []
        
        msisdn = parsed_query.get("msisdn")
        if msisdn:
            response_parts.append(f"Analisis untuk MSISDN {msisdn}:")
        
        # Extract key information from results
        for tool_name, result in tool_results.items():
            if isinstance(result, dict) and "error" not in result:
                if "telco" in tool_name:
                    analysis = result.get("analysis", {})
                    insights = analysis.get("insights", [])
                    if insights:
                        response_parts.append("\nInsight utama:")
                        for insight in insights[:3]:
                            response_parts.append(f"• {insight}")
                
                elif "vector_db" in tool_name and "search" in tool_name:
                    results = result.get("results", [])
                    if results:
                        response_parts.append(f"\nDitemukan {len(results)} kasus serupa.")
        
        if not response_parts:
            return "Analisis selesai, namun tidak ditemukan insight spesifik untuk query Anda."
        
        return "\n".join(response_parts)
    
    async def health_check(self) -> bool:
        """Check if vLLM service is available"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/v1/models")
                return response.status_code == 200
        except:
            return False