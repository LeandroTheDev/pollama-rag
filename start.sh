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
    -v "$APP_DIR:/data" \
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

# Pull LLM model if needed (embed model is handled by FastEmbed locally)
if ! podman exec ollama ollama list | grep -q "$LLM_MODEL"; then
    echo "[ollama] pulling $LLM_MODEL..."
    podman exec ollama ollama pull "$LLM_MODEL"
fi

# RAG API (always recreated to pick up env var changes)
IMAGE_NAME="localhost/rag-api"
APP_DIR="$BASE_DIR/rag-api"
mkdir -p "$APP_DIR"
if ! podman image exists "$IMAGE_NAME"; then
    echo "[rag-api] building..."
    podman build -t "$IMAGE_NAME" -f "$APP_DIR/Containerfile" "$APP_DIR"
fi
podman rm -f rag-api 2>/dev/null
podman run -d \
    --name rag-api \
    --restart=always \
    -e "LLM_MODEL=$LLM_MODEL" \
    -e "EMBED_MODEL=$EMBED_MODEL" \
    -v "$BASE_DIR/documents:/app/documents" \
    -p 8000:8000 \
    "$IMAGE_NAME"
echo "[rag-api] started"

echo ""
echo "Waiting services..."
sleep 3

echo ""
podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

until curl -s http://127.0.0.1:8000/health > /dev/null; do
    echo "Waiting rag-api..."
    sleep 2
done

echo ""

./run-rag-cli.sh
./stop.sh
