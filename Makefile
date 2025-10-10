# Makefile für HPC Module Tracking System

.PHONY: help collect web push clean install test serve

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
	rm -rf data/*.json
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
	@python3 -c "import sys; sys.path.append('scripts'); from collect_modules import ModuleCollector; collector = ModuleCollector(); print('✓ ModuleCollector can be imported'); print(f'✓ Architectures: {collector.architectures}'); print(f'✓ Categories: {len(collector.categories)} defined')"
	@echo "2. Testing web files..."
	@test -f web/index.html && echo "✓ index.html present" || echo "✗ index.html missing"
	@test -f web/module-browser.js && echo "✓ module-browser.js present" || echo "✗ module-browser.js missing"
	@test -f web/sample-data.json && echo "✓ sample-data.json present" || echo "✗ sample-data.json missing"
	@echo "3. Testing Git setup..."
	@git --version > /dev/null && echo "✓ Git available" || echo "✗ Git not available"
	@echo "Tests completed!"

# Collect modules for specific architecture
collect-genoa:
	python3 scripts/collect_modules.py --architecture genoa --output-dir data

collect-h200:
	python3 scripts/collect_modules.py --architecture h200 --output-dir data

collect-l40s:
	python3 scripts/collect_modules.py --architecture l40s --output-dir data

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