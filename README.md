# Pollama Rag

Local RAG (Retrieval-Augmented Generation) stack running on Podman containers.

## Stack

| Service | Description | Port |
|---|---|---|
| **Ollama** | LLM runner | 11434 |
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

### Build images manually

```sh
./build-chromadb.sh
./build-ollama.sh
./build-rag-api.sh
```

### Run the CLI

```sh
./run-rag-cli.sh
```

## CLI Commands

Inside the RAG CLI:

| Command | Description |
|---|---|
| `ingest` or `/ingest` | Index all documents in the `documents/` folder |
| `clean` or `/clean` | Clean and normalize all `.txt` files in `documents/` |
| `exit` or `quit` | Exit the CLI |
| Any other text | Query the RAG engine |

## Adding Documents

Place files (PDF, TXT, etc.) in the `documents/` folder, then run `/ingest` inside the CLI to index them.

## Configuration

Edit `config.sh` to change models or the base directory:

```sh
BASE_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
LLM_MODEL="qwen3.5:4b"
EMBED_MODEL="BAAI/bge-small-en-v1.5"
```

Models can also be overridden via environment variables:

```sh
LLM_MODEL=llama3:8b ./start.sh
```

The embedding model uses [FastEmbed](https://github.com/qdrant/fastembed) and runs locally inside the RAG API container — no Ollama required for embeddings.

> **Note:** changing `EMBED_MODEL` requires deleting the ChromaDB data and re-ingesting all documents, since embedding dimensions must match.

## Data Persistence

ChromaDB data is stored in `chromadb/` (mounted to `/data` inside the container). If the container is recreated without this volume, data is lost.
