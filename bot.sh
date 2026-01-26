#!/bin/bash
# Управление ботом: ./bot.sh start|stop|restart|status

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SCRIPT_DIR/bot.pid"

start() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "Bot already running (PID: $(cat $PID_FILE))"
        return 1
    fi

    echo "Starting bot..."
    cd "$SCRIPT_DIR"
    python3 main.py &
    echo $! > "$PID_FILE"
    sleep 2

    if kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "Bot started (PID: $(cat $PID_FILE))"
    else
        echo "Failed to start bot"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop() {
    # Убиваем по PID файлу
    if [ -f "$PID_FILE" ]; then
        kill $(cat "$PID_FILE") 2>/dev/null
        rm -f "$PID_FILE"
    fi

    # Убиваем все процессы main.py на всякий случай
    pkill -f "python.*main.py" 2>/dev/null
    pkill -f "Python.*main.py" 2>/dev/null

    echo "Bot stopped"
}

status() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "Bot running (PID: $(cat $PID_FILE))"
    else
        echo "Bot not running"
        rm -f "$PID_FILE" 2>/dev/null
    fi
}

case "$1" in
    start)   start ;;
    stop)    stop ;;
    restart) stop; sleep 2; start ;;
    status)  status ;;
    *)       echo "Usage: $0 {start|stop|restart|status}" ;;
esac
