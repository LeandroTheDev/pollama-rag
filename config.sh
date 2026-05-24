#!/bin/sh

# Base directory for data and scripts
BASE_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"

# Models — change here to switch without rebuilding images
LLM_MODEL="${LLM_MODEL:-qwen3.5:4b}"
EMBED_MODEL="${EMBED_MODEL:-BAAI/bge-small-en-v1.5}"
