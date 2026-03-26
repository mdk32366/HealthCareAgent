# Streamlit Web Interface

The Healthcare RAG Agent now includes a **user-friendly web interface** built with Streamlit. This allows you to interact with the agent through a modern, intuitive web app instead of the command line.

## Quick Start

### 1. Install Streamlit

```bash
pip install -r requirements.txt
```

(Streamlit is now included in requirements.txt)

### 2. Verify Configuration

```bash
python verify_config.py
```

Ensure your API keys are properly configured.

### 3. Start the Web App

```bash
streamlit run streamlit_app.py
```

The app will automatically open in your browser at **http://localhost:8501**

## Features

### 🎯 Ask Questions

- Simple text input for health questions
- Real-time response streaming
- Automatic topic detection
- Verbose logging option

### 📚 Formatted Answers

Responses include:

- **Main Answer** — Comprehensive overview
- **Treatment Dimensions** — FDA-approved, Homeopathic, Supplements, Surgical
- **Video Resources** — Educational YouTube videos with transcripts
- **Sources & Citations** — Every claim linked to its source
- **Safety Disclaimer** — Always-present medical warnings
- **Performance Metrics** — Response time and memory usage

### 📜 Conversation History

- Sidebar shows recent questions (last 10)
- Click to expand and re-read previous answers
- Search and organize your queries

### 📚 Saved Notes Browser

- View all saved notes organized by topic
- Filter by health topic (vaccines, cancer, diabetes, etc.)
- Preview note content
- See when notes were created

### 🔧 Configuration Panel

- Sidebar configuration area
- Verify API keys are loaded
- Toggle verbose logging
- Quick configuration validation

## Usage Scenarios

### Scenario 1: Researching a Health Topic

1. Open the app: `streamlit run streamlit_app.py`
2. Ask: "What are all treatment options for thyroid cancer?"
3. Read comprehensive answer with all therapy dimensions
4. Click video links to watch educational content
5. View citations for further research

### Scenario 2: Comparing Treatment Options

1. Ask: "How do FDA-approved diabetes medications compare to supplements?"
2. Read separate sections for each therapy dimension
3. Reference citations for clinical evidence
4. Save important findings to Obsidian notes

### Scenario 3: Building a Knowledge Base

1. Ask multiple related questions
2. Use conversation history to review past research
3. Browse saved notes to see what's been learned
4. Ingest local documents via CLI for specific expertise

## Installation Options

### Option A: Using Streamlit Directly

```bash
# Simple way
streamlit run streamlit_app.py

# With custom config
streamlit run streamlit_app.py -- --logger.level=debug

# Headless (for remote servers)
streamlit run streamlit_app.py --server.headless true
```

### Option B: Using the Launcher Script

```bash
# Interactive menu to choose CLI or Web
python launcher.py

# Select option 1 for Streamlit
```

### Option C: Python Script

```python
#!/usr/bin/env python3
import subprocess
import sys

subprocess.run([
    sys.executable, "-m", "streamlit", 
    "run", "streamlit_app.py"
])
```

## Configuration

### Application Settings

The Streamlit app respects all configuration from:

1. `config.json` — Your production configuration
2. `.env` — Environment variables
3. Environment variables — System-wide settings

### Streamlit-Specific Config

For performance or customization, create `.streamlit/config.toml`:

```toml
[client]
showErrorDetails = true

[logger]
level = "info"

[theme]
primaryColor = "#2196f3"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"

[server]
port = 8501
headless = false
```

## Performance Tips

### Optimization

1. **First run slower** — Streamlit compiles on first execution
2. **Use caching** — Session state preserves conversation
3. **Limit history** — App shows last 10 messages in sidebar
4. **Vector store** — First queries slower, subsequent queries faster

### Troubleshooting Slow Responses

- Check internet connection (web search requires it)
- Verify API keys have proper rate limits
- Check system resources (CPU, RAM)
- See logs with `streamlit run streamlit_app.py --logger.level=debug`

## Deployment

### Local Network

```bash
# Make accessible from other machines on your network
streamlit run streamlit_app.py --server.address 0.0.0.0
```

Then access from another machine at: `http://your-ip:8501`

### Cloud Deployment

Streamlit Community Cloud supports free hosting:

```bash
# Deploy to Streamlit Cloud
streamlit deploy
```

See [Streamlit deployment docs](https://docs.streamlit.io/deploy/streamlit-community-cloud)

### Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

CMD ["streamlit", "run", "streamlit_app.py"]
```

Build and run:

```bash
docker build -t healthcare-rag .
docker run -p 8501:8501 -v $(pwd)/config.json:/app/config.json healthcare-rag
```

## Advanced Usage

### Session State for Multi-Step Workflows

The app maintains conversation history in `st.session_state`:

```python
# View conversation history
st.session_state.messages  # List of question/response pairs

# Clear history
st.session_state.messages = []
st.rerun()
```

### Extending the Interface

Modify `streamlit_app.py` to add:

- Custom sidebar widgets
- Additional tabs
- Data export functionality
- Integration with other systems

### Logging

Enable detailed logging:

```bash
streamlit run streamlit_app.py --logger.level=debug
```

View logs in the terminal where Streamlit runs.

## Security Considerations

### Credential Management

- **Never** paste API keys directly into the app
- Use `config.json` (protected in `.gitignore`)
- Use environment variables for CI/CD
- Rotate keys regularly via provider dashboards

### Data Privacy

- Questions are not logged externally
- Responses saved locally in Obsidian vault
- No data sent to third parties (except APIs)
- All processing on your machine/your credentials

### Network Considerations

- App runs on `localhost:8501` by default
- To access remotely, use authentication or VPN
- Consider SSL/TLS for deployment
- Review Streamlit security best practices

## Troubleshooting

### "Cannot import streamlit"

```bash
pip install streamlit>=1.28.0
# or
pip install -r requirements.txt
```

### "API key not found"

```bash
python verify_config.py
# Follow the instructions to set up config.json
```

### "Connection error" or "Web search failed"

- Check internet connection
- Verify TAVILY_API_KEY is set
- Check Tavily account rate limits

### App is slow

- First load takes time (Python + dependencies)
- Subsequent interactions faster
- Check browser console (F12) for errors
- Try `--logger.level=debug` for diagnostics

### Port 8501 already in use

```bash
# Use different port
streamlit run streamlit_app.py --server.port 8502
```

## Keyboard Shortcuts

- `R` — Rerun app
- `C` — Clear cache
- `t` — Toggle dark mode
- `S` — Show settings

(In Settings → Keyboard shortcuts for full list)

## Comparing CLI vs Web

| Feature | CLI | Web |
|---------|-----|-----|
| Ease of use | Medium | Easy |
| Batch processing | ✅ Yes | ❌ No |
| Conversation history | 🔵 Manual | ✅ Automatic |
| Visual formatting | 🔵 ANSI colors | ✅ Rich HTML |
| Video links | 🔵 Text URLs | ✅ Clickable |
| Configuration | 🔵 Arguments | ✅ Sidebar |
| Automation/scripting | ✅ Yes | ❌ No |
| Mobile friendly | ❌ No | ✅ Yes |
| No dependencies | ❌ No | ✅ (Streamlit) |

**Recommendation:**
- **Use Web** if you're a regular user, want nice formatting, conversation history
- **Use CLI** if you're scripting, processing multiple questions, or prefer command-line tools

## FAQ

**Q: Can I use both CLI and Web at the same time?**
A: Yes! They share the same `config.json` and memory databases. Start one or both anytime.

**Q: How do I save an answer?**
A: Answers are automatically saved to your Obsidian vault. Use the "Saved Notes" tab to browse them.

**Q: Can I customize the appearance?**
A: Yes! Edit `.streamlit/config.toml` for theme colors, fonts, etc.

**Q: How do I host this for a team?**
A: See Deployment section above. Streamlit Cloud is easiest for free hosting.

**Q: Does Streamlit work offline?**
A: No, the agent requires web search. But previously saved notes are accessible offline.

---

For more help, see:
- [Streamlit documentation](https://docs.streamlit.io)
- [SECURITY.md](SECURITY.md) — API key setup
- [README.md](README.md) — General usage
- [launcher.py](launcher.py) — Interactive launcher
