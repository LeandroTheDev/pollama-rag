#!/bin/sh
. "$(dirname "$(readlink -f "$0")")/config.sh"

IMAGE_NAME="localhost/rag-cli"
APP_DIR="$BASE_DIR/rag-cli"

#podman rm -f rag-cli
#podman rmi localhost/rag-cli

if ! podman image exists "$IMAGE_NAME"; then
    echo "Building rag-cli..."
    podman build -t "$IMAGE_NAME" -f "$APP_DIR/Containerfile" "$APP_DIR"
fi

podman run -it --rm \
    --name rag-cli \
    --network host \
    "$IMAGE_NAME"
