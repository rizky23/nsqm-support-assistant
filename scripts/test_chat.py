#!/usr/bin/env python3

import asyncio
import httpx
import json
import time
from typing import Dict, Any

# Test queries
TEST_QUERIES = [
    {
        "query": "Cek traffic MSISDN 08123456789 kemarin",
        "description": "Basic traffic analysis with MSISDN extraction"
    },
    {
        "query": "Kenapa jaringan lambat untuk nomor 08111222333 hari ini?",
        "description": "Troubleshooting query with intent detection"
    },
    {
        "query": "Bandingkan dengan kasus serupa latency tinggi",
        "description": "Knowledge base search without specific MSISDN"
    },
    {
        "query": "Bagaimana cara mengatasi device compatibility issues?",
        "description": "General knowledge query"
    },
    {
        "query": "Analisis lengkap untuk 82261813123 minggu lalu",
        "description": "Comprehensive analysis with date parsing"
    }
]

ORCHESTRATOR_BASE_URL = "http://localhost:8000"

class ChatTester:
    def __init__(self, base_url: str = ORCHESTRATOR_BASE_URL):
        self.base_url = base_url
        self.session_id = f"test_session_{int(time.time())}"
    
    async def test_health(self) -> bool:
        """Test if the orchestrator is healthy"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health", timeout=10.0)
                if response.status_code == 200:
                    health_data = response.json()
                    print("🏥 Health Check Results:")
                    print(f"   Orchestrator: {health_data.get('orchestrator', 'unknown')}")
                    print(f"   Chat System: {health_data.get('chat_system', 'unknown')}")
                    print(f"   vLLM Service: {'✅' if health_data.get('vllm_service') else '❌'}")
                    
                    servers = health_data.get('servers', {})
                    for server_name, status in servers.items():
                        emoji = "✅" if status == "healthy" else "❌"
                        print(f"   {server_name.title()} MCP: {emoji} {status}")
                    
                    return health_data.get('overall_status', 'unknown') in ['healthy', 'degraded']
                else:
                    print(f"❌ Health check failed: HTTP {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    async def test_chat_query(self, query: str, description: str) -> Dict[str, Any]:
        """Test a single chat query"""
        print(f"\n🧪 Testing: {description}")
        print(f"   Query: \"{query}\"")
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat",
                    json={
                        "query": query,
                        "session_id": self.session_id
                    },
                    timeout=60.0
                )
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    
                    print(f"   ✅ Success ({response_time:.2f}s)")
                    print(f"   Tools used: {result.get('tools_used', [])}")
                    print(f"   Response length: {len(result.get('response', ''))}")
                    
                    # Show response preview
                    response_text = result.get('response', '')
                    preview = response_text[:200] + "..." if len(response_text) > 200 else response_text
                    print(f"   Response preview: {preview}")
                    
                    return {
                        "success": True,
                        "response_time": response_time,
                        "result": result
                    }
                else:
                    print(f"   ❌ HTTP Error: {response.status_code}")
                    try:
                        error_detail = response.json()
                        print(f"   Error detail: {error_detail}")
                    except:
                        print(f"   Response text: {response.text}")
                    
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}"
                    }
                    
        except Exception as e:
            response_time = time.time() - start_time
            print(f"   ❌ Exception ({response_time:.2f}s): {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_suggestions(self):
        """Test getting suggested queries"""
        print("\n📝 Testing suggested queries...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/chat/suggestions", timeout=10.0)
                
                if response.status_code == 200:
                    suggestions = response.json()
                    print("   ✅ Suggestions retrieved:")
                    
                    for category in suggestions:
                        cat_name = category.get('category', 'Unknown')
                        queries = category.get('queries', [])
                        print(f"     {cat_name}: {len(queries)} queries")
                    
                    return True
                else:
                    print(f"   ❌ Failed: HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            return False
    
    async def test_session_management(self):
        """Test session management features"""
        print("\n👤 Testing session management...")
        
        try:
            async with httpx.AsyncClient() as client:
                # Get session history
                response = await client.get(
                    f"{self.base_url}/chat/sessions/{self.session_id}/history",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    history = response.json()
                    conversation_count = history.get('conversation_count', 0)
                    print(f"   ✅ Session history: {conversation_count} conversations")
                    
                    # Clear session
                    response = await client.delete(
                        f"{self.base_url}/chat/sessions/{self.session_id}",
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        print("   ✅ Session cleared successfully")
                        return True
                    else:
                        print(f"   ❌ Failed to clear session: HTTP {response.status_code}")
                        return False
                else:
                    print(f"   ❌ Failed to get history: HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            return False
    
    async def test_mcp_servers(self):
        """Test direct MCP server access"""
        print("\n🔧 Testing MCP servers...")
        
        try:
            async with httpx.AsyncClient() as client:
                # List servers
                response = await client.get(f"{self.base_url}/mcp/servers", timeout=10.0)
                
                if response.status_code == 200:
                    servers = response.json()
                    print(f"   ✅ Found {len(servers)} MCP servers:")
                    
                    for server_name, server_info in servers.items():
                        status = server_info.get('status', 'unknown')
                        tools_count = len(server_info.get('tools', []))
                        emoji = "✅" if status == "healthy" else "❌"
                        print(f"     {emoji} {server_name}: {status} ({tools_count} tools)")
                    
                    return True
                else:
                    print(f"   ❌ Failed: HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            return False
    
    async def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Starting Telecom MCP Chat Interface Tests")
        print("=" * 60)
        
        # Health check first
        healthy = await self.test_health()
        if not healthy:
            print("\n❌ System not healthy - aborting tests")
            return False
        
        print(f"\n🔑 Using session ID: {self.session_id}")
        
        # Test MCP servers
        await self.test_mcp_servers()
        
        # Test suggestions
        await self.test_suggestions()
        
        # Test chat queries
        print(f"\n💬 Testing {len(TEST_QUERIES)} chat queries...")
        
        successful_tests = 0
        total_response_time = 0
        
        for i, test_case in enumerate(TEST_QUERIES, 1):
            result = await self.test_chat_query(
                test_case["query"], 
                f"Test {i}: {test_case['description']}"
            )
            
            if result["success"]:
                successful_tests += 1
                total_response_time += result["response_time"]
        
        # Test session management
        await self.test_session_management()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Test Summary:")
        print(f"   Total queries tested: {len(TEST_QUERIES)}")
        print(f"   Successful: {successful_tests}")
        print(f"   Failed: {len(TEST_QUERIES) - successful_tests}")
        
        if successful_tests > 0:
            avg_response_time = total_response_time / successful_tests
            print(f"   Average response time: {avg_response_time:.2f}s")
        
        success_rate = (successful_tests / len(TEST_QUERIES)) * 100
        print(f"   Success rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("\n✅ Tests PASSED - System is working well!")
        elif success_rate >= 60:
            print("\n⚠️  Tests PARTIALLY PASSED - Some issues detected")
        else:
            print("\n❌ Tests FAILED - Major issues detected")
        
        return success_rate >= 80

def main():
    """Main function to run tests"""
    import sys
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("Usage: python test_chat.py [base_url]")
            print("       python test_chat.py --help")
            print()
            print("Default base_url: http://localhost:8000")
            return
        else:
            base_url = sys.argv[1]
    else:
        base_url = ORCHESTRATOR_BASE_URL
    
    print(f"Testing chat interface at: {base_url}")
    
    tester = ChatTester(base_url)
    
    try:
        success = asyncio.run(tester.run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Test runner crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()