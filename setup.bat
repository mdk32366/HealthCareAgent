@echo off
echo ==> Creating virtual environment...
python -m venv .venv
call .venv\Scripts\activate

echo ==> Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo ==> Setting up .env...
if not exist .env (
  copy .env.example .env
  echo.
  echo   !! Edit .env and add your API keys before running the agent.
)

echo.
echo Setup complete. To start:
echo   .venv\Scripts\activate
echo   python main.py ask "What are the treatments for Type 2 diabetes?"
