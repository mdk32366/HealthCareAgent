# Healthcare RAG Agent

A production-grade, **Pythonic agentic RAG system** for answering healthcare
questions across five topic domains using publicly available information,
with persistent memory via ChromaDB and an Obsidian Markdown vault.

---

## Features

| Capability | Details |
|---|---|
| **Agentic tool use** | Claude decides which tools to call (web search, YouTube, memory recall) |
| **RAG retrieval** | Tavily search + DuckDuckGo fallback + BeautifulSoup scraping |
| **YouTube transcripts** | yt-dlp search + youtube-transcript-api for video content |
| **Vector memory** | ChromaDB with sentence-transformers embeddings (local, no API key) |
| **Obsidian vault** | Human-readable Markdown notes per Q&A, organized by topic |
| **Therapy dimensions** | FDA/clinical · Homeopathic · Supplementation · Surgical |
| **Health topics** | Vaccines · Cancer · Hemophilia · Weight control · Diabetes |
| **Source citations** | Every factual claim linked to its source URL |
| **Safety layer** | Always-present medical disclaimer + hallucination guidance |

---

## Installation

```bash
# 1. Clone and enter
git clone https://github.com/your-org/health-rag-agent
cd health-rag-agent

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API keys
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY (required)
# Add TAVILY_API_KEY for best web search results (free tier at tavily.com)
```

---

## Quick Start

```bash
# Ask a question
python main.py ask "What are all treatment options for Type 2 diabetes?"

# More examples
python main.py ask "Hemophilia A factor replacement therapy options"
python main.py ask "Natural and medical treatments for weight loss"
python main.py ask "HPV vaccine safety and effectiveness evidence"
python main.py ask "Breast cancer treatment overview all options"

# Verbose mode (shows tool calls)
python main.py ask "diabetes supplements" --verbose

# JSON output for programmatic use
python main.py ask "cancer immunotherapy" --json
```

---

## Memory Commands

```bash
# List all saved notes
python main.py notes

# Filter by topic
python main.py notes --topic diabetes
python main.py notes --topic cancer

# Show memory statistics
python main.py stats

# Ingest a local document
python main.py ingest /path/to/research_paper.txt --topic cancer \
  --url https://pubmed.example.com/123 --title "My Research Paper"
```

---

## Architecture

```
health_rag_agent/
├── main.py                     ← CLI entry point (typer + rich)
├── config/
│   └── settings.py             ← Pydantic settings (env vars, constants)
├── agent/
│   ├── models.py               ← Shared data models (SourceDocument, AgentResponse…)
│   └── orchestrator.py         ← Core agent loop (tool use → synthesis)
├── retrieval/
│   ├── web_search.py           ← Tavily + DuckDuckGo + BeautifulSoup scraper
│   └── youtube_retrieval.py    ← yt-dlp + youtube-transcript-api
├── memory/
│   └── memory_manager.py       ← ChromaDB vector store + Obsidian vault writer
└── data/
    ├── chroma_db/              ← Persisted ChromaDB files (auto-created)
    └── obsidian_vault/         ← Markdown notes (open in Obsidian app)
        ├── vaccines/
        ├── cancer/
        ├── hemophilia/
        ├── weight_control/
        └── diabetes/
```

---

## Agent Flow

```
User question
     │
     ▼
Topic detection (keyword → enum)
     │
     ▼
Claude (tool-use loop, max 10 rounds)
     ├─ recall_memory   → ChromaDB + Obsidian prior knowledge
     ├─ web_search      → Tavily / DuckDuckGo + page scraping
     │    ├─ query for FDA/clinical evidence
     │    ├─ query for homeopathic / naturopathic options
     │    ├─ query for supplements
     │    └─ query for surgical options
     └─ youtube_search  → transcripts + video links
     │
     ▼
Re-rank & deduplicate (score boost: trusted domains, token overlap)
     │
     ▼
Claude synthesis (all therapy dimensions + inline citations)
     │
     ▼
Safety disclaimer appended
     │
     ├─── ChromaDB upsert (new chunks)
     ├─── Obsidian note saved (topic/YYYYMMDD_HHMMSS_slug.md)
     └─── AgentResponse returned to user
```

---

## Trusted Sources

The agent preferentially retrieves from:

**Government / regulatory**
- nih.gov, pubmed.ncbi.nlm.nih.gov, cdc.gov, fda.gov, who.int

**Cancer**
- cancer.gov (NCI), cancer.org (ACS)

**Medical institutions**
- mayoclinic.org, hopkinsmedicine.org, clevelandclinic.org

**Specialty**
- hemophilia.org, nhlbi.nih.gov (blood), diabetes.org, niddk.nih.gov

**Complementary / integrative**
- nccih.nih.gov (NIH complementary medicine)

**Supplements**
- examine.com

**Evidence synthesis**
- cochranelibrary.com

---

## Obsidian Integration

1. Open Obsidian → `File` → `Open Folder as Vault`
2. Select `./data/obsidian_vault`
3. Notes are auto-tagged by topic and therapy dimension
4. Use the graph view to explore knowledge connections over time

---

## Programmatic Use

```python
from agent.orchestrator import HealthcareRAGAgent

agent = HealthcareRAGAgent()
response = agent.ask("What supplements help with blood sugar control?")

print(response.answer)
print(response.citations)
print(response.youtube_links)
print(response.therapy_sections["Supplementation"])
```

---

## Configuration

All settings live in `config/settings.py` and can be overridden via `.env`:

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required |
| `TAVILY_API_KEY` | — | Recommended (free tier) |
| `CHROMA_PERSIST_DIR` | `./data/chroma_db` | Vector store location |
| `OBSIDIAN_VAULT_DIR` | `./data/obsidian_vault` | Notes location |

---

## ⚠️ Medical Disclaimer

This tool provides educational information only. It does not constitute
medical advice. Always consult a qualified healthcare professional before
starting, changing, or stopping any treatment.

Homeopathic, supplemental, and alternative therapy information is presented
for completeness; evidence quality varies widely. The agent reports this
evidence as found — it does not endorse any treatment.
