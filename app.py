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

console = Console()

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

def get_chat_response(messages):
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

def detect_language(text):
    """Asks the model to detect the language of the provided text"""
    prompt = f"Identify the language of the following text and reply ONLY with the language name (e.g., English, Spanish, French). Text: {text[:1000]}"
    msg = [{'role': 'user', 'content': prompt}]
    return get_chat_response(msg)

def start_interactive_session(pdf_text, output_lang):
    """Interactive loop with conversation history"""
    console.print("\n" + "─" * 60)
    console.print("[bold cyan]INTERACTIVE SESSION ACTIVE[/bold cyan]")
    
    system_msg = {
        'role': 'system', 
        'content': f"You are a Senior Expert. Use context: {pdf_text}. Answer in {output_lang}. No emojis. No symbols."
    }
    chat_history = [system_msg]
    
    while True:
        query = console.input(f"\n[bold yellow]Ask the Expert ({output_lang}): [/bold yellow]")
        if query.lower() in ['exit', 'quit']: break
        if query.lower() == 'clear':
            chat_history = [system_msg]
            continue
        
        chat_history.append({'role': 'user', 'content': query})
        answer = get_chat_response(chat_history)
        chat_history.append({'role': 'assistant', 'content': answer})
        
        try:
            rendered_ans = Text.from_markup(f"\n[blue]EXPERT INSIGHT:[/blue]\n{answer}")
        except:
            rendered_ans = Text(f"\nEXPERT INSIGHT:\n{answer}")
            
        console.print(Padding(rendered_ans, (1, 3, 1, 3)))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--detail", type=int, default=5)
    parser.add_argument("--lang", type=str, default="Spanish", help="Language for the summary output")
    args = parser.parse_args()

    text = extract_content_strict(args.pdf)
    if not text: return

    # LANGUAGE DETECTION PHASE
    input_lang = detect_language(text)
    console.print(f"\n[bold white]SOURCE LANGUAGE detected:[/bold white] [bold cyan]{input_lang}[/bold cyan]")
    console.print(f"[bold white]OUTPUT LANGUAGE set to:[/bold white] [bold cyan]{args.lang}[/bold cyan]\n")

    # REINFORCED PROMPT: Language specific output
    master_prompt = f"""
    You are a Senior Expert Analyzer. 
    IMPORTANT: You must write the entire report in {args.lang}.
    You must use Rich Markup tags for EVERY section.
    DO NOT use asterisks (*) or any other symbols.

    STRICT MARKUP RULES:
    - To close a style, use the specific tag: [/bold], [/u], [/yellow], etc.
    - NEVER combine closing tags like [/u yellow]. Close them one by one.

    REQUIRED STRUCTURE:
    1. Start with: [bold yellow]PHASE 1: CLASSIFICATION.[/bold yellow]
       Then, write all content for this phase wrapped in [yellow]...[/yellow] tags.

    2. Then: [bold green]PHASE 2: HIGHLIGHTS[/bold green]
       Then, write all content for this phase wrapped in [green]...[/green] tags.

    3. Then: [bold red]PHASE 3: TOP 10 CRITICAL INSIGHTS[/bold red]
       Then, write the 10 points wrapped in [red]...[/red] tags.

    4. Finally: [bold blue]PHASE 4: EXECUTIVE SUMMARY[/bold blue]
       Then, write the summary wrapped in [blue]...[/blue] tags.
    
    Detail level: {args.detail}/10.
    """

    console.print(Panel.fit(f"Document: [cyan]{args.pdf}[/cyan]"))

    initial_msg = [
        {'role': 'system', 'content': f"Context: {text}"},
        {'role': 'user', 'content': master_prompt}
    ]
    
    report = get_chat_response(initial_msg)
    
    console.print("\n" + " " * 12 + f"[bold u]INITIAL EXPERT REPORT ({args.lang})[/bold u]")
    
    try:
        rendered_report = Text.from_markup(report)
    except Exception:
        rendered_report = Text(report)
        
    console.print(Padding(rendered_report, (1, 3, 1, 3)))

    export_to_markdown(report)
    start_interactive_session(text, args.lang)

if __name__ == "__main__":
    main()
