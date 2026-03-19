#!/bin/bash
# Git Push Script for bwForCluster NEMO 2 Easybuild Module Data
# Pushes collected module data to Git repository

set -e

# Configuration
DATA_DIR="./data"
COMMIT_MESSAGE="Update module data - $(date '+%Y-%m-%d %H:%M:%S')"

# Check if Git repository is initialized
if [ ! -d ".git" ]; then
    echo "Git repository not found. Initializing repository..."
    git init
    echo "# bwForCluster NEMO 2 Easybuild Module Data" > README.md
    echo "Automatically generated data about available HPC modules" >> README.md
    git add README.md
    git commit -m "Initial commit"
fi

# Check if remote repository is configured
if ! git remote get-url origin >/dev/null 2>&1; then
    echo "Warning: No remote repository configured."
    echo "Add a remote repository with:"
    echo "  git remote add origin <REPOSITORY_URL>"
    echo "Then run this script again."
    exit 1
fi

# Collect module data
echo "Collecting module data..."
python3 scripts/collect_modules.py --output-dir "$DATA_DIR"
cp "$DATA_DIR/metadata.json" web/metadata.json

# Generate MediaWiki pages
echo "Generating MediaWiki pages..."
python3 scripts/generate_mediawiki.py --data-dir "$DATA_DIR" --output-dir wiki --mode combined

# Check if data exists
if [ ! -d "$DATA_DIR" ] || [ -z "$(ls -A "$DATA_DIR")" ]; then
    echo "Error: No data found in directory $DATA_DIR"
    exit 1
fi

# Git operations
echo "Adding changes to Git..."
git add "$DATA_DIR"/* wiki/*

# Check if there are changes
if git diff --staged --quiet; then
    echo "No changes found. No commit required."
    exit 0
fi

# Commit and push
echo "Creating commit..."
git commit -m "$COMMIT_MESSAGE"

echo "Pushing changes..."
git push origin main

echo "Data successfully pushed to repository!"

# Show statistics
echo ""
echo "Statistics:"
if [ -f "$DATA_DIR/metadata.json" ]; then
    python3 -c "
import json
with open('$DATA_DIR/metadata.json', 'r') as f:
    metadata = json.load(f)
print(f\"Architectures: {', '.join(metadata['architectures'])}\")
print(f\"Total modules: {metadata['total_modules']}\")
for arch, count in metadata['modules_per_arch'].items():
    print(f\"  {arch}: {count} modules\")
"
fi