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
| **Web interface** | Streamlit app for easy browser-based access |
| **CLI tool** | Powerful command-line interface for automation |

---

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Choose Your Interface](#choose-your-interface-cli-or-web)
- [Quick Start](#quick-start)
- [Advanced: Memory & Notes](#advanced-memory--notes)
- [Architecture](#architecture)
- [Documentation Guide](#documentation-guide)

---

## Installation

### Step 1: Clone & Setup Environment

```bash
# 1. Clone the repository
git clone https://github.com/mdk32366/HealthCareAgent.git
cd HealthCareAgent/health_rag_agent

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure API Keys

**Choose Method A (Recommended) or Method B below:**

#### Method A: Using `config.json` (Production-Recommended)

```bash
# Copy the template
cp config.example.json config.json

# Edit config.json with your API keys
# Windows: notepad config.json
# macOS/Linux: nano config.json
```

Edit the file and add your keys:
```json
{
  "api_keys": {
    "anthropic_api_key": "sk-ant-your-actual-key",
    "tavily_api_key": "tvly-your-actual-key"
  },
  ...
}
```

#### Method B: Using `.env` File (Development)

```bash
# Copy the template
cp .env.example .env

# Edit .env with your API keys
# Windows: notepad .env
# macOS/Linux: nano .env
```

Add your keys:
```bash
ANTHROPIC_API_KEY=sk-ant-your-actual-key
TAVILY_API_KEY=tvly-your-actual-key
```

### Step 3: Verify Configuration

```bash
python verify_config.py
```

Expected output:
```
✅ Configuration is valid! Ready to run the application.
```

**If verification fails:**
- See [SECURITY.md](SECURITY.md) for detailed setup help
- Ensure ANTHROPIC_API_KEY is not the placeholder value

---

## Configuration

**Priority order** (first match wins):

1. **`config.json`** ← Primary (production recommended)
2. **`.env` file** ← Fallback (development)
3. **System environment variables** ← For CI/CD
4. **Built-in defaults** ← Final fallback

**Key Details:**

| Setting | Source | Default | Notes |
|---------|--------|---------|-------|
| `ANTHROPIC_API_KEY` | config.json or .env | — | **Required** (get at https://console.anthropic.com) |
| `TAVILY_API_KEY` | config.json or .env | — | Recommended (free tier at https://tavily.com) |
| `CHROMA_PERSIST_DIR` | config.json or env | `./data/chroma_db` | Vector store location |
| `OBSIDIAN_VAULT_DIR` | config.json or env | `./data/obsidian_vault` | Notes folder |

> **Security Note:** `config.json` and `.env` are in `.gitignore` and will never be committed to version control.

---

## Choose Your Interface: CLI or Web

You have **two ways** to use Healthcare RAG Agent:

### 🌐 Web Interface (Streamlit) — Recommended for Most Users

**Best for:**
- Non-technical users
- Beautiful formatting & conversation history
- Sharing with others
- Team collaboration

**To start:**
```bash
streamlit run streamlit_app.py
```

**Opens at:** http://localhost:8501

**Features:**
- 📝 Simple text input for questions
- 💬 Conversation history sidebar
- 📚 Browse saved notes by topic
- 🎬 Clickable video recommendations
- 📖 Formatted citations & sources
- 🌙 Dark mode support

**Or use the interactive launcher:**
```bash
python launcher.py
# Select option 1 for Streamlit
```

### 💻 CLI Interface — Best for Automation & Scripting

**Best for:**
- Batch processing
- Scripting & automation
- Integration with other tools
- Lightweight & fast

**To start:**
```bash
python main.py ask "Your health question"
```

**Or use the interactive launcher:**
```bash
python launcher.py
# Select option 2 for CLI
```

---

## Quick Start

### Quick Start: Web Interface (3 steps)

```bash
# 1. Start the app
streamlit run streamlit_app.py

# 2. Open your browser
# Automatically opens at http://localhost:8501

# 3. Ask a question
# Type your question in the text input and click Search
```

### Quick Start: CLI Interface (1 command)

```bash
# Ask a question directly
python main.py ask "What are all treatment options for Type 2 diabetes?"
```

### Examples for Both Modes

**Example 1: Treatment options**
```bash
# CLI
python main.py ask "What are all treatment options for Type 2 diabetes?"

# Web: Type in the input field, click Search
```

**Example 2: Specific therapy dimension**
```bash
# CLI
python main.py ask "Natural supplements for diabetes management"

# Web: Type the question, get formatted answers by therapy dimension
```

**Example 3: Verbose mode (CLI only - see tool calls)**
```bash
python main.py ask "hemophilia factor replacement therapy" --verbose
```

**Example 4: JSON output (CLI only - for scripting)**
```bash
python main.py ask "cancer immunotherapy" --json
```

### Quick Examples to Try

```bash
# FDA-approved treatments
"What are FDA-approved treatments for breast cancer?"

# Complementary approaches
"Natural and alternative treatments for anxiety"

# Vaccine information
"HPV vaccine safety and effectiveness evidence"

# Weight management
"Prescription medications vs. supplements for weight loss"

# Disease management
"Diabetes: insulin vs. oral medications vs. supplements"
```

---

## Advanced: Memory & Notes

### View & Manage Saved Notes

```bash
# List all saved notes
python main.py notes

# Filter by topic
python main.py notes --topic diabetes
python main.py notes --topic cancer

# Show memory statistics
python main.py stats
```

### Ingest Local Documents

```bash
# Add a research paper to your knowledge base
python main.py ingest /path/to/research_paper.txt \
  --topic cancer \
  --url https://pubmed.example.com/123 \
  --title "My Research Paper"
```

### Obsidian Integration

1. Open Obsidian app → `File` → `Open Folder as Vault`
2. Select `./data/obsidian_vault`
3. Auto-tagged by topic and therapy dimension
4. Use graph view to explore knowledge connections

---

## Programmatic Use (Python)

```python
from agent.orchestrator import HealthcareRAGAgent

agent = HealthcareRAGAgent()
response = agent.ask("What supplements help with blood sugar control?")

# Access response components
print(response.answer)                    # Main answer text
print(response.citations)                 # List of sources
print(response.youtube_links)             # List of video links
print(response.therapy_sections)          # Dict of dimension → content
print(f"{response.elapsed_seconds:.1f}s") # Response time
```

---

## Documentation Guide

| Document | Purpose | For Whom |
|----------|---------|----------|
| **README.md** | Overview, setup, quick start | Everyone (you're reading it!) |
| **SECURITY.md** | API key setup, credential management | Initial setup, security concerns |
| **STREAMLIT.md** | Web interface detailed guide | Web users, deployment |
| **launcher.py** | Interactive menu system | Users who want an easy launcher |
| **verify_config.py** | Configuration validation | Troubleshooting setup issues |

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

## ⚠️ Medical Disclaimer

This tool provides educational information only. It does not constitute
medical advice. Always consult a qualified healthcare professional before
starting, changing, or stopping any treatment.

Homeopathic, supplemental, and alternative therapy information is presented
for completeness; evidence quality varies widely. The agent reports this
evidence as found — it does not endorse any treatment.
