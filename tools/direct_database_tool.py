# # tools/direct_database_tool.py
# import os
# import json
# from typing import Dict, List, Any, Optional
# import clickhouse_connect
# from clickhouse_connect import get_client
# import time

# class DirectDatabaseTool:
#     """Direct ClickHouse database access tool"""
    
#     def __init__(self):
#         """Initialize ClickHouse connection with working config"""
#         self.host = os.getenv('CLICKHOUSE_HOST', 'localhost')
#         self.port = int(os.getenv('CLICKHOUSE_PORT', 9443))
#         self.database = os.getenv('CLICKHOUSE_DB', 'default')
#         self.user = os.getenv('CLICKHOUSE_USER', 'default')
#         self.password = os.getenv('CLICKHOUSE_PASSWORD', '')
#         self.secure = True  # ✅ Working config uses SSL
        
#         print(f"🔧 ClickHouse config: {self.user}@{self.host}:{self.port}/{self.database}, secure={self.secure}")
        
#         try:
#             # ✅ Exact working configuration
#             self.client = clickhouse_connect.get_client(
#                 host=self.host,
#                 port=self.port,
#                 username=self.user,
#                 password=self.password,
#                 database=self.database,
#                 secure=True,    # ✅ SSL enabled
#                 verify=False    # ✅ Don't verify certificates
#             )
            
#             # Test connection
#             test_result = self.client.query('SELECT 1')
#             print(f"✅ ClickHouse connection successful: {self.host}:{self.port}")
#             print(f"✅ Test query result: {test_result.result_rows}")
            
#         except Exception as e:
#             print(f"❌ ClickHouse connection failed: {e}")
#             self.client = None
        
#         self.table_name = os.getenv('CLICKHOUSE_TABLE', 'inap_ticketing_customer_complain')
#         print(f"🔗 Using table: {self.table_name}")
    
#     def test_connection(self) -> Dict[str, Any]:
#         """Test ClickHouse database connection"""
#         try:
#             if self.secure:
#                 # For HTTPS connections
#                 result = self.client.query("SELECT 1 as test")
#                 row_count = self.client.query(f"SELECT count(*) FROM {self.table_name}").first_row[0]
#             else:
#                 # For standard connections  
#                 result = self.client.execute("SELECT 1 as test")
#                 row_count = self.client.execute(f"SELECT count(*) FROM {self.table_name}")[0][0]
            
#             return {
#                 "success": True,
#                 "message": "ClickHouse connection successful",
#                 "config": {
#                     "host": self.host,
#                     "port": self.port,
#                     "database": self.database,
#                     "table": self.table_name
#                 },
#                 "table_row_count": row_count
#             }
#         except Exception as e:
#             return {
#                 "success": False,
#                 "message": f"ClickHouse connection failed: {str(e)}",
#                 "config": {
#                     "host": self.host,
#                     "port": self.port,
#                     "database": self.database,
#                     "table": self.table_name
#                 }
#             }
    
#     def execute_query(self, query: str, params: Optional[Dict] = None) -> Dict[str, Any]:
#         """Execute ClickHouse query with RETRY LOGIC untuk rate limiting"""
#         max_retries = 3
#         base_delay = 2
        
#         for attempt in range(max_retries):
#             try:
#                 print(f"🔍 [{attempt+1}/{max_retries}] Executing query: {query[:100]}...")
                
#                 if self.secure:
#                     if params:
#                         result = self.client.query(query, parameters=params)
#                     else:
#                         result = self.client.query(query)
                    
#                     rows = result.result_rows
                    
#                     # ✅ FIX: Convert ClickHouse tuples to dict (like PostgreSQL)
#                     if hasattr(result, 'column_names') and result.column_names:
#                         columns = result.column_names
#                         dict_rows = [dict(zip(columns, row)) for row in rows]
#                     else:
#                         # Fallback jika tidak ada column info
#                         dict_rows = rows
                        
#                 else:
#                     if params:
#                         rows = self.client.execute(query, params)
#                     else:
#                         rows = self.client.execute(query)
                    
#                     # For non-secure connection, assume rows are already processed
#                     dict_rows = rows
                
#                 # ✅ FIX: Debug logging untuk troubleshooting
#                 print(f"🐛 Debug - rows type: {type(rows)}")
#                 print(f"🐛 Debug - dict_rows type: {type(dict_rows)}")
#                 if dict_rows and len(dict_rows) > 0:
#                     print(f"🐛 Debug - first row type: {type(dict_rows[0])}")
#                     print(f"🐛 Debug - first row sample: {dict_rows[0] if len(str(dict_rows[0])) < 200 else str(dict_rows[0])[:200]}")
                
#                 # ✅ FIX: Pastikan semua rows sudah dalam format dict
#                 if dict_rows and isinstance(dict_rows[0], tuple):
#                     print("🔧 Converting remaining tuple rows to dict...")
#                     if hasattr(result, 'column_names') and result.column_names:
#                         columns = result.column_names
#                         dict_rows = [dict(zip(columns, row)) for row in dict_rows]
#                     else:
#                         # Jika tidak ada column names, buat generic column names
#                         if dict_rows:
#                             columns = [f"col_{i}" for i in range(len(dict_rows[0]))]
#                             dict_rows = [dict(zip(columns, row)) for row in dict_rows]
                
#                 print(f"✅ Query executed successfully. Rows: {len(dict_rows)}")
                
#                 return {
#                     "success": True,
#                     "data": dict_rows,  # ← Now guaranteed to be list of dicts
#                     "row_count": len(dict_rows),
#                     "query": query
#                 }
                
#             except Exception as e:
#                 error_msg = str(e)
#                 print(f"❌ Query error (attempt {attempt+1}): {error_msg}")
                
#                 # Check for rate limiting or connection issues
#                 is_rate_limited = any(indicator in error_msg.lower() for indicator in [
#                     '429', 'rate limit', 'too many', 'connection', 'timeout'
#                 ])
                
#                 if is_rate_limited and attempt < max_retries - 1:
#                     delay = base_delay * (2 ** attempt)  # Exponential backoff
#                     print(f"⏳ Rate limited/connection issue - retrying in {delay}s...")
#                     time.sleep(delay)
#                     continue
                
#                 # Final attempt failed
#                 return {
#                     "success": False,
#                     "error": error_msg,
#                     "query": query,
#                     "data": [],
#                     "retry_attempts": attempt + 1
#                 }
    
#     def get_table_info(self) -> Dict[str, Any]:
#         """Get ClickHouse table structure information"""
#         try:
#             # Get table schema
#             schema_query = f"DESCRIBE TABLE {self.table_name}"
#             schema_result = self.execute_query(schema_query)
            
#             if schema_result["success"]:
#                 columns = []
#                 for row in schema_result["data"]:
#                     # ✅ FIX: Handle both dict and tuple
#                     if isinstance(row, dict):
#                         # Data already converted to dict
#                         row_values = list(row.values())
#                         columns.append({
#                             "name": row_values[0] if len(row_values) > 0 else "",
#                             "type": row_values[1] if len(row_values) > 1 else "",
#                             "default_type": row_values[2] if len(row_values) > 2 else "",
#                             "default_expression": row_values[3] if len(row_values) > 3 else ""
#                         })
#                     else:
#                         # Still tuple format
#                         columns.append({
#                             "name": row[0],
#                             "type": row[1],
#                             "default_type": row[2] if len(row) > 2 else "",
#                             "default_expression": row[3] if len(row) > 3 else ""
#                         })
                
#                 # Get row count
#                 count_result = self.execute_query(f"SELECT count(*) FROM {self.table_name}")
#                 if count_result["success"] and count_result["data"]:
#                     count_row = count_result["data"][0]
#                     # ✅ FIX: Handle both dict and tuple for count
#                     if isinstance(count_row, dict):
#                         total_rows = list(count_row.values())[0]
#                     else:
#                         total_rows = count_row[0]
#                 else:
#                     total_rows = 0
                
#                 return {
#                     "success": True,
#                     "table_name": self.table_name,
#                     "columns": columns,
#                     "total_rows": total_rows,
#                     "column_count": len(columns)
#                 }
#             else:
#                 return {
#                     "success": False,
#                     "error": schema_result["error"]
#                 }
                
#         except Exception as e:
#             return {
#                 "success": False,
#                 "error": str(e)
#             }
    
#     def build_query(self, intent: str, entities: Dict[str, Any], context: Dict[str, Any] = None) -> str:
#         """Build ClickHouse query based on intent and entities"""
        
#         base_table = self.table_name
        
#         # Build WHERE conditions
#         where_conditions = []
        
#         # Geographic filtering
#         if "geographic" in entities and entities["geographic"]:
#             geo_conditions = []
#             for geo in entities["geographic"]:
#                 location = geo["value"].upper()
#                 if geo["type"] == "province":
#                     geo_conditions.append(f"upper(province) LIKE '%{location}%'")
#                 elif geo["type"] == "city":
#                     geo_conditions.append(f"upper(city) LIKE '%{location}%'")
#                 elif geo["type"] == "district":
#                     geo_conditions.append(f"upper(district) LIKE '%{location}%'")
#                 else:
#                     # Generic location search
#                     geo_conditions.append(f"(upper(province) LIKE '%{location}%' OR upper(city) LIKE '%{location}%' OR upper(district) LIKE '%{location}%')")
            
#             if geo_conditions:
#                 where_conditions.append(f"({' OR '.join(geo_conditions)})")
        
#         # Temporal filtering  
#         if "temporal" in entities and entities["temporal"]:
#             for temp in entities["temporal"]:
#                 if temp.get("clickhouse_condition"):
#                     where_conditions.append(temp["clickhouse_condition"])
        
#         # Build WHERE clause
#         where_clause = ""
#         if where_conditions:
#             where_clause = f"WHERE {' AND '.join(where_conditions)}"
        
#         # Build query based on intent
#         if intent == "count":
#             query = f"SELECT count(*) as total_complaints FROM {base_table} {where_clause}"
            
#         elif intent == "list" or intent == "example":
#             query = f"""
#             SELECT 
#                 ticket_number,
#                 complaint_date,
#                 province,
#                 city,
#                 district,
#                 complaint_category,
#                 customer_type,
#                 status,
#                 priority
#             FROM {base_table} 
#             {where_clause}
#             ORDER BY complaint_date DESC
#             LIMIT 10
#             """
            
#         elif intent == "summary":
#             query = f"""
#             SELECT 
#                 province,
#                 city,
#                 complaint_category,
#                 count(*) as complaint_count,
#                 countIf(status = 'Resolved') as resolved_count,
#                 countIf(priority = 'High') as high_priority_count
#             FROM {base_table}
#             {where_clause}
#             GROUP BY province, city, complaint_category
#             ORDER BY complaint_count DESC
#             LIMIT 20
#             """
            
#         else:
#             # Default to simple list
#             query = f"SELECT * FROM {base_table} {where_clause} LIMIT 5"
        
#         return query


import os
import json
import time
import threading
from typing import Dict, List, Any, Optional
import clickhouse_connect
from clickhouse_connect import get_client
from contextlib import contextmanager

class DatabaseConnectionPool:
    """Singleton connection pool for ClickHouse"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.host = os.getenv('CLICKHOUSE_HOST', 'localhost')
        self.port = int(os.getenv('CLICKHOUSE_PORT', 9443))
        self.database = os.getenv('CLICKHOUSE_DB', 'default')
        self.user = os.getenv('CLICKHOUSE_USER', 'default')
        self.password = os.getenv('CLICKHOUSE_PASSWORD', '')
        self.secure = True  # Working config
        
        self._client = None
        self._connection_lock = threading.Lock()
        self._last_health_check = 0
        self._health_check_interval = 30
        self._initialized = True
        
        print(f"🔧 Initializing ClickHouse connection pool: {self.user}@{self.host}:{self.port}")
        self._ensure_connection()
    
    def _ensure_connection(self):
        """Ensure connection is established with retry logic"""
        with self._connection_lock:
            current_time = time.time()
            
            if (self._client is None or 
                current_time - self._last_health_check > self._health_check_interval):
                
                self._establish_connection()
                self._last_health_check = current_time
    
    def _establish_connection(self):
        """Establish connection with working config"""
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                print(f"🔄 Connection attempt {attempt + 1}/{max_retries}")
                
                self._client = clickhouse_connect.get_client(
                    host=self.host,
                    port=self.port,
                    username=self.user,
                    password=self.password,
                    database=self.database,
                    secure=True,    # Working config
                    verify=False    # Working config
                )
                
                # Test connection
                result = self._client.query('SELECT 1')
                print(f"✅ ClickHouse connection pool established: {self.host}:{self.port}")
                return
                
            except Exception as e:
                print(f"❌ Connection attempt {attempt + 1} failed: {str(e)[:100]}")
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"⏳ Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print(f"❌ All connection attempts failed. Setting client to None.")
                    self._client = None
    
    @contextmanager
    def get_client(self):
        """Get client with automatic connection management"""
        self._ensure_connection()
        
        if self._client is None:
            raise ConnectionError("ClickHouse connection not available")
        
        try:
            yield self._client
        except Exception as e:
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                print(f"🔄 Connection error detected, will reconnect: {e}")
                self._client = None
            raise
    
    def is_healthy(self):
        """Check if connection is healthy"""
        try:
            with self.get_client() as client:
                client.query('SELECT 1')
                return True
        except:
            return False


class DirectDatabaseTool:
    """Hybrid ClickHouse tool - Production pooling + existing utilities"""
    
    def __init__(self):
        """Initialize with connection pool + existing config"""
        self.pool = DatabaseConnectionPool()
        self.host = self.pool.host
        self.port = self.pool.port
        self.database = self.pool.database
        self.user = self.pool.user
        self.password = self.pool.password
        self.secure = True
        self.table_name = os.getenv('CLICKHOUSE_TABLE', 'inap_ticketing_customer_complain')
        
        print(f"🔧 ClickHouse config: {self.user}@{self.host}:{self.port}/{self.database}, secure={self.secure}")
        print(f"🔗 Using table: {self.table_name}")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test ClickHouse database connection - Enhanced version"""
        try:
            with self.pool.get_client() as client:
                # Test basic query
                result = client.query("SELECT 1 as test")
                
                # Test table access
                row_count = client.query(f"SELECT count(*) FROM {self.table_name}").first_row[0]
                
                return {
                    "success": True,
                    "message": "ClickHouse connection successful",
                    "config": {
                        "host": self.host,
                        "port": self.port,
                        "database": self.database,
                        "table": self.table_name
                    },
                    "table_row_count": row_count,
                    "connection_pool": self.pool.is_healthy()
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"ClickHouse connection failed: {str(e)}",
                "config": {
                    "host": self.host,
                    "port": self.port,
                    "database": self.database,
                    "table": self.table_name
                },
                "connection_pool": False
            }
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute ClickHouse query with pooling + existing logic"""
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                print(f"🔍 [{attempt+1}/{max_retries}] Executing query: {query[:100]}...")
                
                with self.pool.get_client() as client:
                    if params:
                        result = client.query(query, parameters=params)
                    else:
                        result = client.query(query)
                    
                    rows = result.result_rows
                    
                    # Convert ClickHouse tuples to dict (existing logic)
                    if hasattr(result, 'column_names') and result.column_names:
                        columns = result.column_names
                        dict_rows = [dict(zip(columns, row)) for row in rows]
                    else:
                        dict_rows = rows
                    
                    # Debug logging (existing)
                    print(f"🐛 Debug - rows type: {type(rows)}")
                    print(f"🐛 Debug - dict_rows type: {type(dict_rows)}")
                    if dict_rows and len(dict_rows) > 0:
                        print(f"🐛 Debug - first row type: {type(dict_rows[0])}")
                        print(f"🐛 Debug - first row sample: {dict_rows[0] if len(str(dict_rows[0])) < 200 else str(dict_rows[0])[:200]}")
                    
                    # Ensure all rows are in dict format (existing logic)
                    if dict_rows and isinstance(dict_rows[0], tuple):
                        print("🔧 Converting remaining tuple rows to dict...")
                        if hasattr(result, 'column_names') and result.column_names:
                            columns = result.column_names
                            dict_rows = [dict(zip(columns, row)) for row in dict_rows]
                        else:
                            if dict_rows:
                                columns = [f"col_{i}" for i in range(len(dict_rows[0]))]
                                dict_rows = [dict(zip(columns, row)) for row in dict_rows]
                    
                    print(f"✅ Query executed successfully. Rows: {len(dict_rows)}")
                    
                    return {
                        "success": True,
                        "data": dict_rows,
                        "row_count": len(dict_rows),
                        "query": query
                    }
                    
            except ConnectionError as e:
                print(f"❌ Connection error (attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                else:
                    return {
                        "success": False,
                        "error": f"Database connection unavailable: {str(e)}",
                        "query": query,
                        "data": []
                    }
                    
            except Exception as e:
                error_msg = str(e)
                print(f"❌ Query error (attempt {attempt+1}): {error_msg}")
                
                # Check for rate limiting or connection issues (existing logic)
                is_rate_limited = any(indicator in error_msg.lower() for indicator in [
                    '429', 'rate limit', 'too many', 'connection', 'timeout'
                ])
                
                if is_rate_limited and attempt < max_retries - 1:
                    delay = 2 * (2 ** attempt)  # Exponential backoff
                    print(f"⏳ Rate limited/connection issue - retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    return {
                        "success": False,
                        "error": error_msg,
                        "query": query,
                        "data": [],
                        "retry_attempts": attempt + 1
                    }
    
    def get_table_info(self) -> Dict[str, Any]:
        """Get ClickHouse table structure information - Keep existing utility"""
        try:
            # Get table schema
            schema_query = f"DESCRIBE TABLE {self.table_name}"
            schema_result = self.execute_query(schema_query)
            
            if schema_result["success"]:
                columns = []
                for row in schema_result["data"]:
                    # Handle both dict and tuple (existing logic)
                    if isinstance(row, dict):
                        row_values = list(row.values())
                        columns.append({
                            "name": row_values[0] if len(row_values) > 0 else "",
                            "type": row_values[1] if len(row_values) > 1 else "",
                            "default_type": row_values[2] if len(row_values) > 2 else "",
                            "default_expression": row_values[3] if len(row_values) > 3 else ""
                        })
                    else:
                        # Still tuple format
                        columns.append({
                            "name": row[0],
                            "type": row[1],
                            "default_type": row[2] if len(row) > 2 else "",
                            "default_expression": row[3] if len(row) > 3 else ""
                        })
                
                # Get row count
                count_result = self.execute_query(f"SELECT count(*) FROM {self.table_name}")
                if count_result["success"] and count_result["data"]:
                    count_row = count_result["data"][0]
                    if isinstance(count_row, dict):
                        total_rows = list(count_row.values())[0]
                    else:
                        total_rows = count_row[0]
                else:
                    total_rows = 0
                
                return {
                    "success": True,
                    "table_name": self.table_name,
                    "columns": columns,
                    "total_rows": total_rows,
                    "column_count": len(columns)
                }
            else:
                return {
                    "success": False,
                    "error": schema_result["error"]
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def build_query(self, intent: str, entities: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """Build ClickHouse query - Keep existing utility"""
        base_table = self.table_name
        where_conditions = []
        
        # Geographic filtering (existing logic)
        if "geographic" in entities and entities["geographic"]:
            geo_conditions = []
            for geo in entities["geographic"]:
                location = geo["value"].upper()
                if geo.get("type") == "province":
                    geo_conditions.append(f"upper(province) LIKE '%{location}%'")
                elif geo.get("type") == "city":
                    geo_conditions.append(f"upper(city) LIKE '%{location}%'")
                elif geo.get("type") == "district":
                    geo_conditions.append(f"upper(district) LIKE '%{location}%'")
                else:
                    # Generic location search
                    geo_conditions.append(f"(upper(province) LIKE '%{location}%' OR upper(city) LIKE '%{location}%' OR upper(district) LIKE '%{location}%')")
            
            if geo_conditions:
                where_conditions.append(f"({' OR '.join(geo_conditions)})")
        
        # Temporal filtering (existing logic)
        if "temporal" in entities and entities["temporal"]:
            for temp in entities["temporal"]:
                if temp.get("clickhouse_condition"):
                    where_conditions.append(temp["clickhouse_condition"])
        
        # Build WHERE clause
        where_clause = ""
        if where_conditions:
            where_clause = f"WHERE {' AND '.join(where_conditions)}"
        
        # Build query based on intent (existing logic)
        if intent == "count":
            query = f"SELECT count(*) as total_complaints FROM {base_table} {where_clause}"
        elif intent == "list" or intent == "example":
            query = f"""
            SELECT
                ticket_number,
                complaint_date,
                province,
                city,
                district,
                complaint_category,
                customer_type,
                status,
                priority
            FROM {base_table}
            {where_clause}
            ORDER BY complaint_date DESC
            LIMIT 10
            """
        elif intent == "summary":
            query = f"""
            SELECT
                province,
                city,
                complaint_category,
                count(*) as complaint_count,
                countIf(status = 'Resolved') as resolved_count,
                countIf(priority = 'High') as high_priority_count
            FROM {base_table}
            {where_clause}
            GROUP BY province, city, complaint_category
            ORDER BY complaint_count DESC
            LIMIT 20
            """
        else:
            # Default to simple list
            query = f"SELECT * FROM {base_table} {where_clause} LIMIT 5"
        
        return query
    
    def health_check(self) -> Dict[str, Any]:
        """Health check alias"""
        return self.test_connection()