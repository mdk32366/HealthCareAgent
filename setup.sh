#!/usr/bin/env bash
# One-shot setup for Healthcare RAG Agent
set -e

echo "==> Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "==> Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Setting up .env..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "  !! Edit .env and add your API keys before running the agent."
fi

echo ""
echo "Setup complete. To start:"
echo "  source .venv/bin/activate"
echo "  python main.py ask \"What are the treatments for Type 2 diabetes?\""
