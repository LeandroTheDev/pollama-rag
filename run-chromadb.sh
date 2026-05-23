#!/bin/sh
. "$(dirname "$(readlink -f "$0")")/config.sh"

APP_DIR="$BASE_DIR/chromadb"
mkdir -p $APP_DIR

if podman container exists chromadb; then
    podman start chromadb
else
    podman run -d \
      --name chromadb \
      --restart=always \
      -v "$APP_DIR:/chroma/chroma" \
      -p 8001:8000 \
      docker.io/chromadb/chroma
fi

podman logs --tail 999 chromadb && podman exec -it chromadb sh
