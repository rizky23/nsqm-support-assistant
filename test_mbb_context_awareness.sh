#!/bin/bash
# test_mbb_context_awareness.sh
# Testing scenarios focused on MBB Knowledge Base & Context Awareness

BASE_URL="http://localhost:8000"
TIMESTAMP=$(date +%s)
TEST_CONVERSATION_ID="mbb_test_$TIMESTAMP"

echo "🧠 Testing MBB Knowledge Base Context Awareness"
echo "==============================================="
echo "Base URL: $BASE_URL"
echo "Test Conversation ID: $TEST_CONVERSATION_ID"
echo "Focus: Parameter knowledge, context memory, smart routing"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Function to test MBB scenarios
test_mbb_scenario() {
    local test_name="$1"
    local query="$2"
    local expected="$3"
    
    echo -e "${BLUE}📋 $test_name${NC}"
    echo -e "${PURPLE}Query:${NC} \"$query\""
    echo -e "${PURPLE}Expected:${NC} $expected"
    echo "---"
    
    response=$(curl -s -X POST "$BASE_URL/chat/$TEST_CONVERSATION_ID" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\"}")
    
    if [ $? -eq 0 ]; then
        success=$(echo "$response" | jq -r '.success')
        if [ "$success" = "true" ]; then
            echo -e "${GREEN}✅ API Response Success${NC}"
            
            # Show response preview
            echo -e "${YELLOW}Response Preview:${NC}"
            echo "$response" | jq -r '.response' | head -4
            echo ""
            
            # Show tools used
            tools_used=$(echo "$response" | jq -r '.tools_used[]? // empty' 2>/dev/null)
            if [ ! -z "$tools_used" ]; then
                echo -e "${YELLOW}Tools Used:${NC} $tools_used"
            fi
            
            # Extract metadata if available
            echo -e "${YELLOW}Context Info:${NC}"
            echo "$response" | jq '{
                intent: .metadata.intent // "unknown",
                entities: .metadata.entities // {},
                topics: .metadata.topics // [],
                processing_time: .metadata.processing_time_ms // 0
            }' 2>/dev/null || echo "No context metadata available"
            
        else
            echo -e "${RED}❌ API returned error${NC}"
            echo "$response" | jq -r '.response'
        fi
    else
        echo -e "${RED}❌ API call failed${NC}"
    fi
    
    echo ""
    echo "----------------------------------------"
    sleep 3
}

# Test Health First
echo -e "${YELLOW}🔍 Health Check${NC}"
health_response=$(curl -s "$BASE_URL/health")
mbb_health=$(echo "$health_response" | jq -r '.servers.mbb // "unknown"')
echo "MBB Server Status: $mbb_health"

if [ "$mbb_health" != "healthy" ]; then
    echo -e "${RED}⚠️  MBB server not healthy, tests may fail${NC}"
fi
echo ""

# Test 1: Basic Parameter Query
echo -e "${YELLOW}📚 Phase 1: Basic Parameter Knowledge${NC}"

test_mbb_scenario \
    "Test 1.1: Specific Parameter Query" \
    "Jelaskan parameter InterFreqHoA4RprtQuan" \
    "Should route to MBB, extract parameter entity, provide detailed explanation"

test_mbb_scenario \
    "Test 1.2: RSRP Parameter Query" \
    "Apa itu parameter rsrpThresholdIdle dan fungsinya?" \
    "Should detect parameter intent, route to MBB knowledge base"

test_mbb_scenario \
    "Test 1.3: Handover Parameter Query" \
    "Parameter untuk optimasi handover di LTE" \
    "Should detect 4G optimization topic, route to MBB"

# Test 2: Context-Aware Follow-ups
echo -e "${YELLOW}🔄 Phase 2: Context Awareness - Parameter Follow-ups${NC}"

test_mbb_scenario \
    "Test 2.1: Follow-up Value Query" \
    "Berapa nilai normalnya?" \
    "Should remember previous parameter context"

test_mbb_scenario \
    "Test 2.2: Follow-up Range Query" \
    "Apa range valuenya yang direkomendasikan?" \
    "Should maintain parameter context from previous queries"

test_mbb_scenario \
    "Test 2.3: Follow-up Impact Query" \
    "Kalau valuenya terlalu tinggi efeknya apa?" \
    "Should continue parameter discussion with context"

# Test 3: Topic Switching with Context
echo -e "${YELLOW}🎯 Phase 3: Topic Switching & Context Maintenance${NC}"

test_mbb_scenario \
    "Test 3.1: New Parameter Introduction" \
    "Bagaimana dengan parameter dlschPdschPowerOffset?" \
    "Should switch to new parameter but maintain 4G optimization context"

test_mbb_scenario \
    "Test 3.2: Context-aware Comparison" \
    "Mana yang lebih penting antara parameter ini dengan yang sebelumnya?" \
    "Should remember both parameters discussed"

test_mbb_scenario \
    "Test 3.3: Optimization Context" \
    "Parameter mana yang harus diprioritaskan untuk optimize throughput?" \
    "Should use accumulated parameter knowledge for recommendation"

# Test 4: Complex Scenarios
echo -e "${YELLOW}🧪 Phase 4: Complex Context Scenarios${NC}"

test_mbb_scenario \
    "Test 4.1: Multi-parameter Query" \
    "Hubungan antara InterFreqHoA4RprtQuan dan rsrpThresholdIdle dalam optimasi jaringan" \
    "Should handle multiple parameters and provide comprehensive analysis"

test_mbb_scenario \
    "Test 4.2: Troubleshooting Context" \
    "Jika ada masalah frequent handover, parameter mana yang perlu dicek?" \
    "Should combine troubleshooting intent with parameter knowledge"

test_mbb_scenario \
    "Test 4.3: Best Practice Query" \
    "Best practice setting untuk semua parameter yang sudah kita bahas" \
    "Should summarize all parameters discussed in conversation"

# Test 5: Edge Cases
echo -e "${YELLOW}⚠️  Phase 5: Edge Cases & Error Handling${NC}"

test_mbb_scenario \
    "Test 5.1: Unknown Parameter" \
    "Jelaskan parameter XyzInvalidParam123" \
    "Should handle unknown parameter gracefully"

test_mbb_scenario \
    "Test 5.2: General 4G Query" \
    "Bagaimana cara optimize jaringan 4G secara umum?" \
    "Should route to MBB for general 4G knowledge"

test_mbb_scenario \
    "Test 5.3: Ambiguous Query" \
    "Parameter yang bagus" \
    "Should ask for clarification while maintaining context"

# Test 6: Conversation Analysis
echo -e "${YELLOW}📊 Phase 6: Conversation Analysis${NC}"

echo "📋 Checking conversation history and analysis..."
conversation_response=$(curl -s "$BASE_URL/conversations/$TEST_CONVERSATION_ID")
message_count=$(echo "$conversation_response" | jq '.message_count // 0')
echo "Total messages: $message_count"

if [ "$message_count" -gt 0 ]; then
    echo -e "${GREEN}✅ Conversation persistence working${NC}"
    
    # Get conversation summary
    echo ""
    echo "📊 Conversation Summary:"
    echo "$conversation_response" | jq '{
        message_count: .message_count,
        summary: .summary,
        entities: .entities // {},
        topics: .active_topics // []
    }' 2>/dev/null || echo "Summary not available"
    
    # Try conversation analysis
    echo ""
    echo "🔍 Detailed Conversation Analysis:"
    analysis_response=$(curl -s -X POST "$BASE_URL/conversations/$TEST_CONVERSATION_ID/analyze")
    echo "$analysis_response" | jq '.analysis // {}' 2>/dev/null || echo "Analysis not available"
    
else
    echo -e "${RED}❌ No conversation history found${NC}"
fi

# Test 7: Context Memory Persistence
echo -e "${YELLOW}🧠 Phase 7: Context Memory Test${NC}"

test_mbb_scenario \
    "Test 7.1: Memory Recall" \
    "Ingatkan saya parameter apa saja yang sudah kita bahas" \
    "Should recall all parameters discussed in this conversation"

test_mbb_scenario \
    "Test 7.2: Context-based Recommendation" \
    "Berdasarkan diskusi kita, apa rekomendasi optimasi prioritas?" \
    "Should provide recommendations based on full conversation context"

# Final Summary
echo ""
echo -e "${YELLOW}📈 Test Summary${NC}"
echo "=================================="
echo "Test Conversation ID: $TEST_CONVERSATION_ID"
echo "Total test scenarios: 16"
echo ""
echo "🎯 Key Features Tested:"
echo "✓ Parameter entity extraction"
echo "✓ 4G optimization intent detection"  
echo "✓ MBB knowledge base routing"
echo "✓ Context-aware follow-up responses"
echo "✓ Multi-parameter conversation handling"
echo "✓ Topic switching with context maintenance"
echo "✓ Conversation memory and persistence"
echo "✓ Complex scenario handling"
echo ""
echo "💡 Next Steps:"
echo "1. Review conversation at: $BASE_URL/conversations/$TEST_CONVERSATION_ID"
echo "2. Check health status: $BASE_URL/health"
echo "3. Analyze conversation: $BASE_URL/conversations/$TEST_CONVERSATION_ID/analyze"
echo ""
echo -e "${GREEN}✅ MBB Context Awareness Testing Complete!${NC}"