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

stop_catalog_browser() {
  BROWSER_PIDS="$(pgrep -f "$CRM_PROFILE_DIR" 2>/dev/null)"
  if [ -n "$BROWSER_PIDS" ]; then
    echo "Stopping leftover CRM browser processes..."
    kill_pid_list "$BROWSER_PIDS"
    sleep 0.5
  fi

  CHROMEDRIVER_PIDS="$(pgrep -f "chromedriver" 2>/dev/null)"
  if [ -n "$CHROMEDRIVER_PIDS" ]; then
    echo "Stopping leftover chromedriver processes..."
    kill_pid_list "$CHROMEDRIVER_PIDS"
    sleep 0.5
  fi
}

stop_existing_bot() {
  if [ ! -f "$PID_FILE" ]; then
    LEGACY_PIDS="$(pgrep -f "bot.py" 2>/dev/null)"
    if [ -n "$LEGACY_PIDS" ]; then
      echo "Stopping existing Telegram bot without PID file..."
      for PID in ${(f)LEGACY_PIDS}; do
        if [ -n "$PID" ] && [ "$PID" != "$$" ] && kill -0 "$PID" 2>/dev/null; then
          kill "$PID" 2>/dev/null
        fi
      done
      sleep 1
    fi
    rm -f "$LOCK_FILE"
    stop_catalog_browser
    return
  fi

  PID="$(tr -dc '0-9' < "$PID_FILE")"
  if [ -z "$PID" ]; then
    rm -f "$PID_FILE" "$LOCK_FILE"
    stop_catalog_browser
    return
  fi

  if ! kill -0 "$PID" 2>/dev/null; then
    echo "Old bot PID file found, but process is not running."
    rm -f "$PID_FILE" "$LOCK_FILE"
    stop_catalog_browser
    return
  fi

  echo "Stopping existing Telegram bot (PID $PID)..."
  kill "$PID" 2>/dev/null

  for _ in {1..20}; do
    if ! kill -0 "$PID" 2>/dev/null; then
      break
    fi
    sleep 0.25
  done

  if kill -0 "$PID" 2>/dev/null; then
    echo "Existing bot did not stop, forcing stop..."
    kill -9 "$PID" 2>/dev/null
    sleep 0.5
  fi

  rm -f "$PID_FILE" "$LOCK_FILE"
  stop_catalog_browser
}

if [ ! -d ".venv" ]; then
  echo "Virtual environment .venv not found."
  echo "Run first: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"
  read -k 1 "?Press any key to close..."
  exit 1
fi

stop_existing_bot

echo "Starting Telegram bot..."
.venv/bin/python bot.py

echo
read -k 1 "?Bot stopped. Press any key to close..."
