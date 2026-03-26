"""
Central configuration for the Healthcare RAG Agent.
"""
from pydantic import BaseModel, Field
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent

class Settings(BaseModel):
    # ── Anthropic ──────────────────────────────────────────────────
    anthropic_api_key: str = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    model: str = "claude-opus-4-5"
    max_tokens: int = 4096

    # ── Tavily web search (free tier available) ─────────────────────
    tavily_api_key: str = Field(default_factory=lambda: os.getenv("TAVILY_API_KEY", ""))

    # ── Memory / vector store ───────────────────────────────────────
    chroma_persist_dir: Path = BASE_DIR / "data" / "chroma_db"
    obsidian_vault_dir: Path = BASE_DIR / "data" / "obsidian_vault"
    collection_name: str = "healthcare_knowledge"
    embedding_model: str = "all-MiniLM-L6-v2"   # local, fast, free

    # ── Retrieval ───────────────────────────────────────────────────
    top_k_retrieval: int = 12
    top_k_rerank: int = 6
    chunk_size: int = 800
    chunk_overlap: int = 120

    # ── Topics ──────────────────────────────────────────────────────
    health_topics: list[str] = [
        "vaccines", "cancer", "hemophilia",
        "weight control", "diabetes",
    ]

    # ── Therapy dimensions (always presented) ───────────────────────
    therapy_dimensions: list[str] = [
        "FDA-approved / clinical",
        "Homeopathic / naturopathic",
        "Supplementation",
        "Surgical / procedural",
    ]

    # ── Trusted source domains for web crawling ──────────────────────
    trusted_domains: list[str] = [
        "nih.gov", "pubmed.ncbi.nlm.nih.gov", "cdc.gov", "fda.gov",
        "who.int", "cancer.gov", "cancer.org", "mayoclinic.org",
        "medlineplus.gov", "hopkinsmedicine.org", "clevelandclinic.org",
        "hemophilia.org", "nhlbi.nih.gov", "diabetes.org",
        "niddk.nih.gov", "nccih.nih.gov",     # NIH complementary/integrative
        "examine.com",                          # supplements
        "cochranelibrary.com",                  # systematic reviews
    ]

    class Config:
        arbitrary_types_allowed = True


settings = Settings()
