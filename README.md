# AI

Local RAG (Retrieval-Augmented Generation) stack running on Podman containers.

## Stack

| Service | Description | Port |
|---|---|---|
| **Ollama** | LLM and embedding model runner | 11434 |
| **ChromaDB** | Vector database for document embeddings | 8001 |
| **RAG API** | FastAPI service for ingestion and querying | 8000 |
| **RAG CLI** | Interactive terminal client | — |

## Requirements

- [Podman](https://podman.io/)
- NVIDIA GPU with container support (`nvidia.com/gpu`)

## Usage

### Start everything

```sh
./start.sh
```

This will start ChromaDB, Ollama, and the RAG API, then launch the RAG CLI automatically.

### Stop everything

```sh
./stop.sh
```

### Run services individually

```sh
./run-chromadb.sh
./run-ollama.sh
./run-rag-api.sh
./run-rag-cli.sh
```

## CLI Commands

Inside the RAG CLI:

| Command | Description |
|---|---|
| `ingest` or `/ingest` | Index all documents in the `documents/` folder |
| `exit` or `quit` | Exit the CLI |
| Any other text | Query the RAG engine |

## Adding Documents

Place files (PDF, TXT, etc.) in the `documents/` folder, then run `/ingest` inside the CLI to index them.

## Configuration

Edit `config.sh` to change the base directory:

```sh
BASE_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
```

By default it resolves to the directory where the scripts are located.
