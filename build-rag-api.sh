#!/bin/sh
. "$(dirname "$(readlink -f "$0")")/config.sh"

IMAGE_NAME="localhost/rag-api"
APP_DIR="$BASE_DIR/rag-api"
mkdir -p $APP_DIR

podman rm -f rag-api
podman rmi localhost/rag-api

# build image if it doesn't exist
if ! podman image exists "$IMAGE_NAME"; then
    echo "Building rag-api..."
    podman build -t "$IMAGE_NAME" "$APP_DIR"
fi

# start or create container
if podman container exists rag-api; then
    podman start rag-api
else
    podman run -d \
      --name rag-api \
      --restart=always \
      -v "$BASE_DIR/documents:/app/documents" \
      -p 8000:8000 \
      "$IMAGE_NAME"
fi

podman logs --tail 999 rag-api
sleep 3
podman stop rag-api
