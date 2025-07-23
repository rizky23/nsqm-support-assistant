# shared/utils/context_manager.py
import httpx
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

log = logging.getLogger(__name__)

class OllamaContextManager:
    """Manages conversation context for Ollama with smart token management"""
    
    def __init__(self, ollama_url: str = "http://host.docker.internal:11434"):
        self.ollama_url = ollama_url
        self.max_context_tokens = 6000  # Safe limit for Llama3 8K context
        self.summary_cache = {}  # Cache summaries to avoid regeneration
    
    async def format_conversation_for_ollama(
        self, 
        conversation_history: List[Dict], 
        current_query: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """Format full conversation for Ollama with smart context management"""
        
        # Estimate token count (rough approximation: 1 token ≈ 4 characters)
        def estimate_tokens(text: str) -> int:
            return len(text) // 4
        
        # Build system prompt
        if system_prompt:
            context = f"System: {system_prompt}\n\n"
        else:
            context = """System: Anda adalah asisten analisis telekomunikasi yang ahli dalam menganalisis data jaringan dan parameter 4G/LTE, dan SELALU menjawab dalam bahasa Indonesia yang natural, mudah dipahami, dan professional. 

EXPERTISE ANDA:
- Analisis parameter 4G/LTE (RSRP, RSRQ, SINR, dll)
- Optimasi jaringan telekomunikasi
- Troubleshooting masalah konektivitas
- Interpretasi data traffic dan performance

ATURAN PENTING:
- WAJIB menggunakan bahasa Indonesia dalam semua respons
- TIDAK BOLEH menggunakan bahasa Inggris 
- Jelaskan konsep teknis dengan cara yang mudah dipahami
- Berikan solusi praktis untuk masalah telekomunikasi

"""
        
        # If conversation is short, include everything
        if len(conversation_history) <= 6:
            context += "Conversation History:\n"
            for msg in conversation_history:
                context += f"{msg['role']}: {msg['content']}\n"
            context += f"\nuser: {current_query}\nassistant:"
            return context
        
        # For longer conversations, use smart context management
        return await self._manage_long_conversation(conversation_history, current_query, context)
    
    async def _manage_long_conversation(
        self, 
        conversation_history: List[Dict], 
        current_query: str, 
        base_context: str
    ) -> str:
        """Handle long conversations with summarization"""
        
        # Always keep last 4 exchanges (8 messages) full
        recent_messages = conversation_history[-8:] if len(conversation_history) > 8 else conversation_history
        older_messages = conversation_history[:-8] if len(conversation_history) > 8 else []
        
        # Create or get cached summary for older messages
        if older_messages:
            cache_key = self._get_cache_key(older_messages)
            
            if cache_key in self.summary_cache:
                summary = self.summary_cache[cache_key]
                log.info("Using cached conversation summary")
            else:
                summary = await self._create_conversation_summary(older_messages)
                self.summary_cache[cache_key] = summary
                log.info("Created new conversation summary")
            
            context = base_context
            context += f"Previous Conversation Summary:\n{summary}\n\n"
            context += "Recent Messages:\n"
        else:
            context = base_context + "Conversation History:\n"
        
        # Add recent messages
        for msg in recent_messages:
            context += f"{msg['role']}: {msg['content']}\n"
        
        # Add current query
        context += f"\nuser: {current_query}\nassistant:"
        
        return context
    
    async def _create_conversation_summary(self, messages: List[Dict]) -> str:
        """Create a summary of older conversation parts"""
        
        # Format messages for summarization
        messages_text = ""
        for msg in messages:
            messages_text += f"{msg['role']}: {msg['content']}\n"
        
        summary_prompt = f"""Ringkas percakapan berikut dalam 3-4 kalimat. Fokus pada:
1. Topik utama yang dibahas
2. MSISDN atau device yang dianalisis (jika ada)
3. Parameter 4G atau masalah jaringan yang diidentifikasi
4. Kesimpulan atau rekomendasi penting

Percakapan:
{messages_text}

Ringkasan singkat:"""
        
        try:
            summary = await self._call_ollama_for_summary(summary_prompt)
            return summary.strip()
        except Exception as e:
            log.error(f"Failed to create summary: {e}")
            # Fallback: simple truncation
            return f"Percakapan membahas topik telekomunikasi dengan {len(messages)} pesan sebelumnya."
    
    async def _call_ollama_for_summary(self, prompt: str) -> str:
        """Call Ollama specifically for summarization"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": "llama3:latest",
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,     # ← Reduce from 0.3 (faster)
                            "max_tokens": 80,       # ← Reduce from 200 (shorter)
                            "top_p": 0.5,          # ← Reduce from 0.8 (faster)
                            "top_k": 10,           # ← Add (faster sampling)
                            "num_ctx": 1024        # ← Add (smaller context)
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["response"]
                else:
                    log.error(f"Ollama summary failed: HTTP {response.status_code}")
                    return "Summary unavailable"
                    
        except Exception as e:
            log.error(f"Ollama summary call failed: {e}")
            return "Summary unavailable"
    
    def _get_cache_key(self, messages: List[Dict]) -> str:
        """Generate cache key for message sequence"""
        # Use hash of timestamps and content length for cache key
        key_data = []
        for msg in messages:
            key_data.append(f"{msg.get('timestamp', '')}-{len(msg.get('content', ''))}")
        return hash(tuple(key_data))
    
    async def call_ollama_with_context(
        self, 
        query: str, 
        conversation_history: List[Dict],
        system_prompt: Optional[str] = None,
        model: str = "llama3:latest"
    ) -> str:
        """Main function to call Ollama with full conversation context"""
        
        # Format conversation with smart context management
        full_prompt = await self.format_conversation_for_ollama(
            conversation_history, 
            query, 
            system_prompt
        )
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.5,
                            "top_k": 15,
                            "top_p": 0.7,
                            "num_ctx": 2048,  # Max context for Llama3
                            "num_predict": 600,     # ← Add (limit response length)
                            "repeat_penalty": 1.05, # ← Reduce from 1.1
                            "num_thread": 6         # ← Add (CPU optimization)
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    response_text = result["response"].strip()
                    
                    log.info(f"Ollama response generated: {len(response_text)} characters")
                    return response_text
                else:
                    log.error(f"Ollama API error: {response.status_code}")
                    return "Maaf, terjadi kesalahan saat memproses respons."
                    
        except httpx.TimeoutException:
            log.error("Ollama request timeout")
            return "Maaf, respons memakan waktu terlalu lama. Silakan coba lagi."
        except Exception as e:
            log.error(f"Ollama call failed: {e}")
            return "Maaf, layanan AI sedang tidak tersedia."
    
    def clear_summary_cache(self):
        """Clear the summary cache"""
        self.summary_cache = {}
        log.info("Summary cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self.summary_cache),
            "max_context_tokens": self.max_context_tokens,
            "ollama_url": self.ollama_url
        }

class ConversationAnalyzer:
    """Analyze conversation patterns and extract insights"""
    
    @staticmethod
    def extract_entities(conversation_history: List[Dict]) -> Dict[str, Any]:
        """Extract entities from entire conversation"""
        import re
        
        entities = {
            "msisdns": set(),
            "devices": set(),
            "parameters": set(),
            "topics": set()
        }
        
        # Patterns for entity extraction
        msisdn_patterns = [
            r'\b(08\d{8,11})\b',
            r'\b(82\d{9,12})\b', 
            r'\b(81\d{8,11})\b',
            r'\b(\d{10,13})\b'
        ]
        
        device_pattern = r'\b(?:REALME|SAMSUNG|XIAOMI|OPPO|VIVO|IPHONE|HUAWEI)\s+[A-Z0-9\s]+(?:PLUS|PRO|LITE|MAX)?\b'
        param_pattern = r'\b[A-Z][a-zA-Z0-9]*(?:Rsrp|Rsrq|Sinr|Thld|B1|B2)\b'
        
        for msg in conversation_history:
            content = msg.get("content", "")
            
            # Extract MSISDNs
            for pattern in msisdn_patterns:
                matches = re.findall(pattern, content)
                entities["msisdns"].update(matches)
            
            # Extract devices
            device_matches = re.findall(device_pattern, content, re.IGNORECASE)
            entities["devices"].update([d.strip() for d in device_matches])
            
            # Extract 4G parameters
            param_matches = re.findall(param_pattern, content)
            entities["parameters"].update(param_matches)
            
            # Determine topics
            content_lower = content.lower()
            if any(word in content_lower for word in ["traffic", "analisis", "device"]):
                entities["topics"].add("telco_analysis")
            if any(word in content_lower for word in ["parameter", "4g", "optimize"]):
                entities["topics"].add("4g_optimization")
            if any(word in content_lower for word in ["masalah", "error", "lambat"]):
                entities["topics"].add("troubleshooting")
        
        # Convert sets to lists for JSON serialization
        return {k: list(v) for k, v in entities.items()}
    
    @staticmethod
    def get_conversation_context(conversation_history: List[Dict]) -> Dict[str, Any]:
        """Get comprehensive conversation context"""
        if not conversation_history:
            return {}
        
        entities = ConversationAnalyzer.extract_entities(conversation_history)
        
        return {
            "message_count": len(conversation_history),
            "duration_minutes": ConversationAnalyzer._calculate_duration(conversation_history),
            "entities": entities,
            "last_msisdn": entities["msisdns"][-1] if entities["msisdns"] else None,
            "last_device": entities["devices"][-1] if entities["devices"] else None,
            "active_topics": entities["topics"],
            "conversation_flow": ConversationAnalyzer._analyze_flow(conversation_history)
        }
    
    @staticmethod
    def _calculate_duration(conversation_history: List[Dict]) -> float:
        """Calculate conversation duration in minutes"""
        try:
            if len(conversation_history) < 2:
                return 0
            
            first_time = datetime.fromisoformat(conversation_history[0]["timestamp"])
            last_time = datetime.fromisoformat(conversation_history[-1]["timestamp"])
            
            duration = (last_time - first_time).total_seconds() / 60
            return round(duration, 2)
        except:
            return 0
    
    @staticmethod
    def _analyze_flow(conversation_history: List[Dict]) -> List[str]:
        """Analyze conversation flow patterns"""
        flow = []
        
        for i, msg in enumerate(conversation_history):
            if msg["role"] == "user":
                content = msg["content"].lower()
                
                if any(word in content for word in ["parameter", "4g", "optimize"]):
                    flow.append("parameter_query")
                elif any(word in content for word in ["cek", "analisis", "traffic"]):
                    flow.append("telco_analysis")
                elif any(word in content for word in ["masalah", "error", "lambat"]):
                    flow.append("troubleshooting")
                elif any(word in content for word in ["hai", "hello", "terima kasih"]):
                    flow.append("greeting")
                else:
                    flow.append("general")
        
        return flow
    
    @staticmethod
    def detect_intent(query: str, conversation_context: Dict = None) -> str:
        """Detect user intent from query and context"""
        query_lower = query.lower()
        
        intent_keywords = {
            "analysis": ["analisis", "cek", "check", "lihat", "data", "traffic"],
            "troubleshoot": ["masalah", "error", "lambat", "tidak bisa", "gagal"],
            "optimization": ["optimize", "optimasi", "improve", "tingkatkan"],
            "parameter": ["parameter", "setting", "nilai", "value", "threshold"],
            "comparison": ["bandingkan", "compare", "vs", "dengan", "trend"]
        }
        
        # Score each intent
        intent_scores = {}
        for intent, keywords in intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score > 0:
                intent_scores[intent] = score
        
        # Context-based enhancement
        if conversation_context:
            last_topics = conversation_context.get("active_topics", [])
            if "4g_optimization" in last_topics and "parameter" in intent_scores:
                intent_scores["parameter"] += 1
        
        return max(intent_scores, key=intent_scores.get) if intent_scores else "general"
    
    @staticmethod
    def enhanced_extract_entities(conversation_history: List[Dict]) -> Dict[str, Any]:
        """Enhanced entity extraction with more patterns"""
        import re
        
        entities = {
            "msisdns": set(),
            "devices": set(), 
            "parameters": set(),
            "cell_ids": set(),
            "topics": set()
        }
        
        # Enhanced patterns
        msisdn_patterns = [
            r'\b(08\d{8,11})\b',
            r'\b(82\d{9,12})\b', 
            r'\b(81\d{8,11})\b'
        ]
        
        # Enhanced parameter patterns
        param_patterns = [
            r'\b[A-Z][a-zA-Z0-9]*(?:Rsrp|Rsrq|Sinr|Thld|A4|A5|B1|B2|Ho|Quan|Sw|Offset)\b',
            r'\b(?:InterFreq|IntraFreq|CellResel|HandOver|Mobility)\w*\b'
        ]
        
        # Cell ID patterns
        cell_patterns = [
            r'\b(?:eNodeB|Cell|BTS)[\s_-]?(\w+)\b',
            r'\b(Site\d+)\b'
        ]
        
        for msg in conversation_history:
            content = msg.get("content", "")
            
            # Extract MSISDNs
            for pattern in msisdn_patterns:
                matches = re.findall(pattern, content)
                entities["msisdns"].update(matches)
            
            # Extract parameters (enhanced)
            for pattern in param_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                entities["parameters"].update(matches)
            
            # Extract cell IDs
            for pattern in cell_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                entities["cell_ids"].update([m for m in matches if m])
            
            # Topic detection (enhanced)
            content_lower = content.lower()
            if any(word in content_lower for word in ["traffic", "analisis", "msisdn"]):
                entities["topics"].add("telco_analysis")
            if any(word in content_lower for word in ["parameter", "4g", "rsrp", "optimize"]):
                entities["topics"].add("4g_optimization")
            if any(word in content_lower for word in ["masalah", "error", "lambat"]):
                entities["topics"].add("troubleshooting")
        
        return {k: list(v) for k, v in entities.items()}
    
    @staticmethod
    async def classify_query_intent(query: str, conversation_context: Dict = None, ollama_url: str = "http://host.docker.internal:11434") -> Dict[str, Any]:
        """
        LLM-based query classification untuk smart routing menggunakan bahasa Indonesia
        Returns classification dengan confidence scores
        """
        
        # Build context untuk LLM
        context_info = ""
        if conversation_context:
            topics = conversation_context.get("active_topics", [])
            entities = conversation_context.get("entities", {})
            if topics:
                context_info += f"Topik sebelumnya: {', '.join(topics)}\n"
            if entities.get("msisdns"):
                context_info += f"Nomor yang dibahas: {', '.join(entities['msisdns'][-2:])}\n"
            if entities.get("parameters"):
                context_info += f"Parameter yang dibahas: {', '.join(entities['parameters'][-3:])}\n"
        
        # Indonesian LLM Classification Prompt
        classification_prompt = f"""Kamu adalah ahli telekomunikasi. Analisis query ini dan tentukan kategori yang tepat.

Query: "{query}"

Konteks percakapan sebelumnya:
{context_info if context_info else "Tidak ada konteks sebelumnya"}

Kategorikan ke dalam SATU kategori utama:

1. ANALISIS_TELCO - User ingin analisis nomor telepon tertentu (traffic, performa, info device, trend penggunaan)
2. PENGETAHUAN_PARAMETER - User ingin belajar tentang parameter teknis 4G/LTE (RSRP, handover, setting optimasi)
3. DUKUNGAN_UMUM - Pertanyaan umum, sapaan, atau maksud tidak jelas

Pertimbangkan pola ini:
- Jika ada nomor telepon + kata-kata analisis → ANALISIS_TELCO
- Jika ada nama parameter teknis atau konsep 4G/LTE → PENGETAHUAN_PARAMETER
- Selainnya → DUKUNGAN_UMUM

Berikan jawaban dalam format PERSIS seperti ini:
KATEGORI: [nama_kategori]
KEYAKINAN: [0.0-1.0]
ALASAN: [penjelasan singkat mengapa dipilih kategori ini]
ENTITAS: [sebutkan nomor telepon, parameter, atau istilah teknis yang ditemukan]"""

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": "llama3:latest",
                        "prompt": classification_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.05,    # ← Very low for consistent classification
                            "max_tokens": 120,      # ← Reduce from 300
                            "top_p": 0.5,          # ← Reduce from 0.8
                            "top_k": 5,            # ← Add (fastest sampling)
                            "num_ctx": 1024,       # ← Add (smaller context)
                            "repeat_penalty": 1.0  # ← Add (no penalty)
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    llm_response = result["response"].strip()
                    
                    # Parse LLM response
                    return ConversationAnalyzer._parse_indonesian_classification(llm_response, query)
                else:
                    # Fallback ke simple entity detection
                    return ConversationAnalyzer._simple_entity_fallback(query)
                    
        except Exception as e:
            # Fallback ke simple entity detection
            return ConversationAnalyzer._simple_entity_fallback(query)
    
    @staticmethod
    def _parse_indonesian_classification(llm_response: str, original_query: str) -> Dict[str, Any]:
        """Parse structured LLM classification response dalam bahasa Indonesia"""
        
        classification = {
            "intent": "DUKUNGAN_UMUM",
            "confidence": 0.5,
            "reasoning": "Klasifikasi default",
            "entities": [],
            "should_use_mbb": False,
            "recommended_server": "general",
            "query": original_query
        }
        
        try:
            lines = llm_response.split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith("KATEGORI:"):
                    intent = line.replace("KATEGORI:", "").strip()
                    classification["intent"] = intent
                elif line.startswith("KEYAKINAN:"):
                    confidence_str = line.replace("KEYAKINAN:", "").strip()
                    try:
                        classification["confidence"] = float(confidence_str)
                    except:
                        classification["confidence"] = 0.5
                elif line.startswith("ALASAN:"):
                    reasoning = line.replace("ALASAN:", "").strip()
                    classification["reasoning"] = reasoning
                elif line.startswith("ENTITAS:"):
                    entities_str = line.replace("ENTITAS:", "").strip()
                    if entities_str and entities_str != "-" and entities_str.lower() != "tidak ada":
                        classification["entities"] = [e.strip() for e in entities_str.split(',') if e.strip()]
            
            # Map Indonesian intent to server routing
            if classification["intent"] == "ANALISIS_TELCO":
                classification["should_use_mbb"] = False
                classification["recommended_server"] = "telco"
            elif classification["intent"] == "PENGETAHUAN_PARAMETER":
                classification["should_use_mbb"] = True
                classification["recommended_server"] = "mbb"
            else:
                classification["should_use_mbb"] = False
                classification["recommended_server"] = "general"
                
        except Exception as e:
            # Keep default values jika parsing gagal
            classification["reasoning"] = f"Error parsing LLM response: {str(e)}"
        
        return classification
    
    @staticmethod
    def _simple_entity_fallback(query: str) -> Dict[str, Any]:
        """Simple fallback classification ketika LLM tidak tersedia"""
        
        # Deteksi entitas sederhana sebagai fallback
        import re
        
        # Deteksi nomor telepon Indonesia
        phone_patterns = [
            r'\b08\d{8,11}\b',  # Format 08xxx
            r'\b82\d{9,12}\b',  # Format 82xxx  
            r'\b81\d{8,11}\b'   # Format 81xxx
        ]
        
        found_phones = []
        for pattern in phone_patterns:
            matches = re.findall(pattern, query)
            found_phones.extend(matches)
        
        classification = {
            "intent": "DUKUNGAN_UMUM",
            "confidence": 0.3,
            "reasoning": "Fallback classification - LLM tidak tersedia",
            "entities": found_phones,
            "should_use_mbb": False,
            "recommended_server": "general",
            "query": query
        }
        
        # Jika ada nomor telepon, likely adalah analisis telco
        if found_phones:
            classification.update({
                "intent": "ANALISIS_TELCO",
                "confidence": 0.7,
                "reasoning": "Nomor telepon terdeteksi dalam query",
                "recommended_server": "telco"
            })
        
        return classification
    
    @staticmethod
    async def should_use_mbb_knowledge(query: str, conversation_context: Dict = None) -> bool:
        """
        Updated method menggunakan LLM classification
        """
        try:
            classification = await ConversationAnalyzer.classify_query_intent(query, conversation_context)
            return classification["should_use_mbb"]
        except Exception as e:
            # Fallback ke entity detection sederhana
            fallback = ConversationAnalyzer._simple_entity_fallback(query)
            return fallback["should_use_mbb"]
    
    @staticmethod
    async def get_detailed_routing_analysis(query: str, conversation_context: Dict = None) -> Dict[str, Any]:
        """
        Method baru untuk mendapatkan analisis routing yang detail
        Berguna untuk debugging dan monitoring
        """
        classification = await ConversationAnalyzer.classify_query_intent(query, conversation_context)
        
        # Tambahkan informasi debug
        classification["routing_decision"] = {
            "selected_server": classification["recommended_server"],
            "confidence_level": "high" if classification["confidence"] > 0.7 else "medium" if classification["confidence"] > 0.4 else "low",
            "context_used": bool(conversation_context),
            "entities_found": len(classification["entities"]),
            "timestamp": datetime.now().isoformat()
        }
        
        return classification
    
    # Add these methods to ConversationAnalyzer class in context_manager.py

    @staticmethod
    async def classify_topic_change(query: str, conversation_history: List[Dict], ollama_url: str = "http://host.docker.internal:11434") -> bool:
        """LLM determines if this is a new topic"""
        
        if not conversation_history:
            return False  # No history = no topic change
        
        # Get last few messages for context
        recent_context = ""
        for msg in conversation_history[-3:]:
            recent_context += f"{msg['role']}: {msg['content']}\n"
        
        classification_prompt = f"""
    Analisis apakah query baru ini adalah topik yang COMPLETELY DIFFERENT dari percakapan sebelumnya.

    Percakapan sebelumnya:
    {recent_context if recent_context else "Tidak ada percakapan sebelumnya"}

    Query baru: "{query}"

    Apakah ini topik yang SANGAT BERBEDA? 
    - Parameter teknis vs performance metrics = BERBEDA
    - Network analysis vs device info = BERBEDA  
    - Technical discussion vs general questions = BERBEDA
    - RTT/latency questions vs parameter optimization = BERBEDA

    Jika topik SANGAT BERBEDA, jawab: TOPIK_BARU
    Jika masih related atau similar, jawab: TOPIK_SAMA

    Jawab hanya: TOPIK_BARU atau TOPIK_SAMA
    """

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": "llama3:latest",
                        "prompt": classification_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.05,    # ← Very low (deterministic)
                            "max_tokens": 20,       # ← Very short (just TOPIK_BARU/SAMA)
                            "top_k": 3,            # ← Very low (fastest)
                            "num_ctx": 512,        # ← Very small context
                            "repeat_penalty": 1.0  # ← No penalty                            
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()["response"].strip()
                    is_new_topic = "TOPIK_BARU" in result.upper()
                    log.info(f"Topic change detection: {result} -> {is_new_topic}")
                    return is_new_topic
                
        except Exception as e:
            log.error(f"Topic classification failed: {e}")
        
        return False  # Default: keep context

    @staticmethod
    async def generate_contextual_system_prompt(query: str, conversation_history: List[Dict], ollama_url: str = "http://host.docker.internal:11434") -> str:
        """LLM generates appropriate system prompt based on query"""
        
        prompt_generation = f"""
    Berdasarkan query: "{query}"

    Generate system prompt yang tepat untuk AI assistant yang membantu telekomunikasi.

    Guidelines:
    - Jika tentang RTT/latency/performance → Network performance expert
    - Jika tentang parameter 4G/LTE → Technical parameter expert  
    - Jika tentang traffic/data usage → Data analysis expert
    - Jika pertanyaan umum → General telco support

    Buat system prompt dalam bahasa Indonesia yang spesifik dan fokus.
    Maksimal 3 kalimat. Mulai dengan "Anda adalah..."
    """

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": "llama3:latest",
                        "prompt": prompt_generation,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,     # ← Reduce from 0.3
                            "max_tokens": 80,       # ← Reduce from 150
                            "top_k": 10,           # ← Add
                            "num_ctx": 1024,       # ← Add (smaller context)
                            "repeat_penalty": 1.0  # ← Add                            
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()["response"].strip()
                    log.info(f"Generated contextual system prompt: {result[:100]}...")
                    return result
                
        except Exception as e:
            log.error(f"System prompt generation failed: {e}")
        
        # Fallback
        return """Anda adalah asisten telekomunikasi yang ahli dalam analisis jaringan dan membantu pengguna dengan pertanyaan teknis dalam bahasa Indonesia yang mudah dipahami."""

    

class SimpleSessionManager:
    """Simple session management with timeout"""
    
    def __init__(self, timeout_minutes: int = 30):
        self.sessions = {}
        self.timeout_minutes = timeout_minutes
    
    def get_session_context(self, conversation_id: str) -> Dict[str, Any]:
        """Get session context with timeout check"""
        from datetime import datetime, timedelta
        
        if conversation_id in self.sessions:
            session = self.sessions[conversation_id]
            last_activity = datetime.fromisoformat(session['last_activity'])
            
            # Check timeout
            if datetime.now() - last_activity > timedelta(minutes=self.timeout_minutes):
                # Session expired, reset
                del self.sessions[conversation_id]
                return {}
            else:
                # Update activity
                session['last_activity'] = datetime.now().isoformat()
                return session.get('context', {})
        
        return {}
    
    def update_session_context(self, conversation_id: str, entities: Dict, intent: str, topics: List[str]):
        """Update session context"""
        from datetime import datetime
        
        if conversation_id not in self.sessions:
            self.sessions[conversation_id] = {
                'created_at': datetime.now().isoformat(),
                'context': {}
            }
        
        session = self.sessions[conversation_id]
        session['last_activity'] = datetime.now().isoformat()
        
        # Update context
        context = session['context']
        context['last_intent'] = intent
        context['active_topics'] = topics[-3:] if topics else []  # Keep last 3 topics
        
        # Merge entities
        if 'entities' not in context:
            context['entities'] = {}
        
        for entity_type, values in entities.items():
            if entity_type not in context['entities']:
                context['entities'][entity_type] = []
            
            # Add new unique values
            existing = set(context['entities'][entity_type])
            new_values = set(values) if isinstance(values, list) else {values}
            context['entities'][entity_type] = list(existing.union(new_values))
    
    def cleanup_expired_sessions(self) -> int:
        """Clean expired sessions"""
        from datetime import datetime, timedelta
        
        expired = []
        cutoff = datetime.now() - timedelta(minutes=self.timeout_minutes)
        
        for session_id, session in self.sessions.items():
            last_activity = datetime.fromisoformat(session['last_activity'])
            if last_activity < cutoff:
                expired.append(session_id)
        
        for session_id in expired:
            del self.sessions[session_id]
        
        return len(expired)