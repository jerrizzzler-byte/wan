#!/bin/bash
# ---------------------------------------------------------------------------
# boot.sh -- RunPod container startup for the ComfyUI WAN template.
# Fetched and run by the template's "Container start command".
#
# It:
#   1. launches the image's own /start.sh in the background (boots ComfyUI,
#      JupyterLab, FileBrowser, and creates the ComfyUI venv)
#   2. downloads download.py + download.txt from GitHub
#   3. waits until the ComfyUI venv exists
#   4. runs download.py (apt packages, custom nodes, KJNodes pin, models)
#   5. keeps the container alive
# ---------------------------------------------------------------------------

REPO="https://raw.githubusercontent.com/jerrizzzler-byte/wan/main"
VENV_PYTHON="/workspace/runpod-slim/ComfyUI/.venv-cu128/bin/python"

echo "[boot] starting image /start.sh in background ..."
/start.sh &
START_PID=$!

echo "[boot] downloading download.py and download.txt from GitHub ..."
curl -sL "$REPO/download.py" -o /download.py
curl -sL "$REPO/download.txt" -o /download.txt

if [ ! -s /download.py ] || [ ! -s /download.txt ]; then
    echo "[boot] ERROR: failed to download script files from GitHub."
    echo "[boot] ComfyUI will still run; rerun the download manually if needed."
else
    echo "[boot] waiting for ComfyUI venv to be created by /start.sh ..."
    while [ ! -f "$VENV_PYTHON" ]; do
        echo "[boot] venv not ready yet, waiting 5s ..."
        sleep 5
    done
    echo "[boot] venv is ready -- running download.py"
    python3 /download.py
    echo "[boot] download.py finished -- restart ComfyUI to load new nodes."
fi

# keep the container alive by waiting on the backgrounded /start.sh
wait $START_PID
