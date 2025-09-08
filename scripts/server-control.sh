#!/bin/bash
# scripts/server-control.sh

# Farben
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# PID File
PID_FILE="/tmp/ra-autohaus-tracker.pid"
LOG_FILE="logs/server.log"

# Funktionen
start_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null; then
            echo -e "${YELLOW}⚠️  Server already running (PID: $PID)${NC}"
            echo "   Stop with: stop-server"
            return 1
        fi
    fi
    
    echo -e "${GREEN}🚀 Starting API server...${NC}"
    mkdir -p logs
    nohup python -m src.main > $LOG_FILE 2>&1 &
    echo $! > $PID_FILE
    
    sleep 2
    if ps -p $(cat $PID_FILE) > /dev/null; then
        echo -e "${GREEN}✅ Server started (PID: $(cat $PID_FILE))${NC}"
        echo "   URL: http://localhost:8080"
        echo "   Logs: tail -f $LOG_FILE"
        echo "   Stop: stop-server"
    else
        echo -e "${RED}❌ Server failed to start. Check logs: $LOG_FILE${NC}"
        rm -f $PID_FILE
    fi
}

stop_server() {
    if [ ! -f "$PID_FILE" ]; then
        echo -e "${YELLOW}No server running${NC}"
        return 1
    fi
    
    PID=$(cat $PID_FILE)
    if ps -p $PID > /dev/null; then
        echo -e "${YELLOW}⏹  Stopping server (PID: $PID)...${NC}"
        kill $PID
        rm -f $PID_FILE
        echo -e "${GREEN}✅ Server stopped${NC}"
    else
        echo -e "${YELLOW}Server not running, cleaning up PID file${NC}"
        rm -f $PID_FILE
    fi
}

status_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null; then
            echo -e "${GREEN}✅ Server running (PID: $PID)${NC}"
            echo "   URL: http://localhost:8080"
        else
            echo -e "${RED}❌ Server not running (stale PID file)${NC}"
            rm -f $PID_FILE
        fi
    else
        echo -e "${YELLOW}⚠️  Server not running${NC}"
    fi
}

# Main
case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    status)
        status_server
        ;;
    restart)
        stop_server
        sleep 1
        start_server
        ;;
    *)
        echo "Usage: $0 {start|stop|status|restart}"
        exit 1
        ;;
esac