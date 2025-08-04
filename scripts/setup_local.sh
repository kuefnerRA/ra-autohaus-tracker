#!/bin/bash
set -e

echo "🚀 Lokale Entwicklungsumgebung für RA Autohaus Tracker"

# Virtual Environment erstellen/aktivieren
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual Environment aktiviert"
else
    echo "📦 Virtual Environment erstellen..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Dependencies installieren
echo "📚 Dependencies installieren..."
pip install --upgrade pip
pip install -r requirements.txt

# VS Code Konfiguration
echo "💻 VS Code Konfiguration..."
mkdir -p .vscode
cat > .vscode/settings.json << 'VSCODE_EOF'
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/.pytest_cache": true,
        "**/venv": true
    }
}
VSCODE_EOF

echo "✅ Setup abgeschlossen!"
echo "📝 Nächste Schritte:"
echo "1. Virtual Environment aktivieren: source venv/bin/activate"
echo "2. Google Cloud auth: gcloud auth application-default login"
echo "3. VS Code starten: code ."
