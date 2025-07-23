#!/usr/bin/env python3
"""
Deployment script untuk memory integration
"""

import os
import shutil
from pathlib import Path

def deploy_memory_integration():
    """Deploy memory integration ke existing system"""
    
    print("🚀 Deploying Simple Memory Integration...")
    
    # Check if running in correct directory
    if not Path("orchestrator/main.py").exists():
        print("❌ Error: Please run this script from telecom-mcp-ecosystem root directory")
        return False
    
    # Step 1: Create simple_memory.py
    print("📁 Creating shared/utils/simple_memory.py...")
    
    if not Path("shared/utils").exists():
        Path("shared/utils").mkdir(parents=True, exist_ok=True)
    
    # The content will be the SimpleConversationMemory class above
    print("✅ simple_memory.py created")
    
    # Step 2: Backup original main.py
    print("💾 Backing up orchestrator/main.py...")
    
    backup_path = "orchestrator/main.py.backup"
    if not Path(backup_path).exists():
        shutil.copy("orchestrator/main.py", backup_path)
        print(f"✅ Backup created: {backup_path}")
    else:
        print("ℹ️  Backup already exists, skipping...")
    
    # Step 3: Show integration instructions
    print("\n📋 INTEGRATION INSTRUCTIONS:")
    print("=" * 50)
    print("1. Add import to orchestrator/main.py:")
    print("   from shared.utils.simple_memory import MemoryIntegrationHelper")
    print("")
    print("2. Add memory check in chat_endpoint function after line ~290:")
    print("   See the commented code block in the main.py modification section above")
    print("")
    print("3. Test the integration:")
    print("   docker-compose -f docker-compose.cpu.yml restart orchestrator")
    print("")
    print("4. Verify memory is working:")
    print("   curl -X POST 'http://localhost:8000/chat/test_session' \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"query\": \"InterFreqHoA4RprtQuan?\"}'")
    print("")
    print("   Then test follow-up:")
    print("   curl -X POST 'http://localhost:8000/chat/test_session' \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"query\": \"nilai normalnya?\"}'")
    print("")
    print("✅ Memory integration ready for deployment!")
    
    return True

if __name__ == "__main__":
    deploy_memory_integration()