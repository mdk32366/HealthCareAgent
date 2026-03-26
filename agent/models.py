"""
Shared data models for the Healthcare RAG Agent.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time


class TherapyDimension(str, Enum):
    FDA_CLINICAL   = "FDA-approved / clinical"
    HOMEOPATHIC    = "Homeopathic / naturopathic"
    SUPPLEMENTATION = "Supplementation"
    SURGICAL       = "Surgical / procedural"


class HealthTopic(str, Enum):
    VACCINES     = "vaccines"
    CANCER       = "cancer"
    HEMOPHILIA   = "hemophilia"
    WEIGHT       = "weight control"
    DIABETES     = "diabetes"
    GENERAL      = "general"


@dataclass
class SourceDocument:
    """A single retrieved or scraped document chunk."""
    content: str
    url: str
    title: str
    source_type: str          # "web", "youtube", "obsidian", "vector_store"
    topic: str = ""
    therapy_dimension: str = ""
    relevance_score: float = 0.0
    published_date: str = ""
    chunk_id: str = ""

    def to_citation(self) -> str:
        title = self.title or self.url
        date  = f" ({self.published_date})" if self.published_date else ""
        return f"[{title}{date}]({self.url})"


@dataclass
class RetrievedContext:
    """Bundle of ranked source documents passed to the synthesizer."""
    documents: list[SourceDocument]
    query: str
    topic: HealthTopic
    detected_dimensions: list[TherapyDimension]

    def format_for_prompt(self) -> str:
        parts = []
        for i, doc in enumerate(self.documents, 1):
            parts.append(
                f"[SOURCE {i}] {doc.title}\n"
                f"URL: {doc.url}\n"
                f"Dimension: {doc.therapy_dimension or 'general'}\n"
                f"---\n{doc.content}\n"
            )
        return "\n\n".join(parts)

    def all_citations(self) -> list[str]:
        seen, out = set(), []
        for doc in self.documents:
            if doc.url not in seen:
                out.append(doc.to_citation())
                seen.add(doc.url)
        return out


@dataclass
class AgentResponse:
    """Final structured answer returned to the user."""
    answer: str
    topic: HealthTopic
    therapy_sections: dict[str, str]   # dimension → content
    citations: list[str]
    youtube_links: list[str]
    safety_disclaimer: str
    memory_note: str = ""              # what was written to memory
    elapsed_seconds: float = 0.0

    def render(self) -> str:
        """Pretty-print for terminal / downstream use."""
        lines = [
            f"\n{'='*70}",
            f"  Healthcare RAG Agent — {self.topic.value.title()}",
            f"{'='*70}\n",
            self.answer,
            "",
        ]

        if self.therapy_sections:
            lines.append("─── Therapy Options ───────────────────────────────────────────────")
            for dim, content in self.therapy_sections.items():
                if content.strip():
                    lines.append(f"\n**{dim}**\n{content}")

        if self.youtube_links:
            lines.append("\n─── Video Resources ────────────────────────────────────────────────")
            for link in self.youtube_links:
                lines.append(f"  • {link}")

        if self.citations:
            lines.append("\n─── Sources & Citations ─────────────────────────────────────────────")
            for i, c in enumerate(self.citations, 1):
                lines.append(f"  [{i}] {c}")

        lines.append(f"\n⚠️  {self.safety_disclaimer}")
        lines.append(f"\n(Generated in {self.elapsed_seconds:.1f}s)")
        return "\n".join(lines)
