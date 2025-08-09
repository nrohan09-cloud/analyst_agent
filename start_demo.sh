#!/bin/bash

# Start Demo Script for Analyst Agent
# This script starts both the API server and frontend

echo "🚀 Starting Analyst Agent Demo..."
echo

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Please run this script from the analyst_agent project root directory"
    exit 1
fi

# Check if virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  No virtual environment detected. Activating venv..."
    if [ -d ".venv" ]; then
        source .venv/bin/activate
        echo "✅ Virtual environment activated"
    else
        echo "❌ No venv directory found. Please run: python -m venv venv && source venv/bin/activate && pip install -e ."
        exit 1
    fi
fi

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Check if API is already running
if check_port 8000; then
    echo "✅ API already running on port 8000"
else
    echo "🔧 Starting API server on port 8000..."
    # Start API in background
    python main.py > api.log 2>&1 &
    API_PID=$!
    echo "📝 API PID: $API_PID (logs: api.log)"
    
    # Wait for API to start
    echo "⏳ Waiting for API to start..."
    for i in {1..10}; do
        if check_port 8000; then
            echo "✅ API server started successfully"
            break
        fi
        if [ $i -eq 10 ]; then
            echo "❌ API failed to start within 10 seconds"
            exit 1
        fi
        sleep 1
    done
fi

# Check if frontend is already running
if check_port 3001; then
    echo "✅ Frontend already running on port 3001"
else
    echo "🔧 Starting frontend server on port 3001..."
    # Start frontend in background
    cd frontend
    npm run dev > ../frontend.log 2>&1 &
    FRONTEND_PID=$!
    cd ..
    echo "📝 Frontend PID: $FRONTEND_PID (logs: frontend.log)"
    
    # Wait for frontend to start
    echo "⏳ Waiting for frontend to start..."
    for i in {1..10}; do
        if check_port 3001; then
            echo "✅ Frontend server started successfully"
            break
        fi
        if [ $i -eq 10 ]; then
            echo "❌ Frontend failed to start within 10 seconds"
            exit 1
        fi
        sleep 1
    done
fi

echo
echo "🎉 Demo is ready!"
echo
echo "📡 API Server:  http://localhost:8000"
echo "   📖 API Docs: http://localhost:8000/docs"
echo "🌐 Frontend:   http://localhost:3001"
echo
echo "💡 Try these example questions:"
echo "   • Show me total sales by month"
echo "   • What are the top 5 products by revenue?"
echo "   • How many users signed up this week?"
echo
echo "🔧 To stop the servers:"
echo "   • Press Ctrl+C or run: pkill -f 'python main.py' && pkill -f 'http-server'"
echo
echo "📋 Logs:"
echo "   • API: tail -f api.log"
echo "   • Frontend: tail -f frontend.log"
echo

# Keep script running
echo "Press Ctrl+C to stop all services..."
trap 'echo "🛑 Stopping services..."; kill $API_PID $FRONTEND_PID 2>/dev/null; exit 0' INT
wait 