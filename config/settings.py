"""
Central configuration for the Healthcare RAG Agent.

Loads configuration from config.json (with fallback to environment variables).
Keep config.json out of version control by adding it to .gitignore.
See config.example.json for the configuration structure.
"""
from pydantic import BaseModel, Field
from pathlib import Path
import os
import json
import logging
from dotenv import load_dotenv

log = logging.getLogger(__name__)

# Load .env file for backwards compatibility and environment-specific overrides
load_dotenv()

BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "config.json"
CONFIG_EXAMPLE_FILE = BASE_DIR / "config.example.json"


def _load_config_json() -> dict:
    """Load configuration from config.json, with fallback to config.example.json."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            log.warning(f"Failed to load config.json: {e}. Using example config.")
    
    # Fallback to example config if main config doesn't exist
    if CONFIG_EXAMPLE_FILE.exists():
        with open(CONFIG_EXAMPLE_FILE, 'r') as f:
            return json.load(f)
    
    return {}


# Load configuration from JSON
_config_data = _load_config_json()


class Settings(BaseModel):
    # ── Anthropic ──────────────────────────────────────────────────
    anthropic_api_key: str = Field(
        default_factory=lambda: os.getenv(
            "ANTHROPIC_API_KEY",
            _config_data.get("api_keys", {}).get("anthropic_api_key", "")
        )
    )
    model: str = Field(
        default_factory=lambda: _config_data.get("model", {}).get("name", "claude-opus-4-5")
    )
    max_tokens: int = Field(
        default_factory=lambda: _config_data.get("model", {}).get("max_tokens", 4096)
    )

    # ── Tavily web search (free tier available) ─────────────────────
    tavily_api_key: str = Field(
        default_factory=lambda: os.getenv(
            "TAVILY_API_KEY",
            _config_data.get("api_keys", {}).get("tavily_api_key", "")
        )
    )

    # ── Memory / vector store ───────────────────────────────────────
    chroma_persist_dir: Path = Field(
        default_factory=lambda: Path(
            os.getenv(
                "CHROMA_PERSIST_DIR",
                _config_data.get("storage", {}).get("chroma_persist_dir", "./data/chroma_db")
            )
        )
    )
    obsidian_vault_dir: Path = Field(
        default_factory=lambda: Path(
            os.getenv(
                "OBSIDIAN_VAULT_DIR",
                _config_data.get("storage", {}).get("obsidian_vault_dir", "./data/obsidian_vault")
            )
        )
    )
    collection_name: str = Field(
        default_factory=lambda: _config_data.get("storage", {}).get("collection_name", "healthcare_knowledge")
    )
    embedding_model: str = Field(
        default_factory=lambda: _config_data.get("model", {}).get("embedding_model", "all-MiniLM-L6-v2")
    )

    # ── Retrieval ───────────────────────────────────────────────────
    top_k_retrieval: int = Field(
        default_factory=lambda: _config_data.get("retrieval", {}).get("top_k_retrieval", 12)
    )
    top_k_rerank: int = Field(
        default_factory=lambda: _config_data.get("retrieval", {}).get("top_k_rerank", 6)
    )
    chunk_size: int = Field(
        default_factory=lambda: _config_data.get("retrieval", {}).get("chunk_size", 800)
    )
    chunk_overlap: int = Field(
        default_factory=lambda: _config_data.get("retrieval", {}).get("chunk_overlap", 120)
    )
    health_topics: list[str] = Field(
        default_factory=lambda: _config_data.get("health_topics", [
            "vaccines", "cancer", "hemophilia", "weight control", "diabetes"
        ])
    )

    # ── Therapy dimensions (always presented) ───────────────────────
    therapy_dimensions: list[str] = Field(
        default_factory=lambda: _config_data.get("therapy_dimensions", [
            "FDA-approved / clinical",
            "Homeopathic / naturopathic",
            "Supplementation",
            "Surgical / procedural",
        ])
    )

    # ── Trusted source domains for web crawling ──────────────────────
    trusted_domains: list[str] = Field(
        default_factory=lambda: _config_data.get("trusted_domains", [
            "nih.gov", "pubmed.ncbi.nlm.nih.gov", "cdc.gov", "fda.gov",
            "who.int", "cancer.gov", "cancer.org", "mayoclinic.org",
            "medlineplus.gov", "hopkinsmedicine.org", "clevelandclinic.org",
            "hemophilia.org", "nhlbi.nih.gov", "diabetes.org",
            "niddk.nih.gov", "nccih.nih.gov",
            "examine.com",
            "cochranelibrary.com",
        ])
    )

    class Config:
        arbitrary_types_allowed = True


settings = Settings()
