#!/bin/zsh

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Virtual environment .venv not found."
  echo "Run first: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"
  read -k 1 "?Press any key to close..."
  exit 1
fi

echo "Starting Telegram bot..."
.venv/bin/python bot.py

echo
read -k 1 "?Bot stopped. Press any key to close..."
