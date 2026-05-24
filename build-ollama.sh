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

if ! podman exec ollama ollama list | grep -q "$LLM_MODEL"; then
    podman exec -it ollama ollama pull "$LLM_MODEL"
fi


sleep 3
podman stop ollama