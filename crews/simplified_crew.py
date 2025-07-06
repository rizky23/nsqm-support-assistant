# crews/simplified_crew.py
import time
import re
import requests
from typing import Dict, Any
from memory.session_manager import SessionManager
from workflows.detail_workflow import DetailWorkflow
from workflows.summary_workflow import SummaryWorkflow
from workflows.followup_workflow import FollowupWorkflow
from workflows.knowledge_workflow import KnowledgeWorkflow
from workflows.smartcare_workflow import SmartCareWorkflow

class SimplifiedCrew:
    """Simplified CrewAI crew for ticket analysis with direct database access"""
    
    # Workflow Types
    WORKFLOW_TYPES = {
        "detail": "Individual ticket/MSISDN lookup",
        "summary": "Aggregated data analysis with narratives",
        "list": "Display complaint examples",
        "count": "Simple counting queries",
        "smartcare": "Real-time MSISDN analysis with API data",
        "followup": "Context-aware follow-up queries",
        "off_topic": "Non-system related queries",
        "system_inquiry": "System capability questions"
    }
    
    def __init__(self, shared_db_tool=None):
        """Initialize workflows with SHARED database tool"""
        print("🤖 Initializing SimplifiedCrew with shared DB...")

        # Store shared database tool
        self.shared_db_tool = shared_db_tool
        
        try:
            # Pass shared_db_tool ke SEMUA workflows - BUKAN None!
            self.detail_workflow = DetailWorkflow(shared_db_tool)
            self.summary_workflow = SummaryWorkflow(shared_db_tool) 
            self.followup_workflow = FollowupWorkflow(shared_db_tool)
            self.smartcare_workflow = SmartCareWorkflow()
            self.knowledge_workflow = KnowledgeWorkflow()  # No DB needed
            self.session_manager = SessionManager()
            
            if shared_db_tool:
                print("✅ SimplifiedCrew initialized with SHARED database connection")
            else:
                print("⚠️ SimplifiedCrew initialized WITHOUT database connection")
            
        except Exception as e:
            print(f"❌ SimplifiedCrew initialization failed: {str(e)}")
            raise e
    
    def execute_query(self, crew_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute query through simplified workflow system"""
        try:
            user_query = crew_input.get("user_query", "")
            session_id = crew_input.get("session_id", "")
            
            print(f"[{session_id}] SimplifiedCrew processing: {user_query[:50]}...")
            
            # Step 1: Classification and follow-up detection
            classification_result = self._classify_query(user_query, session_id)
            
            # Step 2: Handle different classification results
            if classification_result.get("intent_category") == "system_prompt":
                return self._create_standard_response("system_prompt", {
                    "response": "System prompt skipped",
                    "status": "system_prompt"
                })
            
            elif classification_result.get("intent_category") == "followup_enhanced":
                result = self._handle_followup_enhanced_query(user_query, classification_result, session_id)
                self._save_session_interaction(session_id, user_query, result, "followup")
                return self._create_standard_response("followup", result)
            
            elif classification_result.get("intent_category") == "knowledge_query":
                result = self._handle_knowledge_query(user_query, classification_result, session_id)
                self._save_session_interaction(session_id, user_query, result, "knowledge")
                return self._create_standard_response("knowledge", result)
            
            elif classification_result.get("intent_category") == "off_topic":
                result = self._handle_off_topic_query(user_query, classification_result, session_id)
                return self._create_standard_response("off_topic", result)
            
            elif classification_result.get("intent_category") == "system_inquiry":
                result = self._handle_system_inquiry(user_query, classification_result, session_id)
                return self._create_standard_response("system_inquiry", result)
            
            elif classification_result.get("intent_category") == "smartcare_query":
                result = self.smartcare_workflow.execute(user_query, session_id)
                self._save_session_interaction(session_id, user_query, result, "smartcare")
                return self._create_standard_response("smartcare", result)  # ✅ workflow="smartcare"
            
            # Step 3: Analyze workflow type for data queries
            workflow_type = self._analyze_query_type(user_query)
            print(f"[{session_id}] Workflow type: {workflow_type}")
            
            # Step 4: Route to appropriate workflow with error handling
            try:
                result = self._route_workflow(workflow_type, crew_input)
            except ZeroDivisionError as zde:
                print(f"[{session_id}] Division by zero in {workflow_type} workflow: {str(zde)}")
                return self._create_standard_response("error", {
                    "response": "Maaf, terjadi kesalahan perhitungan. Data mungkin kosong atau tidak valid untuk analisis ini.",
                    "status": "calculation_error",
                    "error": f"Division by zero in {workflow_type} workflow"
                })
            except Exception as we:
                print(f"[{session_id}] Workflow error in {workflow_type}: {str(we)}")
                return self._create_standard_response("error", {
                    "response": f"Maaf, terjadi kesalahan dalam workflow {workflow_type}: {str(we)}",
                    "status": "workflow_error", 
                    "error": str(we)
                })
            
            # Step 5: Save session interaction
            self._save_session_interaction(session_id, user_query, result, workflow_type)
            
            return self._create_standard_response(workflow_type, result)
                
        except Exception as e:
            print(f"[{session_id}] SimplifiedCrew execution error: {str(e)}")
            return self._create_standard_response("error", {
                "response": f"Maaf, terjadi kesalahan dalam memproses query: {str(e)}",
                "status": "error",
                "error": str(e)
            })
    
    # def _classify_query(self, user_query: str, session_id: str) -> Dict[str, Any]:
    #     """Enhanced LLM-based classification with follow-up detection"""
    #     try:
    #         print(f"[{session_id}] 🧠 Starting classification: '{user_query}'")

    #         # System prompt skip - highest priority
    #         if "### Task:" in user_query or "follow-up questions" in user_query:
    #             print(f"[{session_id}] ⏭️ Skipping system follow-up prompt")
    #             return {
    #                 "intent_category": "system_prompt",
    #                 "confidence": 1.0,
    #                 "reasoning": "System follow-up generation prompt - skip"
    #             }
            
    #         # Check for follow-up context FIRST
    #         session_context = self.session_manager.get_context_for_followup(session_id, user_query)
            
    #         if session_context["is_followup"]:
    #             print(f"[{session_id}] 🔄 FOLLOW-UP DETECTED - BYPASSING LLM CLASSIFICATION")
    #             print(f"[{session_id}] Previous: {session_context['previous_query'][:50]}...")
                
    #             # Enhance query with context using LLM
    #             enhanced_result = self._enhance_followup_with_llm(user_query, session_context, session_id)
    #             return enhanced_result
            
    #         # Continue with LLM classification only if NOT follow-up
    #         print(f"[{session_id}] No follow-up detected, proceeding with LLM classification")
    #         try:
    #             return self._llm_classify(user_query, session_id)
    #         except Exception as llm_error:
    #             print(f"[{session_id}] LLM Error: {str(llm_error)}")
    #             return self._fallback_classification(user_query, session_id)
                
    #     except Exception as e:
    #         print(f"[{session_id}] Classification error: {str(e)}")
    #         return self._fallback_classification(user_query, session_id)

    # def _classify_query(self, user_query: str, session_id: str) -> Dict[str, Any]:
    #     """Enhanced LLM-based classification with follow-up detection"""
    #     try:
    #         print(f"[{session_id}] 🧠 Starting classification: '{user_query}'")

    #         # System prompt skip - highest priority
    #         if "### Task:" in user_query or "follow-up questions" in user_query:
    #             print(f"[{session_id}] ⏭️ Skipping system follow-up prompt")
    #             return {
    #                 "intent_category": "system_prompt",
    #                 "confidence": 1.0,
    #                 "reasoning": "System follow-up generation prompt - skip"
    #             }
            
    #         # HARD RULES OVERRIDE - sebelum follow-up dan LLM
    #         query_lower = user_query.lower()
            
    #         # Knowledge keywords - prioritas tinggi untuk stabilitas
    #         knowledge_keywords = [
    #             'parameter','cara', 'bagaimana', 'gimana', 'jelaskan', 'explain', 
    #             'apa itu', 'what is', 'pengertian', 'definisi', 'arti',
    #             'tutorial', 'panduan', 'guide', 'langkah', 'prosedur',
    #             'troubleshoot', 'troubleshooting', 'solusi', 'solve'
    #         ]
            
    #         if any(keyword in query_lower for keyword in knowledge_keywords):
    #             print(f"[{session_id}] 🎯 HARD RULE: Knowledge keywords detected")
    #             return {
    #                 "is_ticket_related": True,
    #                 "relevance_score": 0.95,
    #                 "intent_category": "knowledge_query",
    #                 "confidence": 0.95,
    #                 "reasoning": "Hard rule: knowledge keywords detected"
    #             }
            
    #         # System inquiry keywords
    #         system_keywords = [
    #             'siapa kamu', 'kamu apa', 'apa kemampuan', 'bisa apa',
    #             'sistem sehat', 'ada masalah', 'status sistem'
    #         ]
            
    #         if any(keyword in query_lower for keyword in system_keywords):
    #             print(f"[{session_id}] 🎯 HARD RULE: System inquiry detected")
    #             return {
    #                 "is_ticket_related": True,
    #                 "relevance_score": 0.95,
    #                 "intent_category": "system_inquiry", 
    #                 "confidence": 0.95,
    #                 "reasoning": "Hard rule: system inquiry keywords"
    #             }
            
    #         # Check for follow-up context
    #         session_context = self.session_manager.get_context_for_followup(session_id, user_query)
            
    #         if session_context["is_followup"]:
    #             print(f"[{session_id}] 🔄 FOLLOW-UP DETECTED - BYPASSING LLM CLASSIFICATION")
    #             enhanced_result = self._enhance_followup_with_llm(user_query, session_context, session_id)
    #             return enhanced_result
            
    #         # Continue with LLM classification dengan temperature 0
    #         print(f"[{session_id}] No hard rules matched, proceeding with LLM classification")
    #         try:
    #             return self._llm_classify(user_query, session_id)
    #         except Exception as llm_error:
    #             print(f"[{session_id}] LLM Error: {str(llm_error)}")
    #             return self._fallback_classification(user_query, session_id)
                    
    #     except Exception as e:
    #         print(f"[{session_id}] Classification error: {str(e)}")
    #         return self._fallback_classification(user_query, session_id)


    def _classify_query(self, user_query: str, session_id: str) -> Dict[str, Any]:
        """Enhanced LLM-based classification with follow-up detection"""
        try:
            print(f"[{session_id}] 🧠 Starting classification: '{user_query}'")

            # System prompt skip - highest priority
            if "### Task:" in user_query or "follow-up questions" in user_query:
                print(f"[{session_id}] ⏭️ Skipping system follow-up prompt")
                return {
                    "intent_category": "system_prompt",
                    "confidence": 1.0,
                    "reasoning": "System follow-up generation prompt - skip"
                }
            
            # 🎯 MSISDN PRIORITY - CHECK FIRST BEFORE FOLLOW-UP
            import re
            msisdn_pattern = r'\b(08\d{8,11}|628\d{8,11}|\+628\d{8,11})\b'
            if re.search(msisdn_pattern, user_query):
                print(f"[{session_id}] 🎯 MSISDN DETECTED - FORCING SMARTCARE")
                return {
                    "is_ticket_related": True,
                    "relevance_score": 0.98,
                    "intent_category": "smartcare_query",
                    "confidence": 0.98,
                    "reasoning": "MSISDN detected - SmartCare priority"
                }
            
            # HARD RULES OVERRIDE (rest of the existing code...)
            query_lower = user_query.lower()
            
            # Knowledge keywords
            knowledge_keywords = [
                'parameter','cara', 'bagaimana', 'gimana', 'jelaskan', 'explain', 
                'apa itu', 'what is', 'pengertian', 'definisi', 'arti',
                'tutorial', 'panduan', 'guide', 'langkah', 'prosedur',
                'troubleshoot', 'troubleshooting', 'solusi', 'solve'
            ]
            
            if any(keyword in query_lower for keyword in knowledge_keywords):
                print(f"[{session_id}] 🎯 HARD RULE: Knowledge keywords detected")
                return {
                    "is_ticket_related": True,
                    "relevance_score": 0.95,
                    "intent_category": "knowledge_query",
                    "confidence": 0.95,
                    "reasoning": "Hard rule: knowledge keywords detected"
                }
            
            # Check for follow-up context (AFTER MSISDN check)
            session_context = self.session_manager.get_context_for_followup(session_id, user_query)
            
            if session_context["is_followup"]:
                print(f"[{session_id}] 🔄 FOLLOW-UP DETECTED - BYPASSING LLM CLASSIFICATION")
                enhanced_result = self._enhance_followup_with_llm(user_query, session_context, session_id)
                return enhanced_result
            
            # Continue with LLM classification
            print(f"[{session_id}] No hard rules matched, proceeding with LLM classification")
            try:
                return self._llm_classify(user_query, session_id)
            except Exception as llm_error:
                print(f"[{session_id}] LLM Error: {str(llm_error)}")
                return self._fallback_classification(user_query, session_id)
                    
        except Exception as e:
            print(f"[{session_id}] Classification error: {str(e)}")
            return self._fallback_classification(user_query, session_id)




    
    def _llm_classify(self, user_query: str, session_id: str) -> Dict[str, Any]:
        """LLM classification using Ollama"""
        classification_prompt = f"""
Anda adalah classifier untuk sistem analisis keluhan pelanggan telekomunikasi.

KONTEKS SISTEM:
- Database berisi keluhan pelanggan telekomunikasi (internet, wifi, jaringan, billing, sinyal)
- Data tersimpan per lokasi geografis (provinsi, kota, kecamatan, daerah)
- Sistem dapat melakukan: analisis statistik, summary/ringkasan, counting, pencarian contoh
- Sistem dapat menjawab pertanyaan tentang data keluhan dan capabilities

QUERY USER: "{user_query}"

TUGAS: Klasifikasi query berdasarkan RELEVANSI dengan sistem keluhan telekomunikasi.

LOGIKA KLASIFIKASI:

SMARTCARE = Query yang butuh data real-time MSISDN dari API:
- Mengandung nomor MSISDN (08xxx, 628xxx, 8xxx format)
- Permintaan data usage/traffic individual ("cek 08111992172", "detil 628xxx")
- Analisis historis per nomor ("riwayat 08111992172 hari ini")
- Status real-time user ("kondisi 628xxx sekarang")
- Visualisasi data individual ("grafik 08111992172 kemarin")

COMPLAINT = Query yang BISA dijawab dengan data keluhan telco:
- Mencari informasi/statistik keluhan berdasarkan lokasi atau waktu
- Analisis data keluhan (summary, trend, pola, perbandingan)
- Counting/jumlah keluhan di area tertentu
- Contoh kasus keluhan dari daerah tertentu
- Pertanyaan tentang jenis masalah telco (internet, sinyal, wifi)
- Query geografis + konteks telco (Jakarta + internet/keluhan/berapa)

KNOWLEDGE_QUERY = Query tentang troubleshooting, SOP, atau prosedur:
- Pertanyaan cara mengatasi masalah teknis ("bagaimana troubleshoot internet lambat")
- Request panduan atau prosedur ("apa sop handle keluhan prioritas tinggi")
- Pertanyaan parameter teknis ("berapa nilai RSRP yang bagus")
- Best practices atau rekomendasi

SYSTEM_INQUIRY = Query tentang sistem/AI ini:
- Pertanyaan tentang kemampuan sistem ("apa yang bisa kamu lakukan")
- Status sistem ("apakah kamu sehat", "ada masalah dengan sistem")
- Identitas sistem ("siapa kamu", "kamu AI apa")

OFF_TOPIC = Query yang TIDAK BISA dijawab dengan data keluhan telco:
- Orang/selebriti/politikus (siapa itu suharto, jokowi, biografi tokoh)
- Makanan/restoran (nasi padang, cafe, resep masakan)
- Hiburan (film, musik, game, olahraga)
- Cuaca, belanja, topik umum yang tidak ada hubungan dengan telco
- Pertanyaan personal umum tanpa konteks telekomunikasi

JAWAB DALAM FORMAT:
CLASSIFICATION: [SMARTCARE/COMPLAINT/KNOWLEDGE_QUERY/SYSTEM_INQUIRY/OFF_TOPIC]
CONFIDENCE: [0.1-1.0]
REASONING: [jelaskan mengapa masuk kategori ini berdasarkan konteks]

CONTOH:
- "detil 08111992172 2 jam lalu" → CLASSIFICATION: SMARTCARE, CONFIDENCE: 0.95, REASONING: Mengandung MSISDN dengan request data historis individual
- "cek 628111992172 jam 10" → CLASSIFICATION: SMARTCARE, CONFIDENCE: 0.95, REASONING: Request data real-time untuk nomor spesifik
- "berapa keluhan di Jakarta?" → CLASSIFICATION: COMPLAINT, CONFIDENCE: 0.95, REASONING: Analisis geografis keluhan dari database
- "cara troubleshoot internet lambat" → CLASSIFICATION: KNOWLEDGE_QUERY, CONFIDENCE: 0.9, REASONING: Request panduan teknis telco
"""

        try:
            llm_response = requests.post("http://host.docker.internal:11434/api/generate", 
                json={
                    "model": "llama3",
                    "prompt": classification_prompt,
                    "stream": False,
                    "options": {"temperature": 0.0}
                })
            
            if llm_response.status_code != 200:
                raise Exception(f"Ollama API error: {llm_response.status_code}")
            
            response_text = llm_response.json()["response"].strip()
            print(f"[{session_id}] LLM Response: {response_text}")
            
            # Parse LLM response
            classification_match = re.search(r'CLASSIFICATION:\s*(\w+)', response_text.upper())
            classification = classification_match.group(1).strip() if classification_match else "OFF_TOPIC"

            confidence_match = re.search(r'CONFIDENCE:\s*([\d.]+)', response_text)
            confidence = float(confidence_match.group(1)) if confidence_match else 0.7

            reasoning_match = re.search(r'REASONING:\s*(.+?)(?=\n|$)', response_text, re.IGNORECASE | re.DOTALL)
            reasoning = reasoning_match.group(1).strip() if reasoning_match else "LLM classification"

            print(f"[{session_id}] ✅ Parsed - Classification: {classification}, Confidence: {confidence}")
            
            if classification == "COMPLAINT":
                return {
                    "is_ticket_related": True,
                    "relevance_score": confidence,
                    "intent_category": "ticket_analysis", 
                    "confidence": confidence,
                    "reasoning": f"LLM: {reasoning}"
                }
            elif classification == "KNOWLEDGE_QUERY":
                return {
                    "is_ticket_related": True,
                    "relevance_score": confidence,
                    "intent_category": "knowledge_query",
                    "confidence": confidence,
                    "reasoning": f"LLM: {reasoning}"
                }
            elif classification == "SYSTEM_INQUIRY":
                return {
                    "is_ticket_related": True,
                    "relevance_score": confidence,
                    "intent_category": "system_inquiry",
                    "confidence": confidence,
                    "reasoning": f"LLM: {reasoning}"
                }
            elif classification == "SMARTCARE":
                return {
                    "is_ticket_related": True,
                    "relevance_score": confidence,
                    "intent_category": "smartcare_query",
                    "confidence": confidence,
                    "reasoning": f"LLM: {reasoning}"
                }
            else:
                return {
                    "is_ticket_related": False,
                    "relevance_score": 1.0 - confidence,
                    "intent_category": "off_topic",
                    "confidence": confidence,
                    "reasoning": f"LLM: {reasoning}"
                }
                
        except Exception as e:
            print(f"[{session_id}] LLM classification error: {str(e)}")
            raise e
    
    def _enhance_followup_with_llm(self, user_query: str, session_context: Dict, session_id: str) -> Dict[str, Any]:
        """Enhance follow-up query using LLM with previous context"""
        
        previous_query = session_context.get("previous_query", "")
        previous_entities = session_context.get("previous_entities", {})
        
        # Extract context for enhancement
        last_location = ""
        last_timeframe = ""
        complete_geo_entities = []
        
        if "geographic" in previous_entities:
            complete_geo_entities = previous_entities["geographic"]
            if complete_geo_entities:
                last_location = complete_geo_entities[0].get("value", "")
        
        if "temporal" in previous_entities:
            temp_entity = previous_entities["temporal"][0] if previous_entities["temporal"] else {}
            last_timeframe = temp_entity.get("value", "")
        
        prompt = f"""
Analyze follow-up query dengan context sebelumnya:

CONTEXT SEBELUMNYA:
- Query: "{previous_query}"
- Lokasi: "{last_location}"  
- Waktu: "{last_timeframe}"
- Type: "{session_context.get('previous_query_type', '')}"

FOLLOW-UP QUERY: "{user_query}"

ATURAN INTENT UNTUK FOLLOW-UP:
- "berikan contohnya", "tampilkan contoh", "show examples" → INTENT: list
- "berapa total", "jumlah berapa" → INTENT: count  
- "detail lebih", "informasi lengkap" → INTENT: detail
- "ringkasan", "summary", "laporan" → INTENT: summary

Tentukan:
1. Intent: [summary/list/detail/count] 
2. Inherit lokasi: [yes/no]
3. Inherit waktu: [yes/no] 
4. Filter tambahan: [status filter, dll]

Format jawaban:
INTENT: list
INHERIT_LOCATION: yes
INHERIT_TIME: yes
LOCATION: {last_location if last_location else "N/A"}
TIMEFRAME: {last_timeframe if last_timeframe else "N/A"}
FILTERS: [additional conditions]
"""

        try:
            llm_response = requests.post("http://host.docker.internal:11434/api/generate", 
                json={
                    "model": "llama3",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.0}
                })
            
            if llm_response.status_code == 200:
                response_text = llm_response.json()["response"]
                enhanced_context = self._parse_followup_enhancement(response_text, last_location, last_timeframe)
                enhanced_context["complete_geo_entities"] = complete_geo_entities
                
                print(f"[{session_id}] 🤖 LLM Enhanced: {enhanced_context}")
                
                return {
                    "is_ticket_related": True,
                    "relevance_score": 0.9,
                    "intent_category": "followup_enhanced",
                    "confidence": 0.9,
                    "reasoning": "Follow-up query enhanced with LLM",
                    "enhanced_context": enhanced_context,
                    "original_context": session_context
                }
        
        except Exception as e:
            print(f"[{session_id}] LLM Enhancement error: {str(e)}")
        
        # Fallback
        return {
            "is_ticket_related": True,
            "relevance_score": 0.8,
            "intent_category": "followup_enhanced",
            "confidence": 0.8,
            "reasoning": "Simple follow-up detection",
            "enhanced_context": {
                "intent": "list",
                "inherit_location": True,
                "inherit_time": True,
                "location": last_location,
                "timeframe": last_timeframe,
                "complete_geo_entities": complete_geo_entities
            },
            "original_context": session_context
        }
    
    def _parse_followup_enhancement(self, llm_response: str, actual_location: str = "", actual_timeframe: str = "") -> Dict[str, Any]:
        """Parse LLM response for follow-up enhancement"""
        enhancement = {
            "intent": "list",
            "inherit_location": False,
            "inherit_time": False,
            "location": "",
            "timeframe": "",
            "filters": "",
            "complete_geo_entities": []
        }
        
        try:
            # Extract intent
            intent_match = re.search(r'INTENT:\s*(\w+)', llm_response, re.IGNORECASE)
            if intent_match:
                enhancement["intent"] = intent_match.group(1).lower()
            
            # Extract inherit flags
            inherit_loc_match = re.search(r'INHERIT_LOCATION:\s*(yes|no)', llm_response, re.IGNORECASE)
            if inherit_loc_match:
                enhancement["inherit_location"] = inherit_loc_match.group(1).lower() == "yes"
                if enhancement["inherit_location"]:
                    enhancement["location"] = actual_location
            
            inherit_time_match = re.search(r'INHERIT_TIME:\s*(yes|no)', llm_response, re.IGNORECASE)
            if inherit_time_match:
                enhancement["inherit_time"] = inherit_time_match.group(1).lower() == "yes"
                if enhancement["inherit_time"]:
                    enhancement["timeframe"] = actual_timeframe
            
            # Extract filters
            filters_match = re.search(r'FILTERS:\s*([^\n]+)', llm_response, re.IGNORECASE)
            if filters_match:
                enhancement["filters"] = filters_match.group(1).strip()
        
        except Exception as e:
            print(f"Parse enhancement error: {e}")
        
        return enhancement
    
    # def _fallback_classification(self, user_query: str, session_id: str) -> Dict[str, Any]:
    #     """Fallback classification if LLM fails"""
    #     print(f"[{session_id}] Using fallback classification")
        
    #     query_lower = user_query.lower()
        
    #     # TAMBAHKAN INI - Knowledge/explanation keywords (prioritas tinggi)
    #     knowledge_keywords = [
    #         'apa itu', 'jelaskan', 'explain', 'what is', 'pengertian', 
    #         'definisi', 'arti', 'maksud', 'cara', 'bagaimana', 'how to'
    #     ]
        
    #     # Check knowledge queries FIRST
    #     if any(keyword in query_lower for keyword in knowledge_keywords):
    #         return {
    #             "is_ticket_related": True,
    #             "relevance_score": 0.9,
    #             "intent_category": "knowledge_query",
    #             "confidence": 0.9,
    #             "reasoning": "Fallback: knowledge/explanation keywords detected"
    #         }
        
    #     # Simple keyword check as backup untuk complaint
    #     complaint_keywords = ['keluhan', 'masalah', 'complaint', 'tiket', 'ticket', 'cc-', 'berapa', 'contoh', 'internet', 'wifi', 'jaringan', 'summary', 'ringkasan']
    #     off_topic_keywords = ['nasi', 'padang', 'makan', 'cafe', 'restoran', 'film', 'musik', 'game', 'basket', 'beli', 'jual', 'siapa', 'cuaca']
        
    #     has_complaint = any(keyword in query_lower for keyword in complaint_keywords)
    #     has_off_topic = any(keyword in query_lower for keyword in off_topic_keywords)
        
    #     if has_complaint and not has_off_topic:
    #         return {
    #             "is_ticket_related": True,
    #             "relevance_score": 0.8,
    #             "intent_category": "ticket_analysis",
    #             "confidence": 0.8,
    #             "reasoning": "Fallback: complaint keywords detected"
    #         }
    #     else:
    #         return {
    #             "is_ticket_related": False,
    #             "relevance_score": 0.3,
    #             "intent_category": "off_topic", 
    #             "confidence": 0.7,
    #             "reasoning": "Fallback: no clear complaint keywords or off-topic detected"
    #         }

    def _fallback_classification(self, user_query: str, session_id: str) -> Dict[str, Any]:
        """Fallback classification if LLM fails"""
        print(f"[{session_id}] Using fallback classification")
        
        query_lower = user_query.lower()
        
        # PRIORITY 1: Check for MSISDN (SmartCare)
        from tools.query_parser import SmartCareQueryParser
        parser = SmartCareQueryParser()
        validation = parser.validate_query(user_query)
        
        if validation["is_smartcare_query"]:
            return {
                "is_ticket_related": True,
                "relevance_score": 0.9,
                "intent_category": "smartcare_query",
                "confidence": validation["confidence"],
                "reasoning": "Fallback: MSISDN detected in query"
            }
        
        # PRIORITY 2: Knowledge/explanation keywords
        knowledge_keywords = [
            'apa itu', 'jelaskan', 'explain', 'what is', 'pengertian', 
            'definisi', 'arti', 'maksud', 'cara', 'bagaimana', 'how to',
            'troubleshoot', 'sop', 'panduan', 'guide'
        ]
        
        if any(keyword in query_lower for keyword in knowledge_keywords):
            # Check if it has telco context
            telco_context = any(telco in query_lower for telco in [
                'internet', 'wifi', 'jaringan', 'network', 'signal', 'sinyal',
                'keluhan', 'complaint', 'tiket', 'ticket', 'telkomsel',
                'provider', 'operator', 'telekomunikasi', 'telco'
            ])
            
            if telco_context:
                return {
                    "is_ticket_related": True,
                    "relevance_score": 0.9,
                    "intent_category": "knowledge_query",
                    "confidence": 0.9,
                    "reasoning": "Fallback: knowledge keywords with telco context"
                }
            else:
                return {
                    "is_ticket_related": False,
                    "relevance_score": 0.2,
                    "intent_category": "off_topic",
                    "confidence": 0.8,
                    "reasoning": "Fallback: knowledge keywords without telco context"
                }
        
        # PRIORITY 3: System inquiry
        system_keywords = [
            'siapa kamu', 'kamu apa', 'apa kemampuan', 'bisa apa',
            'sistem sehat', 'ada masalah', 'status sistem', 'hello', 'hi'
        ]
        
        if any(keyword in query_lower for keyword in system_keywords):
            return {
                "is_ticket_related": True,
                "relevance_score": 0.95,
                "intent_category": "system_inquiry",
                "confidence": 0.95,
                "reasoning": "Fallback: system inquiry keywords"
            }
        
        # PRIORITY 4: Off-topic keywords
        off_topic_keywords = [
            'who is', 'who are', 'biography', 'biografi',
            'sejarah', 'history', 'politik', 'political',
            'nasi', 'padang', 'makan', 'cafe', 'restoran', 'makanan', 'food',
            'film', 'movie', 'musik', 'music', 'game', 'gaming',
            'basket', 'football', 'sepak bola', 'olahraga', 'sports',
            'cuaca', 'weather', 'hujan', 'panas', 'dingin',
            'beli', 'jual', 'shopping', 'belanja', 'harga', 'price'
        ]
        
        if any(keyword in query_lower for keyword in off_topic_keywords):
            return {
                "is_ticket_related": False,
                "relevance_score": 0.1,
                "intent_category": "off_topic",
                "confidence": 0.95,
                "reasoning": "Fallback: off-topic keywords detected"
            }
        
        # PRIORITY 5: Complaint keywords (ClickHouse)
        complaint_keywords = [
            'keluhan', 'masalah', 'complaint', 'tiket', 'ticket', 'berapa', 'contoh', 
            'internet', 'wifi', 'jaringan', 'summary', 'ringkasan', 'jakarta', 'bandung'
        ]
        
        if any(keyword in query_lower for keyword in complaint_keywords):
            return {
                "is_ticket_related": True,
                "relevance_score": 0.8,
                "intent_category": "ticket_analysis",
                "confidence": 0.8,
                "reasoning": "Fallback: complaint keywords detected"
            }
        
        # Default: off-topic
        return {
            "is_ticket_related": False,
            "relevance_score": 0.3,
            "intent_category": "off_topic",
            "confidence": 0.7,
            "reasoning": "Fallback: no clear classification patterns found"
        }

    
    def _analyze_query_type(self, query: str) -> str:
        """Detect workflow type from query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["summary", "ringkasan", "laporan", "rekap", "statistik"]):
            return "summary"
        elif any(word in query_lower for word in ["berapa", "jumlah", "total", "count"]):
            return "count"
        elif any(word in query_lower for word in ["tampilkan", "lihat", "show", "contoh", "list"]):
            return "list"
        elif any(word in query_lower for word in ["detail", "cc-", "order_id", "ticket"]):
            return "detail"
        else:
            return "list"  # Default
    
    # def _route_workflow(self, workflow_type: str, crew_input: Dict[str, Any]) -> Dict[str, Any]:
    #     """Route to appropriate workflow"""
    #     user_query = crew_input.get("user_query", "")
    #     session_id = crew_input.get("session_id", "")
        
    #     if workflow_type == "detail":
    #         return self.detail_workflow.execute(user_query, None, session_id)
    #     elif workflow_type == "summary":
    #         return self.summary_workflow.execute(user_query, None, session_id)
    #     elif workflow_type == "count":
    #         # ✅ FIX: Use query_builder directly for count instead of followup workflow
    #         try:
    #             from tools.smart_query_builder import SmartQueryBuilder
    #             query_builder = SmartQueryBuilder(use_direct_db=True)
    #             result = query_builder.build_and_execute(user_query)
                
    #             # Convert to standard workflow response format
    #             if result.get("execution_result", {}).get("success"):
    #                 data = result["execution_result"]["data"]
    #                 count = data[0].get('total_count', 0) if data else 0
                    
    #                 # Extract location for response
    #                 entities = result.get("entities", {})
    #                 location = "lokasi yang diminta"
    #                 time_period = "periode yang diminta"
                    
    #                 if entities.get("geographic"):
    #                     location = entities["geographic"][0].get("value", location)
    #                 if entities.get("temporal"):
    #                     if "month" in entities["temporal"][0].get("value", "").lower():
    #                         time_period = "bulan lalu" if "interval" in entities["temporal"][0].get("value", "") else "bulan ini"
                    
    #                 narrative = f"🔢 Ditemukan **{count} keluhan** di {location} {time_period}."
                    
    #                 return {
    #                     "response": narrative,
    #                     "status": "success",
    #                     "metadata": {
    #                         "sql_query": result.get("sql_query"),
    #                         "intent": result.get("intent"),
    #                         "entities": entities,
    #                         "count": count
    #                     }
    #                 }
    #             else:
    #                 error_msg = result.get("execution_result", {}).get("error", "Query failed")
    #                 return {
    #                     "response": f"❌ Gagal menghitung keluhan: {error_msg}",
    #                     "status": "error"
    #                 }
                    
    #         except Exception as e:
    #             return {
    #                 "response": f"❌ Error dalam counting: {str(e)}",
    #                 "status": "error"
    #             }
    #     else:  # list
    #         # ✅ FIX: Provide proper enhanced_context instead of empty dict
    #         enhanced_context = {
    #             "intent": workflow_type,
    #             "inherit_location": False,
    #             "inherit_time": False,
    #             "filters": ""
    #         }
    #         return self.followup_workflow._execute_list_workflow(user_query, enhanced_context, session_id)

    def _route_workflow(self, workflow_type: str, crew_input: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate workflow"""
        user_query = crew_input.get("user_query", "")
        session_id = crew_input.get("session_id", "")
        
        if workflow_type == "detail":
            return self.detail_workflow.execute(user_query, None, session_id)
        elif workflow_type == "summary":
            return self.summary_workflow.execute(user_query, None, session_id)
        elif workflow_type == "smartcare":  # NEW ROUTING
            return self.smartcare_workflow.execute(user_query, None, session_id)
        elif workflow_type == "count":
            # Direct count handling (existing code)
            try:
                from tools.smart_query_builder import SmartQueryBuilder
                query_builder = SmartQueryBuilder(use_direct_db=True)
                result = query_builder.build_and_execute(user_query)
                
                if result.get("execution_result", {}).get("success"):
                    data = result["execution_result"]["data"]
                    count = data[0].get('total_count', 0) if data else 0
                    
                    entities = result.get("entities", {})
                    location = "lokasi yang diminta"
                    time_period = "periode yang diminta"
                    
                    if entities.get("geographic"):
                        location = entities["geographic"][0].get("value", location)
                    if entities.get("temporal"):
                        if "month" in entities["temporal"][0].get("value", "").lower():
                            time_period = "bulan lalu" if "interval" in entities["temporal"][0].get("value", "") else "bulan ini"
                    
                    narrative = f"🔢 Ditemukan **{count} keluhan** di {location} {time_period}."
                    
                    return {
                        "response": narrative,
                        "status": "success",
                        "metadata": {
                            "sql_query": result.get("sql_query"),
                            "intent": result.get("intent"),
                            "entities": entities,
                            "count": count
                        }
                    }
                else:
                    error_msg = result.get("execution_result", {}).get("error", "Query failed")
                    return {
                        "response": f"❌ Gagal menghitung keluhan: {error_msg}",
                        "status": "error"
                    }
                    
            except Exception as e:
                return {
                    "response": f"❌ Error dalam counting: {str(e)}",
                    "status": "error"
                }
        else:  # list
            enhanced_context = {
                "intent": workflow_type,
                "inherit_location": False,
                "inherit_time": False,
                "filters": ""
            }
            return self.followup_workflow._execute_list_workflow(user_query, enhanced_context, session_id)
    
    def _handle_followup_enhanced_query(self, user_query: str, classification_result: Dict, session_id: str) -> Dict[str, Any]:
        """Handle follow-up queries with enhanced context"""
        enhanced_context = classification_result.get("enhanced_context", {})
        return self.followup_workflow.execute(user_query, enhanced_context, session_id)
    
    def _handle_knowledge_query(self, user_query: str, classification_result: Dict, session_id: str) -> Dict[str, Any]:
        """Handle knowledge-based queries using RAG"""
        try:
            return self.knowledge_workflow.execute(user_query, None, session_id)
        except Exception as e:
            print(f"[{session_id}] Knowledge workflow error: {str(e)}")
            
            # Fallback response untuk knowledge queries
            query_lower = user_query.lower()
            
            if "dsc" in query_lower:
                return {
                    "response": """DSC dalam konteks telekomunikasi dapat merujuk pada beberapa hal:

                    1. **Data Service Center** - Pusat layanan data
                    2. **Digital Service Center** - Pusat layanan digital  
                    3. **Direct Service Channel** - Saluran layanan langsung
                    4. **Digital Signature Certificate** - Sertifikat tanda tangan digital

                    Dalam konteks sistem ini, DSC biasanya merujuk pada komponen layanan pelanggan atau sistem internal.

                    Apakah Anda memerlukan informasi lebih spesifik tentang DSC dalam konteks tertentu?""",
                                    "status": "knowledge_fallback"
                }
            else:
                return {
                    "response": f"Maaf, saya memerlukan informasi lebih spesifik untuk menjelaskan '{user_query}'. Bisakah Anda memberikan konteks yang lebih detail?",
                    "status": "knowledge_fallback"
                }
    
    def _handle_off_topic_query(self, user_query: str, classification_result: Dict, session_id: str) -> Dict[str, Any]:
        """Handle off-topic queries"""
        return {
            "response": """Maaf, pertanyaan Anda sepertinya tidak terkait dengan sistem tiket keluhan pelanggan. 

            Saya dapat membantu Anda dengan:
            - Mencari informasi tiket tertentu (contoh: "cari tiket CC-12345")
            - Menghitung jumlah keluhan di lokasi tertentu (contoh: "berapa keluhan di Jakarta Barat?")
            - Menampilkan contoh keluhan dari suatu daerah
            - Menganalisis data keluhan pelanggan

            Silakan ajukan pertanyaan yang terkait dengan data keluhan pelanggan.""",
                        "status": "off_topic"
        }
    
    def _handle_system_inquiry(self, user_query: str, classification_result: Dict, session_id: str) -> Dict[str, Any]:
        """Handle system capability questions"""
        return {
            "response": """Saya adalah sistem AI untuk analisis keluhan pelanggan.

            **Status:** Sistem berjalan normal
            **Fungsi:** Menganalisis data ticket customer service
            **Kemampuan:** 
            - Mencari statistik keluhan per lokasi
            - Menampilkan contoh kasus spesifik
            - Menganalisis trend dan pola keluhan

            Tidak, saya tidak mengalami keluhan - saya adalah tools untuk menganalisis keluhan customer! 😊""",
                        "status": "system_inquiry"
        }
    
    def _save_session_interaction(self, session_id: str, user_query: str, result: Dict, workflow_type: str):
        """Save interaction to session"""
        try:
            response_text = result.get("response", "") if isinstance(result, dict) else str(result)
            entities = {}
            
            if isinstance(result, dict) and "metadata" in result:
                entities = result["metadata"].get("entities", {})
            
            self.session_manager.save_interaction(
                session_id=session_id,
                query=user_query,
                response=response_text,
                query_type=workflow_type,
                entities=entities
            )
        except Exception as e:
            print(f"[{session_id}] Session save error: {e}")
    
    def _create_standard_response(self, workflow_type: str, execution_result: Dict) -> Dict[str, Any]:
        """Create standardized response format"""
        if isinstance(execution_result, dict):
            response_text = execution_result.get("response", str(execution_result))
            status = execution_result.get("status", "success")
            error = execution_result.get("error")
        else:
            response_text = str(execution_result)
            status = "success"
            error = None
        
        return {
            "response": response_text,
            "status": status,
            "workflow": workflow_type,
            "metadata": {
                "workflow_description": self.WORKFLOW_TYPES.get(workflow_type, "Unknown workflow"),
                "execution_time": time.time()
            },
            "debug": {
                "workflow": workflow_type,
                "error": error,
                "raw_result": execution_result if isinstance(execution_result, dict) else None
            }
        }