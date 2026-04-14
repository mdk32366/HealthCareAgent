"""
Healthcare RAG Agent — core orchestrator.

Uses Anthropic's tool-use API so Claude itself decides when to:
  • search the web
  • fetch YouTube transcripts
  • query the vector memory
  • recall Obsidian notes

After tool resolution, Claude synthesizes a fully-documented answer
covering all therapy dimensions.
"""
from __future__ import annotations
import json, logging, re, time
from typing import Any

import anthropic

from config.settings import settings
from agent.models import (
    AgentResponse, HealthTopic, RetrievedContext,
    SourceDocument, TherapyDimension,
)
from retrieval.web_search import deep_search
from retrieval.youtube_retrieval import search_youtube
from memory.memory_manager import VectorMemory, ObsidianMemory, rerank

log = logging.getLogger(__name__)

SAFETY_DISCLAIMER = (
    "This information is for educational purposes only and does not constitute "
    "medical advice. Always consult a qualified healthcare professional before "
    "starting, changing, or stopping any treatment. Homeopathic, supplemental, "
    "and alternative therapies should be discussed with your physician."
)

# ── Tool definitions ──────────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "web_search",
        "description": (
            "Search the web for current healthcare information from government, "
            "academic, and medical institutions. Use for FDA-approved treatments, "
            "clinical evidence, guidelines, and recent research."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query":     {"type": "string", "description": "Search query"},
                "topic":     {"type": "string",
                              "enum":  ["vaccines", "cancer", "hemophilia",
                                        "weight control", "diabetes", "general"],
                              "description": "Primary health topic"},
                "dimension": {"type": "string",
                              "enum":  ["FDA-approved / clinical",
                                        "Homeopathic / naturopathic",
                                        "Supplementation",
                                        "Surgical / procedural", "any"],
                              "description": "Therapy dimension to focus on"},
            },
            "required": ["query", "topic"],
        },
    },
    {
        "name": "youtube_search",
        "description": (
            "Search YouTube for educational health videos and extract transcripts. "
            "Good for patient-friendly explanations, procedure overviews, "
            "and expert interviews."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Video search query"},
                "topic": {"type": "string",
                          "enum": ["vaccines", "cancer", "hemophilia",
                                   "weight control", "diabetes", "general"]},
            },
            "required": ["query", "topic"],
        },
    },
    {
        "name": "recall_memory",
        "description": (
            "Retrieve previously saved Q&A notes and knowledge from the "
            "persistent Obsidian vault and ChromaDB vector store. "
            "Use this first to check if we already have relevant information."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Semantic search query"},
                "topic": {"type": "string",
                          "enum": ["vaccines", "cancer", "hemophilia",
                                   "weight control", "diabetes", "general"]},
            },
            "required": ["query", "topic"],
        },
    },
]

# ── Topic detection ───────────────────────────────────────────────────────────
_TOPIC_KEYWORDS: dict[HealthTopic, list[str]] = {
    HealthTopic.VACCINES:   ["vaccine", "vaccination", "immunization", "booster", "mmr", "covid"],
    HealthTopic.CANCER:     ["cancer", "tumor", "oncology", "chemotherapy", "carcinoma", "lymphoma"],
    HealthTopic.HEMOPHILIA: ["hemophilia", "haemophilia", "factor viii", "bleeding disorder", "clotting"],
    HealthTopic.WEIGHT:     ["weight", "obesity", "bmi", "diet", "bariatric", "metabolic"],
    HealthTopic.DIABETES:   ["diabetes", "insulin", "glucose", "a1c", "type 1", "type 2", "metformin"],
}

def detect_topic(query: str) -> HealthTopic:
    lower = query.lower()
    scores = {t: sum(1 for kw in kws if kw in lower)
              for t, kws in _TOPIC_KEYWORDS.items()}
    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    return best if scores[best] > 0 else HealthTopic.GENERAL


# ── Main agent class ──────────────────────────────────────────────────────────
class HealthcareRAGAgent:
    """
    Agentic loop:
      1. Detect topic
      2. Let Claude decide which tools to call (web search / YouTube / memory)
      3. Execute tools, gather SourceDocuments
      4. Re-rank context
      5. Claude synthesizes full answer covering all therapy dimensions
      6. Write result to memory (ChromaDB + Obsidian)
    """

    def __init__(self):
        self.client  = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.vector  = VectorMemory()
        self.obsidian = ObsidianMemory()
        log.info("HealthcareRAGAgent initialised")

    # ── Tool executor ─────────────────────────────────────────────────────────
    def _execute_tool(
        self,
        name: str,
        inputs: dict[str, Any],
        accumulated_docs: list[SourceDocument],
    ) -> str:
        """Run a single tool call, append docs, return string result for Claude."""
        topic_str = inputs.get("topic", "general")
        try:
            topic_enum = HealthTopic(topic_str)
        except ValueError:
            topic_enum = HealthTopic.GENERAL

        if name == "web_search":
            docs = deep_search(inputs["query"], topic_enum)
            accumulated_docs.extend(docs)
            return json.dumps({
                "status":    "ok",
                "num_chunks": len(docs),
                "previews": [
                    {"title": d.title, "url": d.url,
                     "snippet": d.content[:200], "dimension": d.therapy_dimension}
                    for d in docs[:6]
                ],
            })

        elif name == "youtube_search":
            docs = search_youtube(inputs["query"], topic_enum, max_results=5)
            accumulated_docs.extend(docs)
            return json.dumps({
                "status":    "ok",
                "num_videos": len(docs),
                "videos": [
                    {"title": d.title, "url": d.url, "snippet": d.content[:200]}
                    for d in docs
                ],
            })

        elif name == "recall_memory":
            # Vector store recall
            vector_docs = self.vector.query(inputs["query"], top_k=6, topic_filter=topic_str)
            accumulated_docs.extend(vector_docs)
            # Obsidian recall
            obsidian_text = self.obsidian.recall(topic_enum, keyword=inputs["query"])
            return json.dumps({
                "status":          "ok",
                "vector_hits":     len(vector_docs),
                "obsidian_excerpt": obsidian_text[:500] if obsidian_text else "",
                "previews": [
                    {"title": d.title, "url": d.url, "snippet": d.content[:150]}
                    for d in vector_docs[:4]
                ],
            })

        else:
            return json.dumps({"error": f"Unknown tool: {name}"})

    # ── Agentic loop ──────────────────────────────────────────────────────────
    def ask(self, query: str, verbose: bool = False) -> AgentResponse:
        t0    = time.time()
        topic = detect_topic(query)
        log.info(f"Query: {query!r} | Topic: {topic.value}")

        # Prior knowledge for context
        prior = self.obsidian.recall(topic, max_notes=3, keyword=query)

        system_prompt = f"""You are a comprehensive healthcare research assistant.
Your role is to answer health questions by gathering information from multiple
sources and presenting ALL therapeutic options fairly, including:
  • FDA-approved / clinical (drugs, clinical trials, evidence-based protocols)
  • Homeopathic / naturopathic (herbal, traditional, integrative medicine)
  • Supplementation (vitamins, minerals, nutraceuticals)
  • Surgical / procedural (operations, interventions, devices)

IMPORTANT RULES:
1. Call recall_memory FIRST to check existing knowledge.
2. Then call web_search with dimension-specific queries for each category you
   need to fill in. Use multiple searches if needed.
3. Call youtube_search to find educational videos for the user.
4. Cover EVERY therapy dimension even if one seems unconventional — present
   the evidence (or lack thereof) neutrally.
5. Every factual claim MUST cite a source using [SOURCE N] inline.
6. End with the standard safety disclaimer.
7. Format the final answer with clear sections for each therapy dimension.

Trusted sources to prefer: NIH, PubMed, CDC, FDA, WHO, Mayo Clinic,
Cleveland Clinic, NCI, NCCIH (for complementary medicine), Examine.com
(for supplements), Cochrane Library.

{f"PRIOR KNOWLEDGE FROM VAULT:{chr(10)}{prior}{chr(10)}" if prior else ""}
"""

        messages: list[dict] = [
            {"role": "user", "content": query}
        ]
        accumulated_docs: list[SourceDocument] = []

        # ── Agentic loop (max 10 rounds) ──────────────────────────────────────
        for _round in range(10):
            resp = self.client.messages.create(
                model=settings.model,
                max_tokens=settings.max_tokens,
                system=system_prompt,
                tools=TOOLS,
                messages=messages,
            )
            if verbose:
                log.debug(f"Round {_round}: stop_reason={resp.stop_reason}")

            # Append assistant turn
            messages.append({"role": "assistant", "content": resp.content})

            if resp.stop_reason == "end_turn":
                break

            if resp.stop_reason == "tool_use":
                tool_results = []
                for block in resp.content:
                    if block.type == "tool_use":
                        result_str = self._execute_tool(
                            block.name, block.input, accumulated_docs
                        )
                        tool_results.append({
                            "type":        "tool_result",
                            "tool_use_id": block.id,
                            "content":     result_str,
                        })
                if tool_results:
                    messages.append({"role": "user", "content": tool_results})
                continue

            break   # safety exit

        # ── Extract final text response ───────────────────────────────────────
        final_text = ""
        for block in resp.content:
            if hasattr(block, "text"):
                final_text += block.text

        # ── Re-rank accumulated documents ─────────────────────────────────────
        ranked_docs = rerank(accumulated_docs, query, top_k=settings.top_k_rerank)

        # ── Parse therapy sections from final text ────────────────────────────
        therapy_sections = _extract_therapy_sections(final_text)

        # ── Collect citations ─────────────────────────────────────────────────
        yt_links = [d.url for d in accumulated_docs if d.source_type == "youtube"]
        citations = list({d.to_citation() for d in ranked_docs if d.url})

        # ── Build response ────────────────────────────────────────────────────
        agent_resp = AgentResponse(
            answer=final_text,
            topic=topic,
            therapy_sections=therapy_sections,
            citations=citations,
            youtube_links=yt_links,
            safety_disclaimer=SAFETY_DISCLAIMER,
            elapsed_seconds=time.time() - t0,
        )

        # ── Write to memory ───────────────────────────────────────────────────
        n_upserted = self.vector.upsert(ranked_docs)
        note_path  = self.obsidian.save(query, agent_resp)
        agent_resp.memory_note = (
            f"Saved to Obsidian: {note_path.name} | "
            f"Upserted {n_upserted} chunks to ChromaDB"
        )
        log.info(agent_resp.memory_note)

        return agent_resp


# ── Helper: parse therapy dimension sections ──────────────────────────────────
def _extract_therapy_sections(text: str) -> dict[str, str]:
    """
    Pull out named therapy-dimension sections from the answer text.
    Returns a dict of dimension → content.
    """
    dims = settings.therapy_dimensions
    sections: dict[str, str] = {}
    # Try to find each dimension header
    for i, dim in enumerate(dims):
        # Flexible regex: matches markdown headers or bold/plain text
        pattern = rf"(?:#{1,3}|[\*_]{{0,2}})\s*{re.escape(dim)}\s*(?:[\*_]{{0,2}})?\s*:?\n(.*?)(?=(?:#{1,3}|[\*_]{{0,2}})\s*(?:{'|'.join(map(re.escape, dims))})|$)"
        m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if m and m.group(1) is not None:
            sections[dim] = m.group(1).strip()[:2000]
    return sections
