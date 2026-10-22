#!/bin/sh
# Starts Iris on this machine. Open http://127.0.0.1:8473 and use the browser's "Install" option.
cd "$(dirname "$0")" && exec python3 iris/webui.py --store store "$@"
