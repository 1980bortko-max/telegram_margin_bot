#!/bin/zsh

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR" || exit 1

PID_FILE=".bot.pid"
LOCK_FILE=".bot.lock"
CRM_PROFILE_DIR="$PROJECT_DIR/.crm_chrome_profile"

kill_pid_list() {
  local PIDS="$1"
  for PID in ${(f)PIDS}; do
    if [ -n "$PID" ] && [ "$PID" != "$$" ] && kill -0 "$PID" 2>/dev/null; then
      kill "$PID" 2>/dev/null
    fi
  done
}

stop_existing_bot() {
  if [ -f "$PID_FILE" ]; then
    PID="$(tr -dc '0-9' < "$PID_FILE")"
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
      echo "Stopping Telegram bot (PID $PID)..."
      kill "$PID" 2>/dev/null
      sleep 1
    fi
  fi

  LEGACY_PIDS="$(pgrep -f "bot.py" 2>/dev/null)"
  if [ -n "$LEGACY_PIDS" ]; then
    echo "Stopping hidden Telegram bot processes..."
    kill_pid_list "$LEGACY_PIDS"
    sleep 1
  fi

  rm -f "$PID_FILE" "$LOCK_FILE"
}

stop_catalog_browser() {
  BROWSER_PIDS="$(pgrep -f "$CRM_PROFILE_DIR" 2>/dev/null)"
  if [ -n "$BROWSER_PIDS" ]; then
    echo "Stopping CRM browser processes..."
    kill_pid_list "$BROWSER_PIDS"
    sleep 0.5
  fi

  CHROMEDRIVER_PIDS="$(pgrep -f "chromedriver" 2>/dev/null)"
  if [ -n "$CHROMEDRIVER_PIDS" ]; then
    echo "Stopping chromedriver processes..."
    kill_pid_list "$CHROMEDRIVER_PIDS"
    sleep 0.5
  fi
}

stop_existing_bot
stop_catalog_browser

echo
echo "Bot stopped."
read -k 1 "?Press any key to close..."
