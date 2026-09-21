#!/usr/bin/env bash
# Start Polaris Frontend & GCS Streaming Server
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$HOME/.local/bin:$PATH"

echo "=== Starting Polaris 360° Studio ==="

# Check if API server is already running on port 5001
if ! curl -s http://localhost:5001/api/health > /dev/null 2>&1; then
    echo "Starting backend API server on port 5001..."
    nohup python3 "$DIR/frontend/server/api_server.py" > /tmp/polaris_api.log 2>&1 &
    API_PID=$!
    disown $API_PID 2>/dev/null || true
    sleep 2
else
    echo "Backend API server is already running on port 5001."
fi

# Check if Vite dev server or production server
echo ""
echo "🚀 Polaris Frontend is ready!"
echo "Production SPA + API: http://localhost:5001"
echo ""
echo "To launch Vite Dev Server with Hot Reloading:"
echo "  cd $DIR/frontend && npm run dev"
echo ""
