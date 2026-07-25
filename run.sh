#!/bin/bash

# CheckIn Real-Time Voice Server Launcher

echo "================================"
echo "  CheckIn Real-Time Voice"
echo "================================"
echo ""

# Check if we're in the right directory
if [ ! -f "server.py" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo "Error: .env file not found"
    echo "Please create .env with DEEPGRAM_API_KEY and GEMINI_API_KEY"
    exit 1
fi

# Check for required packages
echo "Checking dependencies..."
python -c "import pipecat" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "Starting voice server on ws://localhost:8765"
echo "Starting frontend on http://localhost:8080"
echo ""
echo "Press Ctrl+C to stop"
echo "================================"
echo ""

# Start frontend server in background
python3 -m http.server 8080 --directory docs &
FRONTEND_PID=$!

# Start voice server in foreground
python3 server.py

# Clean up frontend server on exit
kill $FRONTEND_PID 2>/dev/null
