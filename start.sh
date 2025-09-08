#!/bin/bash

# Ins richtige Verzeichnis wechseln (egal von wo aufgerufen)
cd "$(dirname "$0")"

# Start-Dev Script ausführen
exec ./scripts/start-dev.sh