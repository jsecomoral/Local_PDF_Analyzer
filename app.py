import fitz  # PyMuPDF
import ollama
import sys
import os
import re
import pickle
import argparse
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.padding import Padding
from rich.text import Text

# --- UTILITY COMPONENTS ---

class Colors:
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def clean_text_content(text):
    """Sanitizes output by removing non-ASCII characters (emojis/symbols)"""
    text = text.encode('ascii', 'ignore').decode('ascii')
    return text.strip()

def extract_content_strict(pdf_path):
    """Extracts text using Pickle cache and block-sorting logic"""
    pickle_path = f"{pdf_path}.pkl"
    if os.path.exists(pickle_path):
        console.print(f"[bold green]✔ Loading document from cache...[/bold green]")
        with open(pickle_path, 'rb') as f:
            return pickle.load(f)
    try:
        doc = fitz.open(pdf_path)
        full_content = []
        for page in doc:
            blocks = page.get_text("blocks", sort=True)
            for b in blocks:
                if b[6] == 0: full_content.append(b[4])
        text = "\n".join(full_content)
        processed_text = text.encode('ascii', 'ignore').decode('ascii')
        with open(pickle_path, 'wb') as f:
            pickle.dump(processed_text, f)
        return processed_text
    except Exception as e:
        print(f"{Colors.FAIL}Extraction Error: {e}{Colors.ENDC}")
        return None

# --- EXPERT ENGINE LOGIC ---

# console = Console(width=100)   ## modify this line if you want larger content per line or auto-console text adjustment
console = Console()

def remove_formatting_tags(text):
    """Removes Rich markup tags for clean Markdown file export"""
    return re.sub(r'\[/?(?:red|green|white|blue|yellow|cyan|bold|u|italic)\]', '', text)

def export_to_markdown(content, filename="summary.md"):
    """Saves the expert analysis to a professional .md file"""
    clean_content = remove_formatting_tags(content)
    header = f"# EXPERT ANALYSIS REPORT\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(header + clean_content)
        return True
    except Exception as e:
        return False

def get_chat_response(messages, detail_level=5):
    """Communicates with Ollama API"""
    try:
        with console.status("[bold green]Senior Expert Panel processing..."):
            response = ollama.chat(
                model="llama3",
                messages=messages,
                options={"temperature": 0.2, "num_ctx": 16384}
            )
            return clean_text_content(response['message']['content'])
    except Exception as e:
        return f"[red]Error: {e}[/red]"

def start_interactive_session(pdf_text, detail_level):
    """Interactive loop with conversation history"""
    console.print("\n" + "─" * 60)
    console.print("[bold cyan]INTERACTIVE SESSION ACTIVE[/bold cyan]")
    
    system_msg = {
        'role': 'system', 
        'content': f"You are a Senior Expert. Use context: {pdf_text}. No emojis. No symbols."
    }
    chat_history = [system_msg]
    
    while True:
        query = console.input("\n[bold yellow]Ask the Expert: [/bold yellow]")
        if query.lower() in ['exit', 'quit']: break
        if query.lower() == 'clear':
            chat_history = [system_msg]
            continue
        
        chat_history.append({'role': 'user', 'content': query})
        answer = get_chat_response(chat_history, detail_level)
        chat_history.append({'role': 'assistant', 'content': answer})
        console.print(Padding(Text.from_markup(f"\n[blue]EXPERT INSIGHT:[/blue]\n{answer}"), (1, 3, 1, 3)))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--detail", type=int, default=5)
    args = parser.parse_args()

    text = extract_content_strict(args.pdf)
    if not text: return

    # REINFORCED PROMPT: Mandatory tags for EVERY word
    master_prompt = f"""
    You are a Senior Expert Analyzer. 
    IMPORTANT: You must use Rich Markup tags for EVERY section.
    DO NOT use asterisks (*) or any other symbols.

    REQUIRED STRUCTURE:
    1. Start with: [bold u yellow]PHASE 1: CLASSIFICATION.[/bold u yellow]
       Then, write all content for this phase wrapped in [yellow]...[/yellow] tags.

    2. Then: [bold u green]PHASE 2: HIGHLIGHTS[/bold u green]
       Then, write all content for this phase wrapped in [green]...[/green] tags.

    3. Then: [bold u red]PHASE 3: TOP 10 CRITICAL INSIGHTS[/bold u red]
       Then, write the 10 points wrapped in [red]...[/red] tags.

    4. Finally: [bold u blue]PHASE 4: EXECUTIVE SUMMARY[/bold u blue]
       Then, write the summary wrapped in [blue]...[/blue] tags.
    
    Detail level: {args.detail}/10.
    """

    console.print(Panel.fit(f"Document: [cyan]{args.pdf}[/cyan]"))

    initial_msg = [
        {'role': 'system', 'content': f"Context: {text}"},
        {'role': 'user', 'content': master_prompt}
    ]
    
    report = get_chat_response(initial_msg, args.detail)
    
    # We use Text.from_markup to ensure colors are rendered
    console.print("\n" + " " * 12 + "[bold u]INITIAL EXPERT REPORT[/bold u]")
    console.print(Padding(Text.from_markup(report), (1, 3, 1, 3)))

    export_to_markdown(report)
    start_interactive_session(text, args.detail)

if __name__ == "__main__":
    main()
