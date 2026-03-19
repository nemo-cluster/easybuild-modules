# Makefile für HPC Module Tracking System

.PHONY: help collect web push clean install test serve wiki

# Standard target
help:
	@echo "bwForCluster NEMO 2 Easybuild Module Tracking System"
	@echo "====================================================="
	@echo ""
	@echo "Available commands:"
	@echo "  make collect    - Collect module data for all architectures"
	@echo "  make web        - Start local web server (port 8000)"
	@echo "  make push       - Collect data and push to Git repository"
	@echo "  make clean      - Delete generated data"
	@echo "  make install    - Install Python dependencies"
	@echo "  make test       - Test the system with sample data"
	@echo "  make serve      - Alias for 'make web'"
	@echo "  make wiki       - Generate MediaWiki page(s) (combined)"
	@echo "  make wiki-cat   - Generate one MediaWiki page per category"
	@echo "  make wiki-arch  - Generate one MediaWiki page per arch group"

# Collect module data
collect:
	@echo "Collecting module data..."
	python3 scripts/collect_modules.py --output-dir data
	@echo "Done! Data saved in 'data/' directory."

# Start local web server
web serve:
	@echo "Starting web server on http://localhost:8000"
	@cd web && python3 -m http.server 8000

# Collect data and push to Git repository
push:
	@echo "Collecting data and pushing to repository..."
	./scripts/update_git.sh

# Delete generated data
clean:
	@echo "Deleting generated data..."
	rm -rf data/*.json wiki/*.mediawiki
	@echo "Data deleted."

# Install Python dependencies (if required)
install:
	@echo "Installing Python dependencies..."
	# For extended features, pip installations could be here
	@echo "No additional dependencies required."

# Test system
test:
	@echo "Testing the system..."
	@echo "1. Testing Python script with mock data..."
	@python3 -c "import sys; sys.path.append('scripts'); from collect_modules import ModuleCollector, ALL_ARCHITECTURES, ARCH_GROUPS, CATEGORIES; collector = ModuleCollector(); print('✓ ModuleCollector can be imported'); print(f'✓ Architectures: {ALL_ARCHITECTURES}'); print(f'✓ Arch groups: {ARCH_GROUPS}'); print(f'✓ Categories: {len(CATEGORIES)} defined')"
	@echo "2. Testing MediaWiki generator..."
	@python3 -c "import sys; sys.path.append('scripts'); from generate_mediawiki import generate_combined, load_data; print('✓ generate_mediawiki can be imported')"
	@echo "3. Testing web files..."
	@test -f web/index.html && echo "✓ index.html present" || echo "✗ index.html missing"
	@test -f web/module-browser.js && echo "✓ module-browser.js present" || echo "✗ module-browser.js missing"
	@test -f web/sample-data.json && echo "✓ sample-data.json present" || echo "✗ sample-data.json missing"
	@echo "4. Testing Git setup..."
	@git --version > /dev/null && echo "✓ Git available" || echo "✗ Git not available"
	@echo "Tests completed!"

# Generate MediaWiki pages
wiki:
	@echo "Generating combined MediaWiki page..."
	python3 scripts/generate_mediawiki.py --data-dir data --output-dir wiki --mode combined

wiki-cat:
	@echo "Generating per-category MediaWiki pages..."
	python3 scripts/generate_mediawiki.py --data-dir data --output-dir wiki --mode per-category

wiki-arch:
	@echo "Generating per-architecture MediaWiki pages..."
	python3 scripts/generate_mediawiki.py --data-dir data --output-dir wiki --mode per-arch

# Collect modules for specific architecture
collect-genoa:
	python3 scripts/collect_modules.py --architecture genoa --output-dir data

collect-h200:
	python3 scripts/collect_modules.py --architecture h200 --output-dir data

collect-rtx:
	python3 scripts/collect_modules.py --architecture rtx --output-dir data

collect-mi300a:
	python3 scripts/collect_modules.py --architecture mi300a --output-dir data

collect-milan:
	python3 scripts/collect_modules.py --architecture milan --output-dir data

# Initialize Git repository
init-git:
	@echo "Initializing Git repository..."
	@if [ ! -d ".git" ]; then \
		git init; \
		git add .; \
		git commit -m "Initial commit: bwForCluster NEMO 2 Easybuild Module Tracking System"; \
		echo "Repository initialized."; \
		echo "Add a remote repository with:"; \
		echo "  git remote add origin <REPOSITORY_URL>"; \
	else \
		echo "Git repository already exists."; \
	fi

# Show project status
status:
	@echo "bwForCluster NEMO 2 Easybuild Module Tracking System - Status"
	@echo "=============================================================="
	@echo "Project structure:"
	@find . -type f -name "*.py" -o -name "*.js" -o -name "*.html" -o -name "*.json" -o -name "*.sh" | head -20
	@echo ""
	@echo "Data directory:"
	@if [ -d "data" ]; then \
		ls -la data/ || echo "No files in data/ directory"; \
	else \
		echo "data/ directory does not exist"; \
	fi
	@echo ""
	@echo "Git status:"
	@git status --short 2>/dev/null || echo "No Git repository"