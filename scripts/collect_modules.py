#!/usr/bin/env python3
"""
HPC Module Collector
Sammelt Informationen über verfügbare Module von verschiedenen HPC-Architekturen
und erstellt maschinenlesbare JSON-Ausgaben für Git-Repository.
"""

import subprocess
import json
import re
import os
import argparse
from datetime import datetime
from typing import Dict, List, Tuple


class ModuleCollector:
    def __init__(self):
        self.architectures = ['genoa', 'h200', 'l40s', 'mi300a', 'milan']
        self.categories = {
            'bio': 'Biology Software',
            'chem': 'Chemistry Software', 
            'compiler': 'Compilers',
            'math': 'Mathematics Software',
            'phys': 'Physics Software',
            'tools': 'Development Tools',
            'lib': 'Libraries',
            'data': 'Data Analysis',
            'ai': 'Artificial Intelligence',
            'vis': 'Visualization'
        }
    
    def run_module_command(self, architecture: str) -> str:
        """
        Führt den module avail Befehl für eine spezifische Architektur aus
        """
        try:
            # Lade die entsprechende Architektur
            load_cmd = f"module load arch/{architecture}"
            avail_cmd = "module avail"
            
            # Kombiniere beide Befehle
            full_cmd = f"{load_cmd} && {avail_cmd}"
            
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # module avail gibt Ausgabe über stderr aus
            return result.stderr + result.stdout
            
        except subprocess.TimeoutExpired:
            print(f"Timeout beim Ausführen des Befehls für {architecture}")
            return ""
        except Exception as e:
            print(f"Fehler beim Ausführen des Befehls für {architecture}: {e}")
            return ""
    
    def get_module_spider_data(self, architecture: str) -> Dict[str, str]:
        """
        Führt module spider einmal aus und extrahiert alle Beschreibungen
        """
        try:
            load_cmd = f"module load arch/{architecture}"
            spider_cmd = "module spider"
            
            full_cmd = f"{load_cmd} && {spider_cmd}"
            
            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60  # Spider kann länger dauern
            )
            
            output = result.stdout + result.stderr
            return self.parse_spider_output(output)
            
        except subprocess.TimeoutExpired:
            print(f"Timeout beim Ausführen von module spider für {architecture}")
            return {}
        except Exception as e:
            print(f"Fehler beim Ausführen von module spider für {architecture}: {e}")
            return {}
    
    def parse_spider_output(self, output: str) -> Dict[str, str]:
        """
        Parst die module spider Ausgabe und extrahiert Software-Beschreibungen
        """
        descriptions = {}
        lines = output.split('\n')
        current_software = None
        current_description = []
        
        for line in lines:
            # Erkenne Software-Header (z.B. "  lang/bison:")
            if line.strip() and ':' in line and not line.startswith('    '):
                # Speichere vorherige Beschreibung falls vorhanden
                if current_software and current_description:
                    descriptions[current_software] = ' '.join(current_description).strip()
                
                # Extrahiere Software-Namen (ohne Versionen)
                software_match = re.match(r'\s*(\S+):\s*', line)
                if software_match:
                    current_software = software_match.group(1)
                    current_description = []
                else:
                    current_software = None
                    current_description = []
            
            # Sammle Beschreibungszeilen (beginnen mit 4+ Leerzeichen)
            elif line.startswith('    ') and current_software:
                # Überspringe Versionszeilen (enthalten meist Kommas und Modulnamen)
                if not ('/' in line and ',' in line):
                    desc_line = line.strip()
                    if desc_line:
                        current_description.append(desc_line)
        
        # Speichere letzte Beschreibung
        if current_software and current_description:
            descriptions[current_software] = ' '.join(current_description).strip()
        
        return descriptions
    
    def parse_module_output(self, output: str, architecture: str, spider_descriptions: Dict[str, str]) -> List[Dict]:
        """
        Parst die module avail Ausgabe und extrahiert Modul-Informationen
        """
        modules = []
        current_category = "Unknown"
        
        lines = output.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Erkenne Kategorie-Header (z.B. "Chemistry Software")
            if line.startswith('---') and line.endswith('---'):
                # Extrahiere Kategorie-Namen zwischen den Strichen
                category_match = re.search(r'---+\s*(.+?)\s*---+', line)
                if category_match:
                    current_category = category_match.group(1).strip()
                continue
            
            # Erkenne Module (enthalten Versionsnummern und optional Flags)
            if '/' in line and not line.startswith('-'):
                # Teile die Zeile in einzelne Module auf
                module_entries = re.findall(r'(\S+/\S+(?:\s*\([^)]+\))?)', line)
                
                for entry in module_entries:
                    # Filtere arch/* Module aus
                    clean_entry = re.sub(r'\s*\([^)]+\)$', '', entry.strip())
                    if clean_entry.startswith('arch/'):
                        continue
                    
                    module_info = self.parse_single_module(entry, current_category, architecture, spider_descriptions)
                    if module_info:
                        modules.append(module_info)
        
        return modules
    
    def parse_single_module(self, module_entry: str, category: str, architecture: str, spider_descriptions: Dict[str, str]) -> Dict:
        """
        Parst einen einzelnen Modul-Eintrag
        """
        # Entferne Flags wie (D), (L), (S) am Ende
        clean_entry = re.sub(r'\s*\([^)]+\)$', '', module_entry.strip())
        
        # Teile in Komponenten: kategorie/software/version
        parts = clean_entry.split('/')
        if len(parts) < 2:
            return None
        
        # Bestimme Software und Version basierend auf Anzahl der Parts
        if len(parts) == 2:
            # Format: software/version
            software = parts[0]
            version = parts[1]
            detected_category = self.detect_category(software, category)
            software_key = software
        else:
            # Format: kategorie/software/version (3+ parts)
            category_prefix = parts[0]
            software = parts[1]
            version = '/'.join(parts[2:])  # Rest ist Version (kann weitere Slashes enthalten)
            
            # Verwende Kategorie-Präfix für bessere Kategorisierung
            detected_category = self.detect_category_from_prefix(category_prefix, category)
            software_key = f"{category_prefix}/{software}"
        
        # Hole Beschreibung aus Spider-Daten
        description = spider_descriptions.get(software_key, "")
        
        # Fallback-Beschreibung falls Spider keine Daten hat
        if not description:
            description = f"{software} version {version} for {architecture} architecture"
        
        return {
            'software': software,
            'version': version,
            'category': detected_category,
            'architecture': architecture,
            'description': description,
            'full_name': clean_entry,
            'collected_at': datetime.now().isoformat()
        }
    
    def detect_category(self, software: str, header_category: str) -> str:
        """
        Bestimmt die Kategorie basierend auf Software-Namen und Header
        """
        # Prüfe ob Software mit bekanntem Präfix beginnt
        for prefix, cat_name in self.categories.items():
            if software.startswith(prefix + '/') or software == prefix:
                return cat_name
        
        # Verwende Header-Kategorie falls verfügbar
        if header_category and header_category != "Unknown":
            return header_category
        
        # Fallback-Kategorien basierend auf Software-Namen
        software_lower = software.lower()
        if any(term in software_lower for term in ['gcc', 'intel', 'llvm', 'go']):
            return 'Compilers'
        elif any(term in software_lower for term in ['python', 'r-', 'julia']):
            return 'Programming Languages'
        elif any(term in software_lower for term in ['mpi', 'openmpi', 'cuda']):
            return 'Parallel Computing'
        else:
            return 'Other'
    
    def detect_category_from_prefix(self, category_prefix: str, header_category: str) -> str:
        """
        Bestimmt die Kategorie basierend auf Modul-Präfix (z.B. devel, bio, chem)
        """
        # Direkte Zuordnung von bekannten Präfixen
        prefix_mapping = {
            'devel': 'Development Tools',
            'bio': 'Biology Software',
            'chem': 'Chemistry Software',
            'compiler': 'Compilers',
            'math': 'Mathematics Software',
            'phys': 'Physics Software',
            'tools': 'Development Tools',
            'lib': 'Libraries',
            'data': 'Data Analysis',
            'ai': 'Artificial Intelligence',
            'vis': 'Visualization',
            'lang': 'Programming Languages',
            'mpi': 'Parallel Computing',
            'gpu': 'GPU Computing',
            'system': 'System Tools',
            'numlib': 'Numerical Libraries',
            'toolchain': 'Toolchains'
        }
        
        # Prüfe direkte Zuordnung
        if category_prefix.lower() in prefix_mapping:
            return prefix_mapping[category_prefix.lower()]
        
        # Prüfe ob Präfix in den definierten Kategorien ist
        if category_prefix in self.categories:
            return self.categories[category_prefix]
        
        # Verwende Header-Kategorie falls verfügbar
        if header_category and header_category != "Unknown":
            return header_category
        
        return 'Other'
    
    def collect_all_modules(self) -> Dict[str, List[Dict]]:
        """
        Sammelt Module für alle Architekturen
        """
        all_modules = {}
        
        for arch in self.architectures:
            print(f"Sammle Module für Architektur: {arch}")
            
            # Hole Spider-Daten einmal für diese Architektur
            print(f"  -> Führe module spider aus...")
            spider_descriptions = self.get_module_spider_data(arch)
            print(f"  -> {len(spider_descriptions)} Software-Beschreibungen gefunden")
            
            # Hole module avail Ausgabe
            output = self.run_module_command(arch)
            
            if output:
                modules = self.parse_module_output(output, arch, spider_descriptions)
                all_modules[arch] = modules
                print(f"  -> {len(modules)} Module gefunden")
            else:
                print(f"  -> Keine Module gefunden oder Fehler aufgetreten")
                all_modules[arch] = []
        
        return all_modules
    
    def save_data(self, modules_data: Dict[str, List[Dict]], output_dir: str):
        """
        Speichert die gesammelten Daten in JSON-Dateien
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Speichere Daten pro Architektur
        for arch, modules in modules_data.items():
            arch_file = os.path.join(output_dir, f"modules_{arch}.json")
            with open(arch_file, 'w', encoding='utf-8') as f:
                json.dump(modules, f, indent=2, ensure_ascii=False)
            print(f"Daten für {arch} gespeichert: {arch_file}")
        
        # Erstelle kombinierte Datei
        all_modules = []
        for modules in modules_data.values():
            all_modules.extend(modules)
        
        combined_file = os.path.join(output_dir, "modules_all.json")
        with open(combined_file, 'w', encoding='utf-8') as f:
            json.dump(all_modules, f, indent=2, ensure_ascii=False)
        print(f"Kombinierte Daten gespeichert: {combined_file}")
        
        # Erstelle Metadaten
        metadata = {
            'collection_date': datetime.now().isoformat(),
            'architectures': list(modules_data.keys()),
            'total_modules': len(all_modules),
            'modules_per_arch': {arch: len(modules) for arch, modules in modules_data.items()}
        }
        
        metadata_file = os.path.join(output_dir, "metadata.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"Metadaten gespeichert: {metadata_file}")


def main():
    parser = argparse.ArgumentParser(description='HPC Module Collector')
    parser.add_argument('--output-dir', '-o', default='./data',
                       help='Ausgabe-Verzeichnis für JSON-Dateien')
    parser.add_argument('--architecture', '-a', 
                       help='Sammle nur für spezifische Architektur')
    
    args = parser.parse_args()
    
    collector = ModuleCollector()
    
    if args.architecture:
        if args.architecture not in collector.architectures:
            print(f"Unbekannte Architektur: {args.architecture}")
            print(f"Verfügbare Architekturen: {', '.join(collector.architectures)}")
            return 1
        
        collector.architectures = [args.architecture]
    
    print("Starte Modul-Sammlung...")
    modules_data = collector.collect_all_modules()
    
    print("\nSpeichere Daten...")
    collector.save_data(modules_data, args.output_dir)
    
    print("\nSammlung abgeschlossen!")
    return 0


if __name__ == "__main__":
    exit(main())