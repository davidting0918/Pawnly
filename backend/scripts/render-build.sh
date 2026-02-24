#!/usr/bin/env bash
# Render build script — installs dependencies + Stockfish

set -e

# Install Python dependencies
pip install -r requirements.txt

# Install Stockfish chess engine (needed for bot play)
apt-get update && apt-get install -y --no-install-recommends stockfish

echo "✅ Build complete — Stockfish at $(which stockfish)"
