# shared/utils/simple_memory.py
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from shared.utils.logger import log

class SimpleConversationMemory:
    """Simple memory yang cek raw_data dari previous queries - completely generic"""
    
    def __init__(self):
        self.llm_query_cache = {}  # Cache untuk LLM analysis
    
    async def check_previous_data(self, conversation_store, conversation_id: str, 
                          new_query: str) -> Optional[Dict[str, Any]]:
        """
        Cek apakah ada raw_data di conversation sebelumnya yang bisa answer new_query
        Completely generic - no hardcoded patterns
        """
        
        try:
            # Load existing conversation history
            messages = conversation_store.load_conversation(conversation_id)
            
            if not messages:
                return None
            
            # Cari messages yang punya raw_data_available
            for message in reversed(messages):  # Start from latest
                if (message.get("role") == "assistant" and 
                    message.get("metadata", {}).get("raw_data_available")):
                    
                    # Get the raw_data reference
                    raw_data_ref = message.get("metadata", {}).get("raw_data")
                    
                    if raw_data_ref:
                        # Try to extract answer using LLM reasoning
                        answer = await self._llm_extract_answer(raw_data_ref, new_query, message)
                        
                        if answer:
                            log.info(f"Found answer in memory for: {new_query}")
                            return {
                                "success": True,
                                "answer": answer,
                                "source": "memory",
                                "original_query": self._get_original_query(message, messages),
                                "from_timestamp": message.get("timestamp"),
                                "raw_data_used": True
                            }
            
            return None
            
        except Exception as e:
            log.error(f"Memory check failed: {e}")
            return None
    
    async def _llm_extract_answer(self, raw_data: Dict, new_query: str, 
                                original_message: Dict) -> Optional[str]:
        """Use LLM untuk extract answer dari raw_data - no hardcoded patterns"""
        
        try:
            # Create cache key
            cache_key = f"{hash(str(raw_data))}_{hash(new_query)}"
            
            if cache_key in self.llm_query_cache:
                return self.llm_query_cache[cache_key]
            
            # Build prompt untuk LLM
            extraction_prompt = self._build_extraction_prompt(raw_data, new_query, original_message)
            
            # Call LLM (using existing Ollama infrastructure)
            extracted_answer = await self._call_llm_for_extraction(extraction_prompt)
            
            # Cache result
            self.llm_query_cache[cache_key] = extracted_answer
            
            return extracted_answer
            
        except Exception as e:
            log.error(f"LLM extraction failed: {e}")
            return None
    
    def _build_extraction_prompt(self, raw_data: Dict, new_query: str, 
                               original_message: Dict) -> str:
        """Build prompt untuk LLM extraction - completely dynamic"""
        
        # Get context dari original conversation
        original_response = original_message.get("content", "")
        
        prompt = f"""
Analyze the following data and determine if it contains information to answer the new question.

PREVIOUS CONVERSATION:
User asked something and system responded: "{original_response}"

RAW DATA from that response:
{json.dumps(raw_data, indent=2)}

NEW QUESTION: "{new_query}"

TASK:
1. Check if the raw data contains information that can answer the new question
2. If yes, extract the specific answer from the raw data
3. If no, respond with "NO_ANSWER_FOUND"

RULES:
- Only use information that is explicitly present in the raw data
- Be specific and direct in your answer
- Don't make assumptions or add information not in the data
- Answer in the same language as the question

ANSWER:"""

        return prompt
    
    async def _call_llm_for_extraction(self, prompt: str) -> Optional[str]:
        """Call LLM untuk extraction using existing Ollama setup"""
        
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://host.docker.internal:11434/api/generate",
                    json={
                        "model": "llama3:latest",
                        "prompt": prompt,
                        "stream": False
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result.get("response", "").strip()
                    
                    # Check if LLM found an answer
                    if "NO_ANSWER_FOUND" in answer.upper():
                        return None
                    
                    return answer
                
                return None
                
        except Exception as e:
            log.error(f"LLM call failed: {e}")
            return None
    
    def _get_original_query(self, message: Dict, all_messages: List[Dict]) -> str:
        """Get original user query yang triggered this response"""
        
        try:
            # Find the user message right before this assistant message
            message_timestamp = message.get("timestamp")
            
            for i, msg in enumerate(all_messages):
                if (msg.get("timestamp") == message_timestamp and 
                    msg.get("role") == "assistant"):
                    # Look for previous user message
                    if i > 0 and all_messages[i-1].get("role") == "user":
                        return all_messages[i-1].get("content", "")
            
            return ""
            
        except Exception as e:
            log.error(f"Original query extraction failed: {e}")
            return ""

class MemoryIntegrationHelper:
    """Helper untuk integrate memory check dengan existing orchestrator"""
    
    def __init__(self, conversation_store):
        self.conversation_store = conversation_store
        self.memory = SimpleConversationMemory()
    
    async def check_memory_first(self, conversation_id: str, user_query: str) -> Optional[Dict]:
        """
        Check memory first sebelum call external APIs
        Returns answer from memory atau None jika perlu call external
        """
        
        return await self.memory.check_previous_data(
            self.conversation_store, 
            conversation_id, 
            user_query
        )
    
    def should_save_raw_data(self, tools_used: List[str]) -> bool:
        """Determine if response should save raw_data untuk future reference"""
        
        # Save raw_data if external tools were used
        external_tools = [
            "search_mbb_knowledge", 
            "search_4g_parameters",
            "get_comprehensive_analysis",
            "analyze_network_issues"
        ]
        
        return any(tool in tools_used for tool in external_tools)

# Integration instructions untuk existing orchestrator/main.py:

"""
INTEGRATION STEPS:

1. Add import di main.py:
   from shared.utils.simple_memory import MemoryIntegrationHelper

2. Initialize helper di chat_endpoint function:
   memory_helper = MemoryIntegrationHelper(conversation_store)

3. Add memory check BEFORE external tool calls:
   
   # NEW: Check memory first
   memory_result = await memory_helper.check_memory_first(conversation_id, request.query)
   
   if memory_result:
       # Use answer from memory
       response_text = memory_result["answer"]
       tools_used = ["memory"]
       raw_data = None
   else:
       # Continue with existing logic (MBB, telco API, etc)
       # ... existing code ...

4. EXISTING save_message calls remain unchanged - no modifications needed

5. The system will automatically:
   - Check memory first for every query
   - Use LLM to intelligently extract answers from previous raw_data
   - Fall back to external calls if no memory match
   - Work with ANY type of raw_data (telco, MBB, future APIs)

EXAMPLE FLOW:
User: "8111992172" -> Call telco API -> Save with raw_data
User: "device support 5G?" -> Check memory -> LLM extracts from previous raw_data -> Answer without new API call

NO HARDCODED PATTERNS - LLM figures out what data is relevant!
"""