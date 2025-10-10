#!/bin/bash
# Git Push Script für HPC Module Data
# Pushed die gesammelten Modul-Daten ins Git-Repository

set -e

# Konfiguration
DATA_DIR="./data"
COMMIT_MESSAGE="Update module data - $(date '+%Y-%m-%d %H:%M:%S')"

# Prüfe ob Git-Repository initialisiert ist
if [ ! -d ".git" ]; then
    echo "Git-Repository nicht gefunden. Initialisiere Repository..."
    git init
    echo "# HPC Module Data" > README.md
    echo "Automatisch generierte Daten über verfügbare HPC-Module" >> README.md
    git add README.md
    git commit -m "Initial commit"
fi

# Prüfe ob Remote-Repository konfiguriert ist
if ! git remote get-url origin >/dev/null 2>&1; then
    echo "Warnung: Kein Remote-Repository konfiguriert."
    echo "Fügen Sie ein Remote-Repository hinzu mit:"
    echo "  git remote add origin <REPOSITORY_URL>"
    echo "Dann führen Sie dieses Skript erneut aus."
    exit 1
fi

# Sammle Module-Daten
echo "Sammle Modul-Daten..."
python3 scripts/collect_modules.py --output-dir "$DATA_DIR"

# Prüfe ob Daten vorhanden sind
if [ ! -d "$DATA_DIR" ] || [ -z "$(ls -A "$DATA_DIR")" ]; then
    echo "Fehler: Keine Daten im Verzeichnis $DATA_DIR gefunden"
    exit 1
fi

# Git-Operationen
echo "Füge Änderungen zu Git hinzu..."
git add "$DATA_DIR"/*

# Prüfe ob es Änderungen gibt
if git diff --staged --quiet; then
    echo "Keine Änderungen gefunden. Kein Commit erforderlich."
    exit 0
fi

# Commit und Push
echo "Erstelle Commit..."
git commit -m "$COMMIT_MESSAGE"

echo "Pushe Änderungen..."
git push origin main

echo "Daten erfolgreich ins Repository gepusht!"

# Zeige Statistiken
echo ""
echo "Statistiken:"
if [ -f "$DATA_DIR/metadata.json" ]; then
    python3 -c "
import json
with open('$DATA_DIR/metadata.json', 'r') as f:
    metadata = json.load(f)
print(f\"Architekturen: {', '.join(metadata['architectures'])}\")
print(f\"Gesamt Module: {metadata['total_modules']}\")
for arch, count in metadata['modules_per_arch'].items():
    print(f\"  {arch}: {count} Module\")
"
fi