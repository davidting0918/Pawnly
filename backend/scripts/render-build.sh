#!/usr/bin/env bash
# Render build script — installs dependencies + Stockfish
set -e

# Install Python dependencies
pip install -r requirements.txt

# Download Stockfish binary directly (no apt-get needed)
STOCKFISH_DIR="/opt/render/project/src/backend/bin"
mkdir -p "$STOCKFISH_DIR"

if [ ! -f "$STOCKFISH_DIR/stockfish" ]; then
  echo "Downloading Stockfish..."
  curl -L -o /tmp/stockfish.tar \
    "https://github.com/official-stockfish/Stockfish/releases/download/sf_17.1/stockfish-ubuntu-x86-64-avx2.tar"
  tar -xf /tmp/stockfish.tar -C /tmp/
  cp /tmp/stockfish/stockfish-ubuntu-x86-64-avx2 "$STOCKFISH_DIR/stockfish"
  chmod +x "$STOCKFISH_DIR/stockfish"
  rm -rf /tmp/stockfish /tmp/stockfish.tar
fi

echo "✅ Stockfish at: $STOCKFISH_DIR/stockfish"
"$STOCKFISH_DIR/stockfish" <<< "quit" | head -1
echo "✅ Build complete"
