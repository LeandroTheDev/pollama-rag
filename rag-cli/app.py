#!/usr/bin/env python3
import sys
import httpx
from docs_cleanup import clean_txt
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style
from prompt_toolkit.output import create_output
from prompt_toolkit import print_formatted_text
import glob, os, termios, json, threading, time

API_URL = "http://127.0.0.1:8000"

style = Style.from_dict({
    "you": "ansiyellow bold",
    "rag": "ansigreen bold",
})

output = create_output()

BAR_WIDTH = 20
SPINNERS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

def animate_status(step, pct, stop_event):
    filled = round(pct / 100 * BAR_WIDTH)
    bar = "█" * filled + "░" * (BAR_WIDTH - filled)
    start = time.time()
    i = 0
    while not stop_event.is_set():
        elapsed = time.time() - start
        spinner = SPINNERS[i % len(SPINNERS)]
        sys.stdout.write(f"\r\033[2K\033[36m[{bar}] {pct:3d}%  {step}... {spinner} {elapsed:.1f}s\033[0m")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1

def clear_status():
    sys.stdout.write("\r\033[2K")
    sys.stdout.flush()

def stream_ask(question: str):
    fd = sys.stdin.fileno()
    is_tty = sys.stdin.isatty()
    if is_tty:
        old_attrs = termios.tcgetattr(fd)
        no_echo = termios.tcgetattr(fd)
        no_echo[3] &= ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, no_echo)

    stop_event = None
    anim_thread = None

    def start_animation(step, pct):
        nonlocal stop_event, anim_thread
        stop_animation()
        stop_event = threading.Event()
        anim_thread = threading.Thread(target=animate_status, args=(step, pct, stop_event), daemon=True)
        anim_thread.start()

    def stop_animation():
        nonlocal stop_event, anim_thread
        if stop_event:
            stop_event.set()
            anim_thread.join()
            stop_event = None
            anim_thread = None

    generating = False
    try:
        with httpx.Client(timeout=None) as client:
            with client.stream("POST", f"{API_URL}/ask/stream",
                               json={"question": question}) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line:
                        continue
                    ev = json.loads(line)
                    if ev["type"] == "status":
                        start_animation(ev["step"], ev["pct"])
                    elif ev["type"] == "token":
                        if not generating:
                            stop_animation()
                            clear_status()
                            print_formatted_text(FormattedText([("class:rag", "rag: ")]), style=style, end="")
                            generating = True
                        sys.stdout.write(ev["text"])
                        sys.stdout.flush()
                    elif ev["type"] == "done":
                        break
    finally:
        stop_animation()
        if is_tty:
            termios.tcsetattr(fd, termios.TCSANOW, old_attrs)
            termios.tcflush(fd, termios.TCIFLUSH)
    print()

def clean():
    base = "/app/documents"
    count = 0
    for file in glob.glob(os.path.join(base, "**/*.txt"), recursive=True):
        if not file.endswith('.kate-swp'):
            clean_txt(file)
            print(f"Cleaned: {file}")
            count += 1
    print(f"✓ {count} file(s) cleaned")

def ingest():
    with httpx.Client(timeout=None) as client:
        r = client.post(f"{API_URL}/ingest", json={})
        r.raise_for_status()
        data = r.json()
        print(f"✓ {data['ingested']} document(s) indexed")

def health():
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(f"{API_URL}/health")
            r.raise_for_status()
        return True
    except Exception:
        return False

def main():
    print("RAG CLI — type 'quit' to exit, 'ingest' or '/ingest' to index documents, 'clean' or '/clean' to clean documents\n")

    if not health():
        print(f"✗ API unavailable at {API_URL}")
        sys.exit(1)

    print(f"✓ Connected to {API_URL}\n")

    while True:
        try:
            question = pt_prompt(
                FormattedText([("class:you", "you: ")]),
                style=style,
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not question:
            continue
        if question.lower() in ("exit", "quit"):
            break
        if question.lower() in ("clean", "/clean"):
            clean()
            continue
        if question.lower() in ("ingest", "/ingest"):
            ingest()
            continue

        try:
            stream_ask(question)
        except httpx.HTTPStatusError as e:
            print(f"\n✗ HTTP error {e.response.status_code}")
        except httpx.RequestError as e:
            print(f"\n✗ Connection error: {e}")

if __name__ == "__main__":
    main()
