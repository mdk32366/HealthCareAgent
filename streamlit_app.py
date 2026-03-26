#!/usr/bin/env python3
"""
Healthcare RAG Agent — Streamlit Web App

A web-based interface for the Healthcare RAG Agent.
Users can ask health questions and get comprehensive answers with citations.

Run with:
    streamlit run streamlit_app.py
"""
import streamlit as st
import logging
from pathlib import Path
from datetime import datetime
import json

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger(__name__)

# Must set page config before any other Streamlit commands
st.set_page_config(
    page_title="Healthcare RAG Agent",
    page_icon="⚕️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .therapy-section {
        border-left: 4px solid #0066cc;
        padding-left: 12px;
        margin: 12px 0;
    }
    .citation {
        background-color: #f0f2f6;
        padding: 8px 12px;
        border-radius: 4px;
        margin: 4px 0;
        font-size: 0.9em;
    }
    .video-link {
        background-color: #ffe6e6;
        padding: 8px 12px;
        border-radius: 4px;
        margin: 4px 0;
    }
    .safety-disclaimer {
        background-color: #fff3cd;
        border-left: 4px solid #ff9800;
        padding: 12px;
        border-radius: 4px;
        margin: 16px 0;
    }
    .response-container {
        border: 1px solid #ddd;
        padding: 16px;
        border-radius: 8px;
        margin: 16px 0;
        background-color: #fafafa;
    }
    .question-bubble {
        background-color: #e3f2fd;
        padding: 12px;
        border-radius: 8px;
        margin: 8px 0;
        border-left: 4px solid #2196f3;
    }
    </style>
""", unsafe_allow_html=True)


def _validate_config() -> bool:
    """Check that configuration is properly set up."""
    from config.settings import settings
    
    if not settings.anthropic_api_key:
        return False
    return True


def _get_agent():
    """Initialize the healthcare RAG agent."""
    from agent.orchestrator import HealthcareRAGAgent
    return HealthcareRAGAgent()


def _format_therapy_section(dimension: str, content: str) -> None:
    """Display a therapy dimension section with formatted content."""
    st.markdown(f"### {dimension}", unsafe_allow_html=True)
    st.markdown(content)


def _display_citations(citations: list[str]) -> None:
    """Display citations in a formatted manner."""
    if not citations:
        return
    
    st.markdown("### 📚 Sources & Citations")
    for i, citation in enumerate(citations, 1):
        st.markdown(f'<div class="citation">[{i}] {citation}</div>', 
                   unsafe_allow_html=True)


def _display_videos(youtube_links: list[str]) -> None:
    """Display YouTube video links."""
    if not youtube_links:
        return
    
    st.markdown("### 🎬 Video Resources")
    for link in youtube_links:
        st.markdown(
            f'<div class="video-link"><a href="{link}" target="_blank">▶️ {link}</a></div>',
            unsafe_allow_html=True
        )


def _display_response(response) -> None:
    """Display a complete agent response."""
    with st.container():
        st.markdown('<div class="response-container">', unsafe_allow_html=True)
        
        # Main answer
        st.markdown("## Answer")
        st.markdown(response.answer)
        
        # Therapy dimensions
        if response.therapy_sections:
            st.markdown("## Treatment Dimensions")
            
            # Create columns for therapy dimensions
            cols = st.columns(2)
            for i, (dimension, content) in enumerate(response.therapy_sections.items()):
                with cols[i % 2]:
                    _format_therapy_section(dimension, content)
        
        # Videos
        if response.youtube_links:
            _display_videos(response.youtube_links)
        
        # Citations
        if response.citations:
            _display_citations(response.citations)
        
        # Safety disclaimer
        if response.safety_disclaimer:
            st.markdown(
                f'<div class="safety-disclaimer"><strong>⚠️  Medical Disclaimer:</strong><br/>{response.safety_disclaimer}</div>',
                unsafe_allow_html=True
            )
        
        # Performance metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Response Time", f"{response.elapsed_seconds:.1f}s")
        with col2:
            st.metric("Memory Note", response.memory_note)
        
        st.markdown('</div>', unsafe_allow_html=True)


def _display_conversation_history() -> None:
    """Display conversation history as a sidebar."""
    if "messages" in st.session_state and st.session_state.messages:
        st.sidebar.markdown("### 📜 Conversation History")
        
        for msg in st.session_state.messages[-10:]:  # Show last 10
            with st.sidebar.expander(msg["question"][:50] + "..."):
                st.markdown(msg["question"])
                if "timestamp" in msg:
                    st.caption(f"Asked: {msg['timestamp']}")


def _get_saved_notes() -> list[str]:
    """Get list of saved notes from Obsidian vault."""
    try:
        from memory.memory_manager import ObsidianMemory
        obsidian = ObsidianMemory()
        notes = obsidian.list_notes()
        return [str(n) for n in notes]
    except Exception as e:
        log.error(f"Error loading notes: {e}")
        return []


def _display_notes_browser() -> None:
    """Display a browser for saved notes."""
    from memory.memory_manager import ObsidianMemory
    from agent.models import HealthTopic
    
    st.markdown("## 📚 Saved Notes")
    
    # Topic filter
    topic_options = ["All"] + [t.value for t in HealthTopic]
    selected_topic = st.selectbox("Filter by topic:", topic_options)
    
    try:
        obsidian = ObsidianMemory()
        topic_enum = None
        if selected_topic != "All":
            topic_enum = HealthTopic(selected_topic)
        
        notes = obsidian.list_notes(topic_enum)
        
        if not notes:
            st.info("No notes found.")
            return
        
        # Display notes in a table format
        st.markdown(f"Found **{len(notes)}** notes:")
        
        for note_path in notes[:50]:  # Limit to 50 for performance
            try:
                with open(note_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract title and preview
                lines = content.split('\n')
                title = note_path.stem
                preview = '\n'.join(lines[:5])
                
                with st.expander(f"📄 {title}"):
                    st.markdown(preview)
                    st.caption(f"File: {note_path.name}")
            except Exception as e:
                st.warning(f"Could not read {note_path.name}: {e}")
    
    except Exception as e:
        st.error(f"Error browsing notes: {e}")


def main():
    """Main Streamlit application."""
    
    # Sidebar configuration
    with st.sidebar:
        st.markdown("# ⚙️ Configuration")
        
        # Check configuration
        if not _validate_config():
            st.error(
                "❌ Configuration incomplete. Please ensure API keys are set up.\n\n"
                "See SECURITY.md or run `python verify_config.py` for setup instructions."
            )
            st.stop()
        
        st.success("✅ Configuration valid")
        
        # Verbose logging toggle
        verbose = st.checkbox("Verbose logging", value=False)
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        st.markdown("---")
        
        # Display conversation history
        _display_conversation_history()
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown(
            """
            Healthcare RAG Agent provides comprehensive,
            multi-dimensional answers to health questions
            with proper medical disclaimers and citations.
            
            **Topics:**
            - Vaccines
            - Cancer
            - Hemophilia
            - Weight Control
            - Diabetes
            """
        )
    
    # Main content
    st.markdown(
        """
        # ⚕️ Healthcare RAG Agent
        
        Ask comprehensive health questions and get answers covering all treatment dimensions:
        FDA-approved therapies, homeopathic/naturopathic options, supplements, and surgical procedures.
        """
    )
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["❓ Ask Question", "📚 Saved Notes", "ℹ️ About"])
    
    # Tab 1: Ask Question
    with tab1:
        st.markdown("## Ask a Health Question")
        
        # Question input
        question = st.text_input(
            "Your question:",
            placeholder="e.g., What are all treatment options for Type 2 diabetes?",
            label_visibility="collapsed"
        )
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            submit = st.button("🔍 Search", use_container_width=True)
        
        with col2:
            clear_chat = st.button("🗑️ Clear Chat", use_container_width=True)
        
        with col3:
            example = st.button("📋 Example", use_container_width=True)
        
        if example:
            question = "What are all treatment options for Type 2 diabetes?"
            st.session_state.example_question = question
        
        if clear_chat:
            st.session_state.messages = []
            st.rerun()
        
        # Handle submitted question
        if submit and question:
            # Show thinking/loading state
            with st.spinner("🔍 Researching your question..."):
                try:
                    agent = _get_agent()
                    response = agent.ask(question, verbose=verbose)
                    
                    # Add to conversation history
                    st.session_state.messages.append({
                        "question": question,
                        "response": response,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                    
                    # Display the response
                    _display_response(response)
                
                except Exception as e:
                    st.error(f"❌ Error processing question: {str(e)}")
                    log.exception("Error in agent.ask()")
        
        # Display previous responses in this session
        if st.session_state.messages:
            st.markdown("---")
            st.markdown("## Session History")
            
            for msg in reversed(st.session_state.messages):
                with st.expander(f"Q: {msg['question'][:60]}..."):
                    st.markdown(f"**Asked:** {msg['timestamp']}")
                    st.markdown(f"**Question:** {msg['question']}")
                    st.markdown("---")
                    _display_response(msg['response'])
    
    # Tab 2: Saved Notes
    with tab2:
        _display_notes_browser()
    
    # Tab 3: About
    with tab3:
        st.markdown(
            """
            ## About Healthcare RAG Agent
            
            This agent provides comprehensive health information by combining:
            
            - **AI-Powered Research:** Uses Claude to synthesize information
            - **Web Search:** Searches trusted medical sources (NIH, CDC, Mayo Clinic, etc.)
            - **YouTube Videos:** Finds educational health videos with transcripts
            - **Vector Memory:** Recalls previously saved information
            - **Obsidian Vault:** Maintains organized markdown notes
            
            ### Supported Health Topics
            - **Vaccines** - Immunization information and safety
            - **Cancer** - Treatment options and management strategies
            - **Hemophilia** - Factor therapy and bleeding disorder management
            - **Weight Control** - Dietary and medical weight management
            - **Diabetes** - Type 1, Type 2, and gestational diabetes management
            
            ### Treatment Dimensions
            Every answer covers:
            1. **FDA-approved / clinical** - Prescription medications and procedures
            2. **Homeopathic / naturopathic** - Traditional and alternative approaches
            3. **Supplementation** - Vitamins, minerals, and over-the-counter supplements
            4. **Surgical / procedural** - Surgical interventions and medical procedures
            
            ### Important Disclaimer
            This tool provides **educational information only**. It does not constitute medical advice.
            Always consult a qualified healthcare professional before starting, changing, or stopping any treatment.
            
            ### Data Privacy
            - Questions are not logged or stored externally
            - Answers are saved locally in your Obsidian vault and vector store
            - All processing happens on your machine or your API keys
            
            ### Getting Started
            1. Configure your API keys (see SECURITY.md)
            2. Ask a health question
            3. Review the comprehensive answer with citations
            4. Save important information to your notes
            
            ---
            
            For more information, visit the project GitHub repository.
            """
        )


if __name__ == "__main__":
    main()
