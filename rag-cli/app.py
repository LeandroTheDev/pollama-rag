#!/usr/bin/env python3
import sys
import httpx
from docs_cleanup import clean_txt
import glob, os

API_URL = "http://127.0.0.1:8000"

def stream_ask(question: str):
    with httpx.Client(timeout=None) as client:
        with client.stream("POST", f"{API_URL}/ask/stream",
                           json={"question": question}) as r:
            r.raise_for_status()
            for chunk in r.iter_bytes():
                print(chunk.decode("utf-8", errors="replace"), end="", flush=True)
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
            question = input("you: ").strip()
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

        print("rag: ", end="", flush=True)
        try:
            stream_ask(question)
        except httpx.HTTPStatusError as e:
            print(f"\n✗ HTTP error {e.response.status_code}")
        except httpx.RequestError as e:
            print(f"\n✗ Connection error: {e}")

if __name__ == "__main__":
    main()
