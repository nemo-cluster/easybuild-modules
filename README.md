# HPC Module Tracking System

Ein automatisiertes System zur Sammlung und Darstellung von verfügbaren Software-Modulen für verschiedene HPC-Architekturen.

## 🏗️ Projektstruktur

```
module/
├── scripts/
│   ├── collect_modules.py    # Python-Skript zur Modul-Sammlung
│   └── update_git.sh         # Bash-Skript für Git-Updates
├── web/
│   ├── index.html           # Haupt-Webseite
│   ├── module-browser.js    # JavaScript-Logik
│   ├── sample-data.json     # Beispiel-Daten für Tests
│   └── sw.js               # Service Worker (optional)
├── data/                   # Generierte JSON-Daten
└── README.md              # Diese Datei
```

## 🚀 Schnellstart

### 1. Modul-Daten sammeln

```bash
# Sammle Module für alle Architekturen
python3 scripts/collect_modules.py

# Sammle nur für spezifische Architektur
python3 scripts/collect_modules.py --architecture genoa
```

### 2. Daten ins Git-Repository pushen

```bash
# Git-Repository konfigurieren (einmalig)
git remote add origin https://github.com/IHR_USERNAME/IHR_REPO.git

# Daten sammeln und pushen
./scripts/update_git.sh
```

### 3. Webseite anzeigen

```bash
# Lokaler Webserver für Tests
cd web
python3 -m http.server 8000

# Öffne http://localhost:8000
```

## 📊 Verfügbare Architekturen

- **genoa** - AMD Genoa Prozessoren (S,L,D)
- **h200** - NVIDIA H200 GPUs (S)
- **l40s** - NVIDIA L40S GPUs (S)
- **mi300a** - AMD MI300A GPUs (S)
- **milan** - AMD Milan Prozessoren (S)

## 🔧 Konfiguration

### Python-Skript

Das `collect_modules.py` Skript kann angepasst werden:

```python
# Architekturen hinzufügen/entfernen
self.architectures = ['genoa', 'h200', 'l40s', 'mi300a', 'milan']

# Kategorien erweitern
self.categories = {
    'bio': 'Biology Software',
    'chem': 'Chemistry Software', 
    'compiler': 'Compilers',
    # ... weitere Kategorien
}
```

### Web-Interface

In `module-browser.js` die Git-Repository URL anpassen:

```javascript
// Ihre Git-Repository URL für Daten
this.dataUrl = 'https://raw.githubusercontent.com/nemo-cluster/easybuild-modules/main/data/modules_all.json';
```

## 📁 Ausgabe-Dateien

Das System generiert folgende JSON-Dateien:

- `modules_all.json` - Alle Module kombiniert
- `modules_genoa.json` - Module nur für Genoa
- `modules_h200.json` - Module nur für H200
- `modules_l40s.json` - Module nur für L40S
- `modules_mi300a.json` - Module nur für MI300A
- `modules_milan.json` - Module nur für Milan
- `metadata.json` - Metadaten über die Sammlung

## 🌐 Web-Interface Features

- **Filterung**: Nach Architektur und Kategorie
- **Suche**: Volltext-Suche in Software-Namen und Beschreibungen
- **Sortierung**: Klickbare Spalten-Header
- **Responsive**: Funktioniert auf Desktop und Mobile
- **Offline**: Service Worker für Offline-Funktionalität

## 🔄 Automatisierung

### Cron-Job für regelmäßige Updates

```bash
# Täglich um 6:00 Uhr Module sammeln und pushen
0 6 * * * cd /pfad/zum/projekt && ./scripts/update_git.sh >> /var/log/module-update.log 2>&1
```

### GitHub Actions (optional)

Erstellen Sie `.github/workflows/update-modules.yml`:

```yaml
name: Update Module Data
on:
  schedule:
    - cron: '0 6 * * *'  # Täglich um 6:00 UTC
  workflow_dispatch:

jobs:
  update:
    runs-on: self-hosted  # Auf HPC-System mit lmod
    steps:
      - uses: actions/checkout@v4
      - name: Collect modules
        run: python3 scripts/collect_modules.py
      - name: Commit and push
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add data/
          git commit -m "Auto-update module data" || exit 0
          git push
```

## 🐛 Fehlerbehebung

### Module-Sammlung funktioniert nicht

1. Prüfen Sie ob `lmod` verfügbar ist:
   ```bash
   module --version
   ```

2. Testen Sie manuell:
   ```bash
   module load arch/genoa
   module avail
   ```

3. Prüfen Sie Berechtigungen für die Architekturen

### Web-Interface zeigt keine Daten

1. Prüfen Sie die Git-Repository URL in `module-browser.js`
2. Stellen Sie sicher, dass das Repository öffentlich ist
3. Testen Sie mit lokalen Daten über `sample-data.json`

### Git-Push schlägt fehl

1. Konfigurieren Sie Git-Credentials:
   ```bash
   git config --global user.name "Ihr Name"
   git config --global user.email "ihre.email@domain.de"
   ```

2. Verwenden Sie SSH-Keys oder Personal Access Tokens

## 📝 Lizenz

MIT License - Siehe LICENSE Datei für Details.

## 🤝 Beitragen

1. Fork des Repositories
2. Feature-Branch erstellen (`git checkout -b feature/AmazingFeature`)
3. Änderungen committen (`git commit -m 'Add some AmazingFeature'`)
4. Branch pushen (`git push origin feature/AmazingFeature`)
5. Pull Request öffnen

## 📞 Support

Bei Fragen oder Problemen erstellen Sie bitte ein Issue im GitHub Repository.