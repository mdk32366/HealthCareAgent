#!/usr/bin/env python3
"""
Configuration verification script.

Checks that API keys and configuration are properly set up.
Run this before starting the application to ensure everything is ready.

Usage:
    python verify_config.py
"""
import json
import os
import sys
from pathlib import Path
from dataclasses import dataclass

BASE_DIR = Path(__file__).parent


@dataclass
class ConfigStatus:
    config_method: str
    anthropic_key_set: bool
    tavily_key_set: bool
    all_ok: bool
    warnings: list[str]


def check_configuration() -> ConfigStatus:
    """Check configuration and return status."""
    warnings = []
    config_method = None
    anthropic_key_set = False
    tavily_key_set = False

    # Check config.json
    config_json_path = BASE_DIR / "config.json"
    if config_json_path.exists():
        try:
            with open(config_json_path) as f:
                config = json.load(f)
            api_keys = config.get("api_keys", {})
            anthropic_key = api_keys.get("anthropic_api_key", "")
            tavily_key = api_keys.get("tavily_api_key", "")

            if anthropic_key and not anthropic_key.startswith("sk-ant-your-"):
                anthropic_key_set = True
                config_method = "config.json"
            else:
                warnings.append("⚠️  config.json: anthropic_api_key is empty or placeholder")

            if tavily_key and not tavily_key.startswith("tvly-your-"):
                tavily_key_set = True
            else:
                warnings.append("⚠️  config.json: tavily_api_key is empty or placeholder (optional)")

        except json.JSONDecodeError as e:
            warnings.append(f"❌ config.json is invalid JSON: {e}")

    # Check .env file
    env_file_path = BASE_DIR / ".env"
    if env_file_path.exists() and not config_method:
        try:
            with open(env_file_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ANTHROPIC_API_KEY="):
                        value = line.split("=", 1)[1]
                        if value and not value.startswith("sk-ant-your-"):
                            anthropic_key_set = True
                            config_method = ".env file"
                    elif line.startswith("TAVILY_API_KEY="):
                        value = line.split("=", 1)[1]
                        if value and not value.startswith("tvly-your-"):
                            tavily_key_set = True
        except Exception as e:
            warnings.append(f"❌ .env file error: {e}")

    # Check environment variables
    if not config_method:
        env_anthropic = os.getenv("ANTHROPIC_API_KEY", "")
        env_tavily = os.getenv("TAVILY_API_KEY", "")

        if env_anthropic:
            anthropic_key_set = True
            config_method = "environment variables"
        if env_tavily:
            tavily_key_set = True

    # Additional checks
    if not config_method:
        warnings.append("❌ No API keys found in config.json, .env, or environment variables")

    if not anthropic_key_set:
        warnings.append("❌ ANTHROPIC_API_KEY is required but not set")

    if not tavily_key_set:
        warnings.append("⚠️  TAVILY_API_KEY is not set (optional, but recommended)")

    all_ok = anthropic_key_set and config_method is not None

    return ConfigStatus(
        config_method=config_method or "None",
        anthropic_key_set=anthropic_key_set,
        tavily_key_set=tavily_key_set,
        all_ok=all_ok,
        warnings=warnings,
    )


def main():
    """Run configuration check."""
    print("\n" + "=" * 70)
    print("Healthcare RAG Agent — Configuration Verification")
    print("=" * 70 + "\n")

    status = check_configuration()

    # Display status
    print(f"Configuration Source:  {status.config_method}")
    print(f"Anthropic API Key:     {'✅ Set' if status.anthropic_key_set else '❌ Not set'}")
    print(f"Tavily API Key:        {'✅ Set' if status.tavily_key_set else '⚠️  Not set (optional)'}")

    # Display warnings
    if status.warnings:
        print("\n" + "-" * 70)
        print("Issues:")
        print("-" * 70)
        for warning in status.warnings:
            print(f"  {warning}")

    # Display result
    print("\n" + "-" * 70)
    if status.all_ok:
        print("✅ Configuration is valid! Ready to run the application.\n")
        return 0
    else:
        print("❌ Configuration issues detected. Please fix the above before running.\n")
        print("Setup instructions:")
        print("  1. Copy config.example.json → config.json")
        print("  2. Edit config.json and add your API keys")
        print("  3. Run this script again to verify\n")
        print("Or use .env file instead:")
        print("  1. Copy .env.example → .env")
        print("  2. Edit .env and add your API keys")
        print("  3. Run this script again to verify\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
