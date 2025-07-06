# tools/smart_query_builder.py (MODIFIED)
import yaml
import re
import json
from typing import Dict, Any, List

class SmartQueryBuilder:
    def __init__(self, use_direct_db=True):
        """Initialize with option to use direct database or MCP"""
        self.semantic_mapping = self.load_semantic_mapping()
        self.table_name = self.semantic_mapping.get('table_name', 'inap_ticketing_customer_complain')
        self.use_direct_db = use_direct_db
        
        # Initialize appropriate database tool
        if self.use_direct_db:
            from tools.direct_database_tool import DirectDatabaseTool
            self.db_tool = DirectDatabaseTool()
            print("✅ SmartQueryBuilder using DirectDatabaseTool")
        # else:
        #     from tools.mcp_database_tool import MCPDatabaseTool
        #     self.db_tool = MCPDatabaseTool()
        #     print("✅ SmartQueryBuilder using MCPDatabaseTool")
    
    def load_semantic_mapping(self):
        """Load semantic mapping from YAML or JSON file"""
        try:
            with open('config/semantic_mapping.yaml', 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                print("[LOG] semantic_mapping.yaml loaded successfully.")
                return data
        except Exception as e:
            print(f"Error loading semantic mapping: {e}")
            return {}

    def analyze_and_build_query(self, user_query: str, context: Dict = None) -> Dict[str, Any]:
        intent = self.detect_intent(user_query)
        entities = self.extract_all_entities(user_query, context)
        sql = self.build_sql(intent, entities)
        return {
            "intent": intent,
            "entities": entities,
            "sql": sql,
            "context_for_next": self.build_context(user_query, entities)
        }

    def detect_intent(self, query: str) -> str:
        query_lower = query.lower()
        
        # Priority 1: Check for ticket ID patterns (CC-YYYYMMDD-XXXXXXXX)
        ticket_patterns = [
            r'cc-\d{8}-\d{8}',  # CC-20250603-00000475 format
            r'inc\d+',           # INC123456 format
        ]
        
        for pattern in ticket_patterns:
            if re.search(pattern, query_lower):
                return 'detail'
        
        # Priority 2: Check for MSISDN patterns
        msisdn_patterns = [
            r'\b628\d{8,12}\b',    # Indonesian mobile format starting with 628
            r'\b08\d{8,12}\b',     # Local Indonesian format starting with 08
            r'\b\d{10,15}\b',      # General 10-15 digit numbers
        ]
        
        for pattern in msisdn_patterns:
            if re.search(pattern, query):
                return 'detail'
        
        # Priority 3: Check other intents from semantic mapping
        intent_patterns = self.semantic_mapping.get('intent_patterns', {})
        for intent_type, pattern_info in intent_patterns.items():
            for keyword in pattern_info.get('keywords', []):
                if keyword.lower() in query_lower:
                    return intent_type
        
        # Priority 4: Check for explicit detail keywords
        detail_keywords = ['detail', 'info', 'informasi', 'rinci']
        if any(word in query_lower for word in detail_keywords):
            return 'detail'
        
        # Priority 5: Common patterns
        if any(word in query_lower for word in ['berapa', 'jumlah', 'count', 'total']):
            return 'count'
        elif any(word in query_lower for word in ['tampilkan', 'lihat', 'show', 'contoh']):
            return 'list'
        elif any(word in query_lower for word in ['summary', 'ringkasan', 'laporan']):
            return 'summary'
        
        # Default fallback
        return 'list'

    def extract_all_entities(self, query: str, context: Dict = None, enhanced_context: Dict = None) -> Dict[str, Any]:
        entities = {}
        query_lower = query.lower()
        
        # Apply enhanced context from follow-up FIRST
        if enhanced_context:
            print(f"[DEBUG] Applying enhanced context: {enhanced_context}")
            
            # Use complete geographic entities if available
            if enhanced_context.get('complete_geo_entities'):
                entities['geographic'] = enhanced_context['complete_geo_entities']
                print(f"[DEBUG] Using complete geo entities: {len(entities['geographic'])} fields")
            
            # Fallback: Create from location value if no complete entities
            elif enhanced_context.get('inherit_location') and enhanced_context.get('location'):
                location_value = enhanced_context['location']
                entities['geographic'] = [
                    {'field': 'provinsi_create_ticket', 'value': location_value, 'search_type': 'contains'},
                    {'field': 'kabupaten_kota_create_ticket', 'value': location_value, 'search_type': 'contains'},
                    {'field': 'kecamatan_create_ticket', 'value': location_value, 'search_type': 'contains'},
                    {'field': 'desa_kelurahan_create_ticket', 'value': location_value, 'search_type': 'contains'},
                    {'field': 'customer_region_create_ticket', 'value': location_value, 'search_type': 'contains'}
                ]
            
            # Inherit timeframe if specified  
            if enhanced_context.get('inherit_time') and enhanced_context.get('timeframe'):
                entities['temporal'] = [{
                    'field': 'create_time',
                    'value': enhanced_context['timeframe'],
                    'search_type': 'raw_sql'
                }]
            
            # Apply additional filters
            filters = enhanced_context.get('filters', '')
            if filters:
                if 'status_pending' in filters or 'belum solve' in filters:
                    entities['status'] = [{
                        'field': 'business_status',
                        'value': 'BusinessStatusInProgress',
                        'search_type': 'exact_match'
                    }]
        
        # Extract detail-specific entities first
        detail_entities = self.extract_detail_entities(query)
        if detail_entities:
            entities['detail'] = detail_entities
        
        # Existing entity extraction logic (only if not already set by enhanced context)
        field_mappings = self.semantic_mapping.get('field_mappings', {})
        for field_name, field_info in field_mappings.items():
            category = field_info.get('category', 'unknown')
            
            # Skip if already set by enhanced context
            if category in entities:
                continue
                
            synonyms = field_info.get('nlq_synonyms', [])
            for synonym in synonyms:
                if synonym.lower() in query_lower:
                    value = self.extract_value_for_field(query, field_name, field_info)
                    if value:
                        if category not in entities:
                            entities[category] = []
                        entities[category].append({
                            'field': field_name,
                            'value': value,
                            'search_type': field_info.get('search_type', 'contains')
                        })
        
        # Geographic entities (only if not set by enhanced context)
        if 'geographic' not in entities:
            geographic_entities = self.extract_geographic_entities(query_lower)
            if geographic_entities:
                entities['geographic'] = geographic_entities
        
        # Time entities (only if not set by enhanced context)
        if 'temporal' not in entities:
            time_entities = self.extract_time_entities(query_lower)
            if time_entities:
                entities['temporal'] = time_entities
        
        # Context entities
        if context:
            for key, value in context.items():
                if key.startswith('last_') and value:
                    entities['context'] = entities.get('context', [])
                    entities['context'].append({
                        'field': key,
                        'value': value,
                        'search_type': 'inherited'
                    })
        
        return entities
    
    def extract_detail_entities(self, query: str) -> List[Dict]:
        """Extract entities specific to detail queries (Ticket ID or MSISDN)"""
        entities = []
        
        # Extract Ticket ID (CC-YYYYMMDD-XXXXXXXX format)
        ticket_match = re.search(r'(cc-\d{8}-\d{8})', query, re.IGNORECASE)
        if ticket_match:
            entities.append({
                'field': 'order_id',
                'value': ticket_match.group(1).upper(),  # Ensure uppercase
                'search_type': 'exact_match',
                'entity_type': 'ticket_id'
            })
        
        # Extract MSISDN
        msisdn_match = re.search(r'\b(628\d{8,12})\b', query)
        if msisdn_match:
            entities.append({
                'field': 'customer_msisdn_create_ticket',
                'value': msisdn_match.group(1),
                'search_type': 'exact_match',
                'entity_type': 'msisdn'
            })
        
        # Convert local format (08) to international (628)
        local_msisdn_match = re.search(r'\b(08\d{8,12})\b', query)
        if local_msisdn_match and not msisdn_match:
            local_number = local_msisdn_match.group(1)
            international_number = '628' + local_number[2:]
            entities.append({
                'field': 'customer_msisdn_create_ticket',
                'value': international_number,
                'search_type': 'exact_match',
                'entity_type': 'msisdn'
            })
        
        # Other long numbers
        if not entities:
            other_number_match = re.search(r'\b(\d{10,15})\b', query)
            if other_number_match:
                entities.append({
                    'field': 'customer_msisdn_create_ticket',
                    'value': other_number_match.group(1),
                    'search_type': 'contains',
                    'entity_type': 'msisdn_fuzzy'
                })
        
        return entities

    def extract_geographic_entities(self, query_lower: str) -> List[Dict]:
        geographic_fields = self.semantic_mapping.get("semantic_categories", {}).get("geographic", {}).get("fields", [])
        location_mappings = {
            'jakbar': 'Jakarta Barat', 'jakarta barat': 'Jakarta Barat',
            'jaksel': 'Jakarta Selatan', 'jakarta selatan': 'Jakarta Selatan',
            'jaktim': 'Jakarta Timur', 'jakarta timur': 'Jakarta Timur',
            'jakut': 'Jakarta Utara', 'jakarta utara': 'Jakarta Utara',
            'jakpus': 'Jakarta Pusat', 'jakarta pusat': 'Jakarta Pusat',
            'jakarta': 'Jakarta', 'bandung': 'Bandung', 'surabaya': 'Surabaya'
        }
        entities = []
        for location_key, location_value in location_mappings.items():
            if location_key in query_lower:
                for field in geographic_fields:
                    entities.append({
                        'field': field,
                        'value': location_value,
                        'search_type': 'contains'
                    })
                break
        return entities

    def extract_time_entities(self, query_lower: str) -> List[Dict]:
        time_expressions = self.semantic_mapping.get('time_expressions', {})
        entities = []

        for time_phrase, time_info in time_expressions.items():
            if time_phrase in query_lower:
                if isinstance(time_info, dict):
                    entities.append({
                        'field': 'create_time',
                        'value': time_info['condition'],
                        'search_type': 'raw_sql',
                        'group_by': time_info.get('group_by')
                    })
                else:
                    entities.append({
                        'field': 'create_time',
                        'value': time_info,
                        'search_type': 'raw_sql'
                    })
                return entities

        return entities

    def extract_value_for_field(self, query: str, field_name: str, field_info: Dict) -> str:
        query_lower = query.lower()
        if field_info.get('search_type') == 'categorical':
            for value in field_info.get('values', []):
                if value.lower() in query_lower:
                    return value
        if 'handset' in field_name or 'device' in field_name:
            for pattern in ['iphone', 'samsung', 'oppo', 'xiaomi', 'android']:
                if pattern in query_lower:
                    return pattern.upper()
        if 'status' in field_name:
            if 'open' in query_lower: return 'Open'
            if 'closed' in query_lower: return 'Closed'
            if 'progress' in query_lower: return 'BusinessStatusInProgress'
            if 'resolved' in query_lower: return 'BusinessStatusResovled'
        if 'priority' in field_name:
            if 'high' in query_lower: return 'High'
            if 'medium' in query_lower: return 'Medium'
            if 'low' in query_lower: return 'Low'
        return None

    def build_sql(self, intent: str, entities: Dict[str, Any]) -> str:
        print(f"[DEBUG] Building SQL for intent: {intent}")
        print(f"[DEBUG] Entities: {entities}")
        
        where_conditions = []
        
        for category, entity_list in entities.items():
            print(f"[DEBUG] Processing category: {category}")
            
            if category == 'context':
                continue
                
            if not isinstance(entity_list, list):
                entity_list = [entity_list]
                
            category_conditions = []
            
            for entity in entity_list:
                field = entity.get('field')
                value = entity.get('value') 
                search_type = entity.get('search_type', 'contains')
                
                print(f"[DEBUG] Entity - field: {field}, value: {value}, search_type: {search_type}")
                
                if not field or not value:
                    print(f"[DEBUG] Skipping entity - missing field or value")
                    continue
                    
                if search_type == 'contains':
                    category_conditions.append(f"{field} ILIKE '%{value}%'")
                elif search_type in ['exact_match', 'categorical']:
                    category_conditions.append(f"{field} = '{value}'")
                elif search_type == 'raw_sql':
                    # FIX: Convert PostgreSQL functions to ClickHouse
                    clickhouse_value = self._convert_to_clickhouse_sql(value)
                    category_conditions.append(clickhouse_value)
                    
            print(f"[DEBUG] Category conditions for {category}: {category_conditions}")
            
            if category_conditions:
                if category == 'geographic':
                    where_conditions.append(f"({' OR '.join(category_conditions)})")
                elif category == 'detail':
                    where_conditions.append(f"({' OR '.join(category_conditions)})")
                else:
                    where_conditions.extend(category_conditions)
        
        where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'
        print(f"[DEBUG] Final WHERE clause: {where_clause}")
        
        # Build SQL based on intent
        if intent == 'count':
            sql = f"SELECT count() AS total_count FROM {self.table_name} WHERE {where_clause}"
        elif intent == 'list':
            sql = f"""
            SELECT order_id, create_time, description,
                kabupaten_kota_create_ticket, customer_type_create_ticket,
                business_status, priority_l2_assign
            FROM {self.table_name}
            WHERE {where_clause}
            ORDER BY create_time DESC
            LIMIT 10
            """
        elif intent == 'detail':
            sql = f"""
            SELECT * FROM {self.table_name}
            WHERE {where_clause}
            ORDER BY create_time DESC
            LIMIT 1
            """
        elif intent == 'summary':
            # Handle summary intent - FIX: Use ClickHouse functions
            group_by_time = "DAY"  # Default
            
            for ent in entities.get("temporal", []):
                if ent.get("group_by"):
                    group_by_time = ent["group_by"].upper()
                    break
            
            # Convert to ClickHouse date functions
            if group_by_time == "DAY":
                date_trunc_func = "toDate(create_time)"
            elif group_by_time == "WEEK":
                date_trunc_func = "toMonday(create_time)"
            elif group_by_time == "MONTH":
                date_trunc_func = "toStartOfMonth(create_time)"
            elif group_by_time == "YEAR":
                date_trunc_func = "toStartOfYear(create_time)"
            else:
                date_trunc_func = "toDate(create_time)"  # fallback
            
            sql = f"""
            SELECT 
                provinsi_create_ticket,
                count() AS total_keluhan,
                business_status,
                customer_type_create_ticket,
                {date_trunc_func} AS waktu
            FROM {self.table_name}
            WHERE {where_clause}
            GROUP BY provinsi_create_ticket, business_status, customer_type_create_ticket, waktu
            ORDER BY waktu DESC
            """
        else:
            print(f"[DEBUG] Unknown intent: {intent}")
            return None
        
        print(f"[DEBUG] Generated SQL: {sql}")
        return sql.strip() if sql else None

    def _convert_to_clickhouse_sql(self, value: str) -> str:
        """Convert PostgreSQL SQL functions to ClickHouse equivalents"""
        
        # Common replacements for temporal functions
        replacements = {
            # Date functions
            "CURRENT_DATE": "today()",
            "NOW()": "now()",
            
            # Date arithmetic - bulan lalu
            "(dateTrunc('month', CURRENT_DATE) - toIntervalMonth(1))": "(toStartOfMonth(today()) - INTERVAL 1 MONTH)",
            "dateTrunc('month', CURRENT_DATE)": "toStartOfMonth(today())",
            
            # Date arithmetic - minggu lalu  
            "(dateTrunc('week', CURRENT_DATE) - toIntervalWeek(1))": "(toMonday(today()) - INTERVAL 1 WEEK)",
            "dateTrunc('week', CURRENT_DATE)": "toMonday(today())",
            
            # Interval functions
            "toIntervalMonth(1)": "INTERVAL 1 MONTH",
            "toIntervalWeek(1)": "INTERVAL 1 WEEK",
            "toIntervalDay(1)": "INTERVAL 1 DAY",
        }
        
        # Apply replacements
        converted_value = value
        for old_syntax, new_syntax in replacements.items():
            converted_value = converted_value.replace(old_syntax, new_syntax)
        
        print(f"[DEBUG] Converted SQL: '{value}' -> '{converted_value}'")
        return converted_value

    def build_context(self, user_query: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        context = {}
        if 'geographic' in entities:
            for entity in entities['geographic']:
                if 'Jakarta' in entity.get('value', ''):
                    context['last_location'] = entity['value']
                    break
        context['last_query_type'] = self.detect_intent(user_query)
        context['last_query'] = user_query
        return context

    def format_response(self, sql_result: Any, intent: str) -> str:
        if not sql_result:
            return "No data found."
        try:
            if intent == 'count':
                count = sql_result[0].get('total_count', 0)
                return f"Found {count} records matching your criteria."
            elif intent == 'list':
                if len(sql_result) == 0:
                    return "No records found."
                formatted = []
                for item in sql_result[:5]:
                    formatted.append({
                        "order_id": item.get('order_id'),
                        "date": item.get('create_time'),
                        "description": item.get('description', '')[:100] + "..." if len(item.get('description', '')) > 100 else item.get('description', ''),
                        "location": item.get('kabupaten_kota_create_ticket'),
                        "status": item.get('business_status')
                    })
                return str(formatted)
            return str(sql_result)
        except Exception as e:
            return f"Error formatting response: {str(e)}"
        
    def execute_query(self, sql_query):
        """Execute SQL query via appropriate database tool"""
        try:
            print(f"🔄 Executing query via {'DirectDatabaseTool' if self.use_direct_db else 'MCPDatabaseTool'}...")
            
            if self.use_direct_db:
                # Use DirectDatabaseTool
                result = self.db_tool.execute_query(sql_query)
                print(f"✅ Query executed successfully. Rows returned: {len(result.get('data', []))}")
                return result
            else:
                # Use existing MCP Database Tool
                result_str = self.db_tool.execute_query(sql_query)
                result = json.loads(result_str)
                
                if result.get("success"):
                    data = result.get("data", [])
                    print(f"✅ Query executed successfully. Rows returned: {len(data)}")
                    return {
                        "success": True,
                        "data": data,
                        "metadata": result.get("metadata", {})
                    }
                else:
                    print(f"❌ Query failed: {result}")
                    return {
                        "success": False,
                        "error": result_str
                    }
                
        except json.JSONDecodeError as e:
            # Handle non-JSON error responses
            print(f"❌ Query execution error: {result_str}")
            return {
                "success": False,
                "error": result_str
            }
        except Exception as e:
            print(f"❌ Exception during query execution: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def build_and_execute(self, user_query, enhanced_context=None):
        """Build SQL and execute it with optional enhanced context"""
        print(f"🚀 Processing query: {user_query}")
        
        try:
            # Step 1: Detect intent
            self.intent = self.detect_intent(user_query)
            print(f"🔍 Detected Intent: {self.intent}")
            
            # Step 2: Extract entities with enhanced context
            self.entities = self.extract_all_entities(user_query, enhanced_context=enhanced_context)
            print(f"🧠 Entities: {self.entities}")
            print(f"🐛 Entities type: {type(self.entities)}")
            print(f"🐛 Entities content: {self.entities}")
            
            # ✅ FIX: Ensure entities is always a dict
            if not isinstance(self.entities, dict):
                print(f"🔧 Converting entities from {type(self.entities)} to dict")
                self.entities = {}
            
            # ✅ FIX: Validate entities structure
            validated_entities = {}
            for key, value in self.entities.items():
                if isinstance(value, (list, dict, str)):
                    validated_entities[key] = value
                elif isinstance(value, tuple):
                    print(f"🔧 Converting tuple to list for key: {key}")
                    validated_entities[key] = list(value)
                else:
                    print(f"🔧 Converting {type(value)} to string for key: {key}")
                    validated_entities[key] = str(value)
            
            self.entities = validated_entities
            print(f"🔧 Validated entities: {self.entities}")
            
            # Step 3: Build SQL
            sql_query = self.build_sql(self.intent, self.entities)
            
            if not sql_query:
                return {
                    "success": False,
                    "error": "Failed to generate SQL query",
                    "user_query": user_query,
                    "intent": self.intent,
                    "entities": self.entities
                }
                
            print(f"📄 SQL Generated: {sql_query}")
            
            # Step 4: Execute SQL
            result = self.execute_query(sql_query)
            
            # ✅ FIX: Validate execution result
            if not isinstance(result, dict):
                print(f"🔧 Converting execution result from {type(result)} to dict")
                result = {
                    "success": False,
                    "error": f"Unexpected result type: {type(result)}",
                    "data": []
                }
            
            # ✅ FIX: Ensure result has required fields
            if "success" not in result:
                result["success"] = False
            if "data" not in result:
                result["data"] = []
            
            print(f"🔧 Execution result validated: success={result.get('success')}, data_count={len(result.get('data', []))}")
            
            # Step 5: Return complete result
            final_result = {
                "success": True,
                "user_query": user_query,
                "sql_query": sql_query,
                "intent": self.intent,
                "entities": self.entities,
                "execution_result": result
            }
            
            print(f"🔧 Final result type check: {type(final_result)}")
            print(f"🔧 Final result keys: {list(final_result.keys())}")
            
            return final_result
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"❌ Error in build_and_execute: {str(e)}")
            print(f"❌ Full traceback: {error_trace}")
            
            return {
                "success": False,
                "error": f"Processing failed: {str(e)}",
                "user_query": user_query,
                "intent": getattr(self, 'intent', 'unknown'),
                "entities": getattr(self, 'entities', {}),
                "traceback": error_trace
            }

    def build_and_execute_with_narrative(self, user_query, enhanced_context=None):
        """Build SQL, execute, and generate narrative using Story Agent"""
        
        # Step 1-4: Build and execute query with enhanced context
        result = self.build_and_execute(user_query, enhanced_context)
        
        # Step 5: Generate narrative if execution successful
        if "execution_result" in result and result["execution_result"].get("success"):
            data = result["execution_result"]["data"]
            intent = result["intent"]
            entities = result["entities"]
            
            # Import and use appropriate story agent
            if intent == 'summary':
                from agents.story_agent import StoryAgentSummary
                story_agent = StoryAgentSummary()
                
                location = story_agent.extract_location_from_entities(entities)
                time_period = story_agent.extract_time_period_from_entities(entities)
                
                narrative = story_agent.generate_summary_narrative(data, location, time_period)
                result["narrative"] = narrative
                
            elif intent == 'detail':
                try:
                    from agents.story_agent import StoryAgentSummary
                    story_agent = StoryAgentSummary()
                    
                    if data and len(data) > 0:
                        narrative = story_agent.generate_detail_narrative(data[0])
                        result["narrative"] = narrative
                    else:
                        detail_entities = entities.get('detail', [])
                        if detail_entities:
                            entity = detail_entities[0]
                            search_value = entity.get('value', 'N/A')
                            entity_type = entity.get('entity_type', 'item')
                            
                            if entity_type == 'ticket_id':
                                result["narrative"] = f"❌ Ticket dengan ID **{search_value}** tidak ditemukan."
                            elif 'msisdn' in entity_type:
                                result["narrative"] = f"❌ Data untuk MSISDN **{search_value}** tidak ditemukan."
                            else:
                                result["narrative"] = f"❌ Data untuk **{search_value}** tidak ditemukan."
                        else:
                            result["narrative"] = "❌ Data tidak ditemukan untuk detail yang diminta."
                except Exception as e:
                    print(f"[ERROR] Detail narrative failed: {e}")
                    result["narrative"] = f"📊 Data ditemukan tapi gagal parsing: {str(e)}"
                    
            elif intent == 'count':
                # Simple narrative for count
                count = data[0].get('total_count', 0) if data else 0
                location = self._extract_location_simple(entities)
                time_period = self._extract_time_simple(entities)
                result["narrative"] = f"🔢 Ditemukan **{count} keluhan** di {location} {time_period}."
                
            elif intent == 'list':
                # Generate detailed complaint examples
                location = self._extract_location_simple(entities)
                time_period = self._extract_time_simple(entities)
                
                # Check if it's a filtered list (e.g., "yang belum solve")
                status_entities = entities.get('status', [])
                
                if len(data) > 0:
                    # Format detailed examples
                    examples = []
                    for i, complaint in enumerate(data[:5], 1):  # Show max 5 examples
                        examples.append(self._format_complaint_example(complaint, i))
                    
                    if status_entities:
                        status_filter = status_entities[0].get('value', '')
                        if 'Progress' in status_filter:
                            result["narrative"] = f"📋 **Contoh Keluhan yang Belum Selesai di {location} {time_period}:**\n\n" + "\n\n".join(examples)
                        else:
                            result["narrative"] = f"📋 **Contoh Keluhan di {location} {time_period}:**\n\n" + "\n\n".join(examples)
                    else:
                        result["narrative"] = f"📋 **Contoh Keluhan di {location} {time_period}:**\n\n" + "\n\n".join(examples)
                else:
                    if status_entities:
                        status_filter = status_entities[0].get('value', '')
                        if 'Progress' in status_filter:
                            result["narrative"] = f"📋 **Keluhan yang Belum Selesai di {location} {time_period}**\n\nDitemukan **0 keluhan** yang masih dalam proses penyelesaian."
                        else:
                            result["narrative"] = f"📋 Tidak ada keluhan ditemukan di {location} {time_period}."
                    else:
                        result["narrative"] = f"📋 Tidak ada keluhan ditemukan di {location} {time_period}."
            
            else:
                result["narrative"] = f"📊 Ditemukan {len(data)} record untuk query Anda."
        
        return result

    def _extract_location_simple(self, entities):
        """Simple location extraction"""
        geo_entities = entities.get('geographic', [])
        if geo_entities:
            return geo_entities[0].get('value', 'lokasi yang diminta')
        return "lokasi yang diminta"
    
    def _format_complaint_example(self, complaint, index):
        """Format single complaint as detailed example"""
        order_id = complaint.get('order_id', 'N/A')
        create_time = complaint.get('create_time', 'N/A')
        description = complaint.get('description', 'N/A')
        location = complaint.get('kabupaten_kota_create_ticket', 'N/A')
        customer_type = complaint.get('customer_type_create_ticket', 'N/A')
        status = complaint.get('business_status', 'N/A')
        priority = complaint.get('priority_l2_assign', 'N/A')
        
        # Format date
        formatted_date = create_time
        if create_time != 'N/A':
            try:
                from datetime import datetime
                if isinstance(create_time, str):
                    date_str = create_time.replace('Z', '').replace('+00:00', '')
                    if 'T' in date_str:
                        dt = datetime.fromisoformat(date_str)
                    else:
                        dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                else:
                    dt = create_time
                formatted_date = dt.strftime('%d %b %Y, %H:%M')
            except Exception as e:
                print(f"Date formatting error: {e}")
                formatted_date = str(create_time)
        
        # Format status with emoji
        status_emoji = "🔄"
        if "Progress" in status or "InProgress" in status:
            status_emoji = "🔄"
            status_text = "Dalam Proses"
        elif "Complete" in status or "Resolved" in status or "Closed" in status:
            status_emoji = "✅"
            status_text = "Selesai"
        elif "Open" in status:
            status_emoji = "🆕"
            status_text = "Baru"
        else:
            status_emoji = "📌"
            status_text = status
        
        # Format customer type
        customer_emoji = "👤" if customer_type == "Konsumen" else "🏢" if customer_type == "Korporat" else "👥"
        
        # Truncate description and clean it
        if description and description != 'N/A':
            clean_desc = description.replace('\n', ' ').replace('\r', ' ').strip()
            short_desc = clean_desc[:120] + "..." if len(clean_desc) > 120 else clean_desc
        else:
            short_desc = "Tidak ada deskripsi keluhan"
        
        # Format priority
        priority_text = ""
        if priority and priority != 'N/A':
            if priority == "High":
                priority_text = "🔴 Prioritas Tinggi"
            elif priority == "Medium":
                priority_text = "🟡 Prioritas Sedang"
            elif priority == "Low":
                priority_text = "🟢 Prioritas Rendah"
            else:
                priority_text = f"📋 {priority}"
        
        # Build the formatted example
        example = f"""**{index}. {order_id}**
📅 {formatted_date}
📍 {location}
📋 {short_desc}
{customer_emoji} {customer_type}
{status_emoji} {status_text}"""

        if priority_text:
            example += f"\n{priority_text}"
        
        return example

    def _extract_time_simple(self, entities):
        """Simple time period extraction"""
        temporal_entities = entities.get('temporal', [])
        if temporal_entities:
            value = temporal_entities[0].get('value', '')
            if 'week' in value.lower() and 'interval' in value.lower():
                return "minggu lalu"
            elif 'week' in value.lower():
                return "minggu ini"
            elif 'month' in value.lower() and 'interval' in value.lower():
                return "bulan lalu"
            elif 'month' in value.lower():
                return "bulan ini"
            elif 'current_date' in value.lower() and 'interval' in value.lower():
                if 'day' in value.lower():
                    return "kemarin"
                return "periode lalu"
        return "periode yang diminta"