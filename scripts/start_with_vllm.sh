#!/bin/bash

echo "🚀 Starting Telecom MCP Ecosystem with vLLM..."

# Check if GPU is available
if command -v nvidia-smi >/dev/null 2>&1; then
    echo "✅ GPU detected - using GPU-accelerated vLLM"
    COMPOSE_FILE="docker-compose.yml"
else
    echo "⚠️  No GPU detected - using CPU-only deployment"
    COMPOSE_FILE="docker-compose.cpu.yml"
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your API credentials before continuing"
    read -p "Press Enter after editing .env file..."
fi

# Create logs directory
mkdir -p logs

echo "🏗️  Building and starting services..."

# Start services
docker-compose -f $COMPOSE_FILE up -d --build

echo "⏳ Waiting for services to start..."
sleep 30

# Health check
echo "🏥 Checking service health..."

services=("http://localhost:8000/health" "http://localhost:8001/health" "http://localhost:8002/health")
service_names=("Orchestrator" "Telco MCP" "Vector DB MCP")

for i in "${!services[@]}"; do
    url="${services[$i]}"
    name="${service_names[$i]}"
    
    if curl -s "$url" > /dev/null; then
        echo "✅ $name: Healthy"
    else
        echo "❌ $name: Not responding"
    fi
done

# Check vLLM
if curl -s "http://localhost:8080/v1/models" > /dev/null; then
    echo "✅ vLLM Service: Healthy"
else
    echo "❌ vLLM Service: Not responding (this may take a few minutes to start)"
fi

echo ""
echo "🎉 Telecom MCP Ecosystem Started!"
echo ""
echo "📋 Service URLs:"
echo "   • Main Interface (Chat): http://localhost:8000"
echo "   • API Documentation: http://localhost:8000/docs"
echo "   • Health Check: http://localhost:8000/health"
echo "   • Telco MCP: http://localhost:8001"
echo "   • Vector DB MCP: http://localhost:8002"
echo "   • vLLM API: http://localhost:8080"
echo "   • ChromaDB: http://localhost:8003"
echo ""
echo "🧪 Test the chat interface:"
echo '   curl -X POST "http://localhost:8000/chat" \'
echo '     -H "Content-Type: application/json" \'
echo '     -d '"'"'{"query": "Cek traffic MSISDN 08123456789 kemarin"}'"'"
echo ""
echo "📊 View logs:"
echo "   docker-compose -f $COMPOSE_FILE logs -f"
echo ""
echo "🛑 Stop services:"
echo "   docker-compose -f $COMPOSE_FILE down"