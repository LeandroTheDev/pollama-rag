#!/bin/sh
. "$(dirname "$(readlink -f "$0")")/config.sh"

APP_DIR="$BASE_DIR/ollama"
mkdir -p $APP_DIR

if podman container exists ollama; then
    podman start ollama
else
    podman run -d \
      --name ollama \
      --restart=always \
      --device nvidia.com/gpu=all \
      -v "$APP_DIR:/root/.ollama" \
      -p 11434:11434 \
      docker.io/ollama/ollama
fi

if ! podman exec ollama ollama list | grep -q "qwen3.5:4b"; then
    podman exec -it ollama ollama pull qwen3.5:4b
fi

if ! podman exec ollama ollama list | grep -q "nomic-embed-text"; then
    podman exec -it ollama ollama pull nomic-embed-text
fi

podman exec -it ollama ollama run qwen3.5:9b
