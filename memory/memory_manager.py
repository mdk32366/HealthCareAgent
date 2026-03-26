"""
Persistent memory layer:
  1. ChromaDB vector store  — semantic search over all retrieved chunks
  2. Obsidian vault writer  — Markdown notes per Q&A session (human-readable)

Both are written to after every answer so knowledge compounds over time.
"""
from __future__ import annotations
import hashlib, json, logging, re, time
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings import settings
from agent.models import SourceDocument, AgentResponse, HealthTopic

log = logging.getLogger(__name__)


# ─── ChromaDB vector store ────────────────────────────────────────────────────

class VectorMemory:
    """
    Thin wrapper around ChromaDB for storing and retrieving
    healthcare document chunks.
    """

    def __init__(self):
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer
            self._client = chromadb.PersistentClient(
                path=str(settings.chroma_persist_dir)
            )
            self._collection = self._client.get_or_create_collection(
                name=settings.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._encoder = SentenceTransformer(settings.embedding_model)
            self._available = True
            log.info(f"ChromaDB ready ({self._collection.count()} docs)")
        except ImportError:
            log.warning("chromadb / sentence-transformers not installed — vector memory disabled")
            self._available = False
        except Exception as exc:
            log.error(f"ChromaDB init error: {exc}")
            self._available = False

    # ── Upsert ────────────────────────────────────────────────────────────────
    def upsert(self, docs: list[SourceDocument]) -> int:
        """Add or update document chunks. Returns number added."""
        if not self._available or not docs:
            return 0
        ids, embeddings, metadatas, texts = [], [], [], []
        for doc in docs:
            if not doc.content.strip():
                continue
            chunk_id = doc.chunk_id or hashlib.md5(
                f"{doc.url}{doc.content[:50]}".encode()
            ).hexdigest()
            ids.append(chunk_id)
            texts.append(doc.content[:1000])
            metadatas.append({
                "url":               doc.url,
                "title":             doc.title[:200],
                "source_type":       doc.source_type,
                "topic":             doc.topic,
                "therapy_dimension": doc.therapy_dimension,
                "published_date":    doc.published_date,
            })

        if not ids:
            return 0

        try:
            embeds = self._encoder.encode(texts, show_progress_bar=False).tolist()
            self._collection.upsert(
                ids=ids,
                embeddings=embeds,
                documents=texts,
                metadatas=metadatas,
            )
            log.info(f"Upserted {len(ids)} chunks to ChromaDB")
            return len(ids)
        except Exception as exc:
            log.error(f"ChromaDB upsert error: {exc}")
            return 0

    # ── Query ─────────────────────────────────────────────────────────────────
    def query(
        self,
        query_text: str,
        top_k: int = 8,
        topic_filter: Optional[str] = None,
    ) -> list[SourceDocument]:
        """Semantic search. Returns ranked SourceDocuments."""
        if not self._available:
            return []
        try:
            embed = self._encoder.encode([query_text]).tolist()
            where = {"topic": topic_filter} if topic_filter else None
            results = self._collection.query(
                query_embeddings=embed,
                n_results=min(top_k, max(1, self._collection.count())),
                where=where,
                include=["documents", "metadatas", "distances"],
            )
            docs = []
            for i, text in enumerate(results["documents"][0]):
                meta  = results["metadatas"][0][i]
                dist  = results["distances"][0][i]
                score = max(0.0, 1.0 - dist)          # cosine → similarity
                docs.append(SourceDocument(
                    content=text,
                    url=meta.get("url", ""),
                    title=meta.get("title", ""),
                    source_type=meta.get("source_type", ""),
                    topic=meta.get("topic", ""),
                    therapy_dimension=meta.get("therapy_dimension", ""),
                    published_date=meta.get("published_date", ""),
                    relevance_score=score,
                ))
            return docs
        except Exception as exc:
            log.error(f"ChromaDB query error: {exc}")
            return []

    def count(self) -> int:
        return self._collection.count() if self._available else 0


# ─── Obsidian vault writer ────────────────────────────────────────────────────

class ObsidianMemory:
    """
    Writes Q&A sessions as Markdown files into an Obsidian-compatible vault.
    Each file includes YAML frontmatter, full answer, citations, and tags.
    Previous notes are read back as context for the current session.
    """

    def __init__(self, vault_path: Optional[Path] = None):
        self.vault = Path(vault_path or settings.obsidian_vault_dir)
        self.vault.mkdir(parents=True, exist_ok=True)
        # Sub-folders by topic
        for topic in HealthTopic:
            (self.vault / topic.value.replace(" ", "_")).mkdir(exist_ok=True)

    # ── Save ──────────────────────────────────────────────────────────────────
    def save(self, query: str, response: AgentResponse) -> Path:
        """Persist an answer as a Markdown note. Returns the file path."""
        slug = re.sub(r"[^\w\s-]", "", query.lower())
        slug = re.sub(r"\s+", "-", slug)[:60]
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ts}_{slug}.md"
        folder   = self.vault / response.topic.value.replace(" ", "_")
        filepath = folder / filename

        tags = [
            response.topic.value.replace(" ", "_"),
            "health_rag",
        ] + [k.replace(" / ", "_").replace(" ", "_").lower()
             for k in response.therapy_sections.keys()]

        citations_md = "\n".join(
            f"{i+1}. {c}" for i, c in enumerate(response.citations)
        )

        note = f"""---
title: "{query}"
date: "{datetime.now().isoformat()}"
topic: "{response.topic.value}"
tags: [{", ".join(tags)}]
elapsed_seconds: {response.elapsed_seconds:.1f}
---

# {query}

{response.answer}

"""
        for dim, content in response.therapy_sections.items():
            if content.strip():
                note += f"## {dim}\n\n{content}\n\n"

        if response.youtube_links:
            note += "## Video Resources\n\n"
            note += "\n".join(f"- {lnk}" for lnk in response.youtube_links)
            note += "\n\n"

        if response.citations:
            note += f"## Sources\n\n{citations_md}\n\n"

        note += f"> ⚠️ {response.safety_disclaimer}\n"

        filepath.write_text(note, encoding="utf-8")
        log.info(f"Obsidian note saved: {filepath}")
        return filepath

    # ── Recall ────────────────────────────────────────────────────────────────
    def recall(
        self,
        topic: HealthTopic,
        max_notes: int = 5,
        keyword: Optional[str] = None,
    ) -> str:
        """
        Return recent notes for a topic as context text.
        Used to prime the agent with previously gathered knowledge.
        """
        folder = self.vault / topic.value.replace(" ", "_")
        if not folder.exists():
            return ""

        notes = sorted(folder.glob("*.md"), reverse=True)[:max_notes * 2]
        selected = []
        for note_path in notes:
            text = note_path.read_text(encoding="utf-8")
            if keyword and keyword.lower() not in text.lower():
                continue
            # Strip frontmatter for brevity
            body = re.sub(r"^---.*?---\n", "", text, flags=re.DOTALL)
            selected.append(body[:800])   # first 800 chars per note
            if len(selected) >= max_notes:
                break

        if not selected:
            return ""
        header = f"=== Prior knowledge from Obsidian vault (topic: {topic.value}) ===\n"
        return header + "\n\n---\n\n".join(selected)

    def list_notes(self, topic: Optional[HealthTopic] = None) -> list[Path]:
        """List all saved notes, optionally filtered by topic."""
        if topic:
            folder = self.vault / topic.value.replace(" ", "_")
            return sorted(folder.glob("*.md"), reverse=True)
        return sorted(self.vault.rglob("*.md"), reverse=True)


# ─── Convenience re-ranker ────────────────────────────────────────────────────

def rerank(
    docs: list[SourceDocument],
    query: str,
    top_k: int = 6,
) -> list[SourceDocument]:
    """
    Simple lexical + score re-ranker (no extra dependencies).
    Boosts:
      - documents from trusted domains
      - documents whose title/content overlaps query terms
      - documents with an assigned therapy dimension
    """
    query_tokens = set(re.findall(r"\w+", query.lower()))
    trusted      = settings.trusted_domains

    def _boost(doc: SourceDocument) -> float:
        base  = doc.relevance_score
        domain = ""
        try:
            from urllib.parse import urlparse
            domain = urlparse(doc.url).netloc.lstrip("www.")
        except Exception:
            pass
        domain_boost = 0.25 if any(domain.endswith(td) for td in trusted) else 0.0
        token_overlap = len(
            query_tokens & set(re.findall(r"\w+", (doc.title + " " + doc.content).lower()))
        ) / max(len(query_tokens), 1)
        dim_boost = 0.1 if doc.therapy_dimension else 0.0
        return base + domain_boost + token_overlap * 0.15 + dim_boost

    ranked = sorted(docs, key=_boost, reverse=True)

    # Deduplicate by URL (keep highest-scoring chunk per URL)
    seen: dict[str, SourceDocument] = {}
    for doc in ranked:
        if doc.url not in seen:
            seen[doc.url] = doc

    return list(seen.values())[:top_k]
