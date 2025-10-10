/**
 * HPC Module Browser JavaScript
 * Verwaltet das Laden, Filtern und Anzeigen von Modul-Daten
 */

class ModuleBrowser {
    constructor() {
        this.modules = [];
        this.filteredModules = [];
        this.sortColumn = 0;
        this.sortDirection = 'asc';
        
        // Git Repository URL für Daten
        this.dataUrl = 'https://raw.githubusercontent.com/nemo-cluster/easybuild-modules/main/data/modules_all.json';
        
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        await this.loadData();
        this.populateFilters();
        this.filterAndDisplay();
    }
    
    setupEventListeners() {
        const architectureFilter = document.getElementById('architectureFilter');
        const categoryFilter = document.getElementById('categoryFilter');
        const searchInput = document.getElementById('searchInput');
        
        architectureFilter.addEventListener('change', () => this.filterAndDisplay());
        categoryFilter.addEventListener('change', () => this.filterAndDisplay());
        searchInput.addEventListener('input', () => this.filterAndDisplay());
    }
    
    async loadData() {
        try {
            // Versuche Daten vom Git Repository zu laden
            let response;
            try {
                response = await fetch(this.dataUrl);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
            } catch (gitError) {
                // Fallback: Lade lokale Testdaten
                console.warn('Kann nicht vom Git Repository laden, verwende lokale Testdaten:', gitError.message);
                response = await fetch('./sample-data.json');
                if (!response.ok) {
                    throw new Error('Kann auch keine lokalen Testdaten laden');
                }
            }
            
            this.modules = await response.json();
            
            document.getElementById('loadingDisplay').style.display = 'none';
            document.getElementById('moduleTable').style.display = 'table';
            
        } catch (error) {
            this.showError(`Fehler beim Laden der Daten: ${error.message}`);
            // Erstelle Beispiel-Daten für Demo
            this.createSampleData();
        }
    }
    
    createSampleData() {
        console.log('Erstelle Beispiel-Daten für Demo');
        this.modules = [
            {
                software: 'gromacs',
                version: '2023.3',
                category: 'Biology Software',
                architecture: 'genoa',
                description: 'Molecular dynamics simulation package'
            },
            {
                software: 'gcc',
                version: '13.3.0',
                category: 'Compilers',
                architecture: 'genoa',
                description: 'GNU Compiler Collection'
            },
            {
                software: 'lammps',
                version: '2aug2023_update2',
                category: 'Chemistry Software',
                architecture: 'h200',
                description: 'Large-scale Atomic/Molecular Massively Parallel Simulator'
            },
            {
                software: 'intel-compilers',
                version: '2024.2.0',
                category: 'Compilers',
                architecture: 'milan',
                description: 'Intel C/C++ and Fortran compilers'
            },
            {
                software: 'orca',
                version: '6.0.1',
                category: 'Chemistry Software',
                architecture: 'l40s',
                description: 'Quantum chemistry program package'
            }
        ];
        
        document.getElementById('loadingDisplay').style.display = 'none';
        document.getElementById('moduleTable').style.display = 'table';
    }
    
    populateFilters() {
        const architectures = [...new Set(this.modules.map(m => m.architecture))].sort();
        const categories = [...new Set(this.modules.map(m => m.category))].sort();
        
        const archSelect = document.getElementById('architectureFilter');
        const catSelect = document.getElementById('categoryFilter');
        
        // Leere bestehende Optionen (außer "Alle")
        archSelect.innerHTML = '<option value="">Alle Architekturen</option>';
        catSelect.innerHTML = '<option value="">Alle Kategorien</option>';
        
        // Füge Architektur-Optionen hinzu
        architectures.forEach(arch => {
            const option = document.createElement('option');
            option.value = arch;
            option.textContent = arch;
            archSelect.appendChild(option);
        });
        
        // Füge Kategorie-Optionen hinzu
        categories.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat;
            option.textContent = cat;
            catSelect.appendChild(option);
        });
    }
    
    filterAndDisplay() {
        const archFilter = document.getElementById('architectureFilter').value;
        const catFilter = document.getElementById('categoryFilter').value;
        const searchTerm = document.getElementById('searchInput').value.toLowerCase();
        
        this.filteredModules = this.modules.filter(module => {
            const matchesArch = !archFilter || module.architecture === archFilter;
            const matchesCat = !catFilter || module.category === catFilter;
            const matchesSearch = !searchTerm || 
                module.software.toLowerCase().includes(searchTerm) ||
                module.description.toLowerCase().includes(searchTerm);
            
            return matchesArch && matchesCat && matchesSearch;
        });
        
        this.sortModules();
        this.displayModules();
        this.updateStats();
    }
    
    sortModules() {
        const direction = this.sortDirection === 'asc' ? 1 : -1;
        const columns = ['software', 'version', 'category', 'architecture', 'description'];
        const sortKey = columns[this.sortColumn];
        
        this.filteredModules.sort((a, b) => {
            const aVal = a[sortKey].toLowerCase();
            const bVal = b[sortKey].toLowerCase();
            
            if (aVal < bVal) return -1 * direction;
            if (aVal > bVal) return 1 * direction;
            return 0;
        });
    }
    
    displayModules() {
        const tbody = document.getElementById('moduleTableBody');
        const noResults = document.getElementById('noResultsDisplay');
        
        if (this.filteredModules.length === 0) {
            tbody.innerHTML = '';
            noResults.style.display = 'block';
            return;
        }
        
        noResults.style.display = 'none';
        
        tbody.innerHTML = this.filteredModules.map(module => `
            <tr>
                <td><strong>${this.escapeHtml(module.software)}</strong></td>
                <td>${this.escapeHtml(module.version)}</td>
                <td><span class="category-tag">${this.escapeHtml(module.category)}</span></td>
                <td><span class="architecture-tag arch-${module.architecture}">${this.escapeHtml(module.architecture)}</span></td>
                <td>${this.escapeHtml(module.description)}</td>
            </tr>
        `).join('');
    }
    
    updateStats() {
        const total = this.modules.length;
        const filtered = this.filteredModules.length;
        const architectures = [...new Set(this.filteredModules.map(m => m.architecture))];
        
        const statsText = `${filtered} von ${total} Modulen angezeigt | Architekturen: ${architectures.length}`;
        document.getElementById('statsDisplay').textContent = statsText;
    }
    
    showError(message) {
        const errorDiv = document.getElementById('errorDisplay');
        errorDiv.innerHTML = `<div class="error">${this.escapeHtml(message)}</div>`;
        
        document.getElementById('loadingDisplay').style.display = 'none';
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Globale Funktion für Tabellen-Sortierung
function sortTable(column) {
    const browser = window.moduleBrowser;
    if (browser.sortColumn === column) {
        browser.sortDirection = browser.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        browser.sortColumn = column;
        browser.sortDirection = 'asc';
    }
    browser.filterAndDisplay();
}

// Initialisiere die Anwendung
document.addEventListener('DOMContentLoaded', () => {
    window.moduleBrowser = new ModuleBrowser();
});

// Service Worker für Offline-Funktionalität (optional)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('./sw.js')
            .then(registration => console.log('SW registered'))
            .catch(registrationError => console.log('SW registration failed'));
    });
}