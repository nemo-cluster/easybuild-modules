# Makefile für HPC Module Tracking System

.PHONY: help collect web push clean install test serve

# Standard-Ziel
help:
	@echo "HPC Module Tracking System"
	@echo "=========================="
	@echo ""
	@echo "Verfügbare Befehle:"
	@echo "  make collect    - Sammle Module-Daten für alle Architekturen"
	@echo "  make web        - Starte lokalen Webserver (Port 8000)"
	@echo "  make push       - Sammle Daten und pushe ins Git-Repository"
	@echo "  make clean      - Lösche generierte Daten"
	@echo "  make install    - Installiere Python-Abhängigkeiten"
	@echo "  make test       - Teste das System mit Beispiel-Daten"
	@echo "  make serve      - Alias für 'make web'"

# Module-Daten sammeln
collect:
	@echo "Sammle Module-Daten..."
	python3 scripts/collect_modules.py --output-dir data
	@echo "Fertig! Daten in 'data/' Verzeichnis gespeichert."

# Lokalen Webserver starten
web serve:
	@echo "Starte Webserver auf http://localhost:8000"
	@cd web && python3 -m http.server 8000

# Daten sammeln und ins Git-Repository pushen
push:
	@echo "Sammle Daten und pushe ins Repository..."
	./scripts/update_git.sh

# Generierte Daten löschen
clean:
	@echo "Lösche generierte Daten..."
	rm -rf data/*.json
	@echo "Daten gelöscht."

# Python-Abhängigkeiten installieren (falls erforderlich)
install:
	@echo "Installiere Python-Abhängigkeiten..."
	# Für erweiterte Features könnten hier pip-Installationen stehen
	@echo "Keine zusätzlichen Abhängigkeiten erforderlich."

# System testen
test:
	@echo "Teste das System..."
	@echo "1. Teste Python-Skript mit Mock-Daten..."
	@python3 -c "import sys; sys.path.append('scripts'); from collect_modules import ModuleCollector; collector = ModuleCollector(); print('✓ ModuleCollector kann importiert werden'); print(f'✓ Architekturen: {collector.architectures}'); print(f'✓ Kategorien: {len(collector.categories)} definiert')"
	@echo "2. Teste Web-Dateien..."
	@test -f web/index.html && echo "✓ index.html vorhanden" || echo "✗ index.html fehlt"
	@test -f web/module-browser.js && echo "✓ module-browser.js vorhanden" || echo "✗ module-browser.js fehlt"
	@test -f web/sample-data.json && echo "✓ sample-data.json vorhanden" || echo "✗ sample-data.json fehlt"
	@echo "3. Teste Git-Setup..."
	@git --version > /dev/null && echo "✓ Git verfügbar" || echo "✗ Git nicht verfügbar"
	@echo "Tests abgeschlossen!"

# Sammle Module für spezifische Architektur
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

# Git-Repository initialisieren
init-git:
	@echo "Initialisiere Git-Repository..."
	@if [ ! -d ".git" ]; then \
		git init; \
		git add .; \
		git commit -m "Initial commit: HPC Module Tracking System"; \
		echo "Repository initialisiert."; \
		echo "Fügen Sie ein Remote-Repository hinzu mit:"; \
		echo "  git remote add origin <REPOSITORY_URL>"; \
	else \
		echo "Git-Repository bereits vorhanden."; \
	fi

# Zeige Projekt-Status
status:
	@echo "HPC Module Tracking System - Status"
	@echo "===================================="
	@echo "Projektstruktur:"
	@find . -type f -name "*.py" -o -name "*.js" -o -name "*.html" -o -name "*.json" -o -name "*.sh" | head -20
	@echo ""
	@echo "Daten-Verzeichnis:"
	@if [ -d "data" ]; then \
		ls -la data/ || echo "Keine Dateien im data/ Verzeichnis"; \
	else \
		echo "data/ Verzeichnis existiert nicht"; \
	fi
	@echo ""
	@echo "Git-Status:"
	@git status --short 2>/dev/null || echo "Kein Git-Repository"