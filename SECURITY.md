# Security & Configuration Guide

## Overview

This project uses a **JSON-based configuration system** to securely manage API keys and secrets, with automatic fallback to environment variables for backward compatibility.

## ⚠️ Important: Protecting Secrets

**Never commit API keys or credentials to version control.**

The following files are protected in `.gitignore`:
- `config.json` — Your actual configuration with real API keys
- `.env` — Environment variables file
- `*.pyc`, `__pycache__/` — Python cache

### setup

## Setup Instructions

### Option 1: Production Setup (Recommended)

Best for deployment and team collaboration:

```bash
# 1. Copy the example configuration
cp config.example.json config.json

# 2. Edit config.json with your actual API keys
# {
#   "api_keys": {
#     "anthropic_api_key": "sk-ant-your-actual-key",
#     "tavily_api_key": "tvly-your-actual-key"
#   },
#   ...
# }

# 3. Verify config.json is in .gitignore (it is by default)
cat .gitignore | grep config.json

# 4. Double-check you never commit it
git status  # should NOT list config.json
```

### Option 2: Development Setup (.env File)

Simple setup for local development:

```bash
# 1. Copy the example environment file
cp .env.example .env

# 2. Edit .env with your API keys
# ANTHROPIC_API_KEY=sk-ant-your-actual-key
# TAVILY_API_KEY=tvly-your-actual-key

# 3. .env is already in .gitignore
git status  # should NOT list .env
```

## Configuration Precedence

Settings are loaded in this order (first match wins):

1. **config.json** — Production-recommended, JSON structured
2. **Environment variables** (.env or system env)
3. **Built-in defaults** — From config/settings.py

### Configuration Structure (config.json)

```json
{
  "api_keys": {
    "anthropic_api_key": "sk-ant-...",         // Required
    "tavily_api_key": "tvly-..."               // Recommended
  },
  "model": {
    "name": "claude-opus-4-5",
    "max_tokens": 4096,
    "embedding_model": "all-MiniLM-L6-v2"
  },
  "storage": {
    "chroma_persist_dir": "./data/chroma_db",
    "obsidian_vault_dir": "./data/obsidian_vault",
    "collection_name": "healthcare_knowledge"
  },
  "retrieval": {
    "top_k_retrieval": 12,
    "top_k_rerank": 6,
    "chunk_size": 800,
    "chunk_overlap": 120
  },
  // ... plus health_topics, therapy_dimensions, trusted_domains
}
```

### Environment Variables

If you prefer `.env`, these variables are supported:

```bash
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
CHROMA_PERSIST_DIR=./data/chroma_db
OBSIDIAN_VAULT_DIR=./data/obsidian_vault
MODEL=claude-opus-4-5
```

## How It Works

### Loading Configuration

The `config/settings.py` file automatically:

1. Looks for `config.json` in the project root
2. If found, loads all settings from it
3. If not found, falls back to `config.example.json` (safe defaults)
4. Checks environment variables (override)
5. Uses Python defaults as final fallback

### Why This Approach?

✅ **Security:**
- Secrets never in version control
- Single location for all configuration
- Easy to rotate credentials

✅ **Flexibility:**
- Works with config.json (production)
- Works with .env (development)
- Works with environment variables (CI/CD)
- Works with defaults (testing)

✅ **Team-Friendly:**
- Example file shows expected structure
- No credentials in repo
- Clear setup instructions

## Common Tasks

### Check Current Configuration

```python
from config.settings import settings

print(f"API Key Loaded: {bool(settings.anthropic_api_key)}")
print(f"Model: {settings.model}")
print(f"Topics: {settings.health_topics}")
```

### Verify Secrets Are Protected

```bash
# Should return EMPTY (no real config in git)
git ls-files | grep config.json
git ls-files | grep "\.env"

# Only example files should be tracked
git ls-files | grep example
git ls-files | grep gitignore
```

### Update Configuration After Deployment

Simply edit your `config.json` file—no code changes needed:

```bash
# Edit the file
nano config.json

# Save
# (no git commit needed—config.json is ignored)

# Restart your application
# New settings loaded automatically
```

## API Key Sources

### Anthropic API Key (Required)

1. Go to https://console.anthropic.com
2. Create an account or sign in
3. Generate an API key
4. Copy to `config.json` or `.env`

**Format:** `sk-ant-...`

### Tavily API Key (Recommended)

1. Go to https://tavily.com
2. Sign up (free tier available)
3. Get your API key from dashboard
4. Copy to `config.json` or `.env`

**Format:** `tvly-...`

## Troubleshooting

### "No API key found" Error

```
FileNotFoundError: anthropic_api_key not configured
```

**Solution:** Ensure either `config.json` or `.env` exists with your API keys.

### Settings Not Loading

```python
from config.settings import settings
print(settings.anthropic_api_key)  # Check if loaded
```

If empty:
- Check `config.json` or `.env` exists
- Verify API keys are filled in (not placeholder values)
- Check file permissions (should be readable)
- Try `.env` method if `config.json` isn't working

### Different Configs Per Environment

Name your files by environment:

```bash
config.json           # Production (loaded by default)
config.dev.json       # Development (manual override)
.env                  # Local secrets
.env.staging          # Staging secrets
```

Then manually load:

```python
import json
from pathlib import Path
from config.settings import _config_data

# Load specific environment config
with open("config.staging.json") as f:
    config_data = json.load(f)
```

## Best Practices

1. ✅ **Do** keep `config.example.json` in git (shows structure)
2. ✅ **Do** keep `.env.example` in git (for reference)
3. ✅ **Do** add `config.json` and `.env` to `.gitignore`
4. ❌ **Don't** commit real API keys or credentials
5. ❌ **Don't** share your `config.json` file unencrypted
6. ✅ **Do** rotate API keys regularly
7. ✅ **Do** use different credentials per environment

## Additional Security Tips

- **Rotate keys regularly:** Regenerate API keys if access is suspected
- **Use IAM roles:** On AWS/GCP, use service account roles instead of static keys
- **Audit access:** Check API key usage on Anthropic/Tavily dashboards
- **Encrypt at rest:** If deploying, use secrets management (AWS Secrets Manager, HashiCorp Vault)
- **Use CI/CD secrets:** GitHub Actions → Settings → Secrets & variables

---

For questions or security concerns, please open an issue on GitHub.
