#!/bin/sh
cd "$(dirname "$0")"

mkdir -p ollama
mkdir -p chromadb

. ./config.sh

./stop.sh

start_container() {
    NAME=$1
    shift
    if podman container exists "$NAME"; then
        podman start "$NAME"
    else
        podman run -d "$@"
    fi
    echo "[$NAME] started"
}

# ChromaDB
APP_DIR="$BASE_DIR/chromadb"
mkdir -p "$APP_DIR"
start_container chromadb \
    --name chromadb \
    --restart=always \
    -v "$APP_DIR:/chroma/chroma" \
    -p 8001:8000 \
    docker.io/chromadb/chroma

# Ollama
APP_DIR="$BASE_DIR/ollama"
mkdir -p "$APP_DIR"
start_container ollama \
    --name ollama \
    --restart=always \
    --device nvidia.com/gpu=all \
    -v "$APP_DIR:/root/.ollama" \
    -p 11434:11434 \
    docker.io/ollama/ollama

# Pull models if needed
for MODEL in qwen3.5:4b nomic-embed-text; do
    if ! podman exec ollama ollama list | grep -q "$MODEL"; then
        echo "[ollama] pulling $MODEL..."
        podman exec ollama ollama pull "$MODEL"
    fi
done

# RAG API
IMAGE_NAME="localhost/rag-api"
APP_DIR="$BASE_DIR/rag-api"
mkdir -p "$APP_DIR"
if ! podman image exists "$IMAGE_NAME"; then
    echo "[rag-api] building..."
    podman build -t "$IMAGE_NAME" -f "$APP_DIR/Containerfile" "$APP_DIR"
fi
start_container rag-api \
    --name rag-api \
    --restart=always \
    -v "$BASE_DIR/documents:/app/documents" \
    -p 8000:8000 \
    "$IMAGE_NAME"

echo ""
echo "Waiting services..."
sleep 3

echo ""
podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
./run-rag-cli.sh
