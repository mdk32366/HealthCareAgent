#!/usr/bin/env python3
"""
Healthcare RAG Agent — Launcher

Simple script to help users choose between CLI and web interface.

Usage:
    python launcher.py
"""
import sys
import os
from pathlib import Path
import subprocess


def check_config():
    """Verify configuration is set up."""
    try:
        from config.settings import settings
        if not settings.anthropic_api_key:
            return False
        return True
    except Exception as e:
        print(f"Error checking config: {e}")
        return False


def run_verification():
    """Run the configuration verification script."""
    script = Path(__file__).parent / "verify_config.py"
    if script.exists():
        print("\nRunning configuration verification...\n")
        subprocess.run([sys.executable, str(script)])
    else:
        print("⚠️  verify_config.py not found")


def show_menu():
    """Display the main menu."""
    print("\n" + "=" * 70)
    print("Healthcare RAG Agent — Launcher")
    print("=" * 70)
    
    if not check_config():
        print("\n⚠️  Configuration not complete!")
        print("\nYou need to set up your API keys first.")
        print("\nOptions:")
        print("  1. Setup configuration")
        print("  2. Exit")
        
        choice = input("\nChoose an option (1-2): ").strip()
        
        if choice == "1":
            run_verification()
            print("\nPlease edit 'config.json' or '.env' with your API keys.")
            input("Press Enter to continue...")
            show_menu()
        else:
            sys.exit(0)
        return
    
    print("\n✅ Configuration is valid!\n")
    print("Choose an interface:\n")
    print("  1. 🌐 Web Interface (Streamlit) — Recommended for most users")
    print("  2. 💻 Command Line Interface (CLI) — For scripting and automation")
    print("  3. 🔧 Verify Configuration — Check setup")
    print("  4. 📖 Show Help — Usage examples")
    print("  5. ❌ Exit\n")
    
    choice = input("Enter your choice (1-5): ").strip()
    
    if choice == "1":
        run_streamlit()
    elif choice == "2":
        run_cli()
    elif choice == "3":
        run_verification()
        input("\nPress Enter to continue...")
        show_menu()
    elif choice == "4":
        show_help()
        input("\nPress Enter to continue...")
        show_menu()
    elif choice == "5":
        print("\nGoodbye! 👋\n")
        sys.exit(0)
    else:
        print("❌ Invalid choice. Please try again.")
        show_menu()


def run_streamlit():
    """Launch the Streamlit app."""
    print("\n🌐 Starting Streamlit web interface...\n")
    print("The app will open in your browser at http://localhost:8501")
    print("Press Ctrl+C to stop the server.\n")
    
    streamlit_app = Path(__file__).parent / "streamlit_app.py"
    
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(streamlit_app)],
            check=False
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
    except Exception as e:
        print(f"❌ Error starting Streamlit: {e}")
    
    input("\nPress Enter to return to menu...")
    show_menu()


def run_cli():
    """Launch the CLI interface."""
    print("\n💻 CLI Mode — Enter your command\n")
    print("Examples:")
    print('  ask "What are treatment options for Type 2 diabetes?"')
    print("  notes --topic diabetes")
    print("  help")
    print("  exit\n")
    
    while True:
        try:
            command = input(">>> ").strip()
            
            if not command:
                continue
            
            if command.lower() == "exit":
                break
            
            if command.lower() == "help":
                show_help()
                continue
            
            # Parse the command
            parts = command.split(maxsplit=1)
            if not parts:
                continue
            
            cmd = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            
            if cmd == "ask":
                if args:
                    question = args[0]
                    # Remove quotes if present
                    if question.startswith('"') and question.endswith('"'):
                        question = question[1:-1]
                    run_ask_command(question)
                else:
                    print("Usage: ask \"Your question\"")
            
            elif cmd == "notes":
                run_notes_command(args)
            
            else:
                print(f"Unknown command: {cmd}")
                print("Type 'help' for available commands.")
        
        except KeyboardInterrupt:
            print("\n")
            break
        except Exception as e:
            print(f"Error: {e}")
    
    print("\nReturning to main menu...\n")
    show_menu()


def run_ask_command(question: str):
    """Execute the ask command."""
    try:
        from agent.orchestrator import HealthcareRAGAgent
        
        print(f"\n🔍 Researching: {question}\n")
        agent = HealthcareRAGAgent()
        response = agent.ask(question)
        
        # Print response
        print(f"\n{'='*70}")
        print(f"Topic: {response.topic.value}")
        print(f"{'='*70}\n")
        
        print("Answer:")
        print(response.answer)
        
        if response.therapy_sections:
            print("\n" + "="*70)
            print("Treatment Dimensions:")
            print("="*70)
            for dimension, content in response.therapy_sections.items():
                print(f"\n{dimension}:")
                print(content)
        
        if response.youtube_links:
            print("\n" + "="*70)
            print("Video Resources:")
            print("="*70)
            for link in response.youtube_links:
                print(f"  • {link}")
        
        if response.citations:
            print("\n" + "="*70)
            print("Sources & Citations:")
            print("="*70)
            for i, citation in enumerate(response.citations, 1):
                print(f"  [{i}] {citation}")
        
        print(f"\n⚠️  {response.safety_disclaimer}")
        print(f"\n⏱️  Response time: {response.elapsed_seconds:.1f}s")
    
    except Exception as e:
        print(f"❌ Error: {e}")


def run_notes_command(args: list):
    """Execute the notes command."""
    try:
        from memory.memory_manager import ObsidianMemory
        from agent.models import HealthTopic
        
        topic = None
        if args and "--topic" in args[0]:
            topic_val = args[1] if len(args) > 1 else None
            if topic_val:
                try:
                    topic = HealthTopic(topic_val)
                except ValueError:
                    print(f"Unknown topic: {topic_val}")
                    return
        
        obsidian = ObsidianMemory()
        notes = obsidian.list_notes(topic)
        
        if not notes:
            print("No notes found.")
            return
        
        print(f"\nFound {len(notes)} note(s):\n")
        for i, note in enumerate(notes[:20], 1):
            print(f"  {i}. {note.name}")
    
    except Exception as e:
        print(f"❌ Error: {e}")


def show_help():
    """Display help information."""
    help_text = """
Healthcare RAG Agent — Help

INTERFACES:
  Web App (Streamlit):
    - Recommended for interactive use
    - Run: streamlit run streamlit_app.py
    - Browse at: http://localhost:8501

  CLI (Command Line):
    - Best for scripting and automation
    - Run: python main.py [command] [options]

COMMANDS:

  ask "question"
    Ask a health-related question
    Example: ask "What are treatment options for diabetes?"

  notes [--topic TOPIC]
    List saved notes (optionally filtered by topic)
    Topics: vaccines, cancer, hemophilia, weight control, diabetes
    Example: notes --topic diabetes

  ingest FILE [--topic TOPIC] [--url URL] [--title TITLE]
    Ingest a document into the knowledge base
    Example: ingest paper.txt --topic cancer --url https://example.com

CONFIGURATION:
  See SECURITY.md and REFACTORING_SUMMARY.md for setup instructions.

Quick start:
  1. cp config.example.json config.json
  2. Edit config.json with your API keys
  3. python launcher.py  (this script)

For more info, see README.md
"""
    print(help_text)


def main():
    """Main entry point."""
    try:
        # Check if already in the right directory
        if not Path("config.example.json").exists():
            print("Error: This script must be run from the project root directory")
            sys.exit(1)
        
        show_menu()
    
    except KeyboardInterrupt:
        print("\n\nGoodbye! 👋\n")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
