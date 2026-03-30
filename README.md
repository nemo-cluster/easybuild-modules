# bwForCluster NEMO 2 – Easybuild Module Tracking

Automatisierte Erfassung und Darstellung verfügbarer Softwaremodule für alle HPC-Architekturen auf bwForCluster NEMO 2.

## Architektur-Gruppen

| Gruppe | Architekturen             | Hinweis                               |
|--------|---------------------------|---------------------------------------|
| genoa  | genoa, h200, rtx, mi300a  | Identische Module (Symlinks → genoa)  |
| l40s   | l40s                      | Eigener Modul-Baum                    |
| milan  | milan                     | Eigener Modul-Baum                    |

Die Gruppen `genoa`, `l40s` und `milan` werden separat per lmod abgefragt. `h200`, `rtx` und `mi300a` sind Kopien von `genoa`.

## Projektstruktur

```
scripts/
  collect_modules.py          # Modul-Sammlung (lmod → JSON)
  generate_mediawiki.py       # MediaWiki- und Spiderlein-Generator
  spiderlein_allowlist.txt    # Allowlist für Spiderlein-Ausgabe
  spiderlein_cat_rename.json  # Umbenennung/Umkategorisierung für Spiderlein
  update_git.sh               # Git-Push-Script
  upload_mediawiki.py         # Upload auf bwHPC-Wiki
data/
  modules_all.json            # Alle Module kombiniert
  modules_genoa.json          # genoa (= h200, rtx, mi300a)
  modules_h200.json           # Kopie von genoa mit architecture=h200
  modules_rtx.json            # Kopie von genoa mit architecture=rtx
  modules_mi300a.json         # Kopie von genoa mit architecture=mi300a
  modules_l40s.json           # l40s
  modules_milan.json          # milan
  metadata.json               # Metadaten (Zeitstempel, Architekturen)
web/
  index.html                  # Modul-Browser (Webseite)
  module-browser.js           # JavaScript-Logik
  nemo2_spiderlein_gsorted.html  # Spiderlein-kompatible Ausgabe
  spiderlein_preview.html     # Vorschau-Viewer für Spiderlein-Output
wiki/
  Easybuild_Module_List.mediawiki   # Kombinierte Übersicht
  Modules_<Kategorie>__.mediawiki   # Je eine Seite pro Kategorie
  Modules_<Arch>.mediawiki          # Je eine Seite pro Architektur-Gruppe
```

## Schnellstart

```bash
# Modul-Daten sammeln (auf dem Cluster mit lmod)
make collect

# MediaWiki-Seiten generieren
make wiki          # kombinierte Seite
make wiki-cat      # eine Seite pro Kategorie
make wiki-arch     # eine Seite pro Architektur-Gruppe

# Spiderlein-kompatible HTML generieren (web/nemo2_spiderlein_gsorted.html)
make spiderlein

# Lokalen Webserver starten
make web           # → http://localhost:8000
make spiderlein-preview  # → http://localhost:8000/spiderlein_preview.html

# Daten pushen
make push
```

## Spiderlein-Ausgabe

Die Spiderlein-Ausgabe (`web/nemo2_spiderlein_gsorted.html`) ist kompatibel mit dem bwHPC-Softwareportal. Sie wird über `generate_mediawiki.py --mode spiderlein` erzeugt.

**Konfiguration:**
- `scripts/spiderlein_allowlist.txt` – welche Module erscheinen (leer = alle)
- `scripts/spiderlein_cat_rename.json` – Umbenennungen für Konsistenz mit anderen Clustern:
  - `software`: Software-Name-Aliase (z. B. `gcc` → `gnu`)
  - `category`: globale Kategorie-Umbenennungen (z. B. `lang` → `devel`)
  - `move`: per-Software-Umkategorisierung (z. B. `bio/gromacs` → `chem`)

Die Umbennungen gelten **nur** für die Spiderlein-Ausgabe. Browser und Wiki zeigen die echten EasyBuild-Pfade.

## Webseite / Modul-Browser

```bash
make web  # startet http.server auf Port 8000
```

Die Seite lädt `data/modules_all.json` direkt aus dem Repository. URL in `web/module-browser.js` anpassen falls nötig.

## Lizenz

MIT – siehe `LICENSE`.

