#!/bin/bash
# init_repo.sh - Repository für RA Autohaus Tracker initialisieren

set -e

echo "🚀 RA Autohaus Tracker Repository Setup"
echo "Verzeichnis: $(pwd)"

# 1. Git Repository initialisieren (falls noch nicht geschehen)
if [ ! -d ".git" ]; then
    echo "📋 Git Repository initialisieren..."
    git init
    git branch -M main
else
    echo "✅ Git Repository bereits vorhanden"
fi

# 2. Remote Repository verbinden
echo "🔗 Remote Repository verbinden..."
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/kuefnerRA/ra-autohaus-tracker.git

# 3. Verzeichnisstruktur erstellen
echo "📁 Verzeichnisstruktur erstellen..."
mkdir -p .github/workflows
mkdir -p src/{models,handlers,services,utils}
mkdir -p tests
mkdir -p scripts
mkdir -p config
mkdir -p docs

# 4. .gitignore erstellen
echo "🚫 .gitignore erstellen..."
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual Environment
venv/
env/
ENV/

# Environment Variables
.env
*.env
config/local.env

# Google Cloud
key.json
service-account-key.json
*-key.json

# IDE
.vscode/settings.json
.idea/

# Logs
*.log
logs/

# Testing
.coverage
.pytest_cache/
htmlcov/

# OS
.DS_Store
Thumbs.db

# Project specific
tmp/
data/
*.backup
EOF