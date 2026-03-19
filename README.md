# HPC Module Tracking System

Ein automatisiertes System zur Sammlung und Darstellung von verfügbaren Software-Modulen für verschiedene HPC-Architekturen auf bwForCluster NEMO 2.

## Architektur-Gruppen

Die Module für **genoa, h200, rtx und mi300a** sind identisch (symbolische Links auf `genoa`). Der Kollektor führt daher nur **einen** lmod-Lauf pro Gruppe durch und dupliziert das Ergebnis.

| Gruppe | Architekturen            | Hinweis                              |
|--------|--------------------------|--------------------------------------|
| genoa  | genoa, h200, rtx, mi300a | Identische Module (symlinks → genoa) |
| milan  | milan                    | Eigener Modul-Baum                   |

## Projektstruktur

```
├── scripts/
│   ├── collect_modules.py      # Modul-Sammlung (lmod → JSON)
│   ├── generate_mediawiki.py   # MediaWiki-Seiten-Generator
│   └── update_git.sh           # Git-Push-Script
├── web/
│   ├── index.html              # Haupt-Webseite
│   ├── module-browser.js       # JavaScript-Logik
│   ├── sample-data.json        # Beispiel-Daten
│   └── sw.js                   # Service Worker
├── data/                       # Generierte JSON-Daten
├── wiki/                       # Generierte MediaWiki-Seiten
└── README.md
```

## Schnellstart

### 1. Modul-Daten sammeln

```bash
# Alle Architekturen (genoa wird nur einmal abgefragt)
make collect

# Nur eine bestimmte Architektur
python3 scripts/collect_modules.py --architecture genoa
```

### 2. MediaWiki-Seiten generieren

```bash
# Eine kombinierte Seite (Standard)
make wiki

# Je eine Seite pro Kategorie
make wiki-cat

# Je eine Seite pro Architektur-Gruppe
make wiki-arch
```

Die generierten `.mediawiki`-Dateien landen in `wiki/`.

### 3. Daten ins Git-Repository pushen

```bash
git remote add origin https://github.com/nemo-cluster/easybuild-modules.git
./scripts/update_git.sh
```

### 4. Webseite anzeigen

```bash
make web
# → http://localhost:8000
```

## Verfügbare Architekturen

- **genoa** – AMD Genoa Prozessoren (S,L,D)
- **h200** – NVIDIA H200 GPUs (S) → identisch mit genoa
- **rtx** – NVIDIA RTX GPUs (S) → identisch mit genoa
- **mi300a** – AMD MI300A GPUs (S) → identisch mit genoa
- **milan** – AMD Milan Prozessoren (S)

## Konfiguration

### Python-Skript

In `collect_modules.py` werden Architekturen und Gruppen zentral definiert:

```python
# Architektur-Gruppen (identische Modul-Bäume)
ARCH_GROUPS = {
    'genoa': ['genoa', 'h200', 'rtx', 'mi300a'],
    'milan': ['milan'],
}

# Kategorien mit Modul-Pfad-Prefix
CATEGORIES = {
    'bio':  'Biology Software (bio/)',
    'lib':  'Libraries (lib/)',
    'chem': 'Chemistry Software (chem/)',
    # ... weitere
}
```

### Web-Interface

In `module-browser.js` die Git-Repository URL anpassen:

```javascript
// Ihre Git-Repository URL für Daten
this.dataUrl = 'https://raw.githubusercontent.com/nemo-cluster/easybuild-modules/main/data/modules_all.json';
```

## Ausgabe-Dateien

### JSON (data/)

- `modules_all.json` – Alle Module kombiniert
- `modules_genoa.json` – Module für Genoa (= H200/RTX/MI300A)
- `modules_h200.json` – Kopie von Genoa mit architecture=h200
- `modules_rtx.json` – Kopie von Genoa mit architecture=rtx
- `modules_mi300a.json` – Kopie von Genoa mit architecture=mi300a
- `modules_milan.json` – Module für Milan
- `metadata.json` – Metadaten über die Sammlung

### MediaWiki (wiki/)

- `Easybuild_Module_List.mediawiki` – Kombinierte Übersicht (make wiki)
- oder getrennte Seiten pro Kategorie / Architektur-Gruppe

## Web-Interface Features

- **Filterung**: Nach Architektur und Kategorie
- **Suche**: Volltext-Suche in Software-Namen und Beschreibungen
- **Sortierung**: Klickbare Spalten-Header
- **Responsive**: Funktioniert auf Desktop und Mobile
- **Offline**: Service Worker für Offline-Funktionalität

## Automatisierung

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

## Fehlerbehebung

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