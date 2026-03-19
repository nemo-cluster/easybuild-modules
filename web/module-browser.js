/**
 * bwForCluster NEMO 2 Easybuild Module Browser
 *
 * Features:
 * - Deduplicates modules that are identical across genoa/h200/rtx/mi300a
 * - Groups architecture badges per row
 * - Shows data generation timestamp from metadata.json
 */

// Architectures that share an identical module tree (mirrors collect_modules.py)
const ARCH_GROUPS = {
    genoa: ['genoa', 'h200', 'rtx', 'mi300a'],
    milan: ['milan'],
};

class ModuleBrowser {
    constructor() {
        this.rawModules   = [];   // deduplicated; each entry has .architectures[]
        this.filteredModules = [];
        this.collectionDate = null;
        this.sortColumn   = 0;
        this.sortDirection = 'asc';

        // Base URL for JSON data — trailing slash, no filename
        this.dataBaseUrl = 'https://raw.githubusercontent.com/nemo-cluster/easybuild-modules/main/data';

        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.loadData();
        this.populateFilters();
        this.filterAndDisplay();
    }

    setupEventListeners() {
        document.getElementById('architectureFilter').addEventListener('change', () => this.filterAndDisplay());
        document.getElementById('categoryFilter').addEventListener('change',     () => this.filterAndDisplay());
        document.getElementById('searchInput').addEventListener('input',         () => this.filterAndDisplay());
    }

    // -- data loading -------------------------------------------------------

    async fetchJson(url) {
        const r = await fetch(url);
        if (!r.ok) throw new Error(`HTTP ${r.status} – ${url}`);
        return r.json();
    }

    async loadData() {
        let modules, metadata;
        try {
            [modules, metadata] = await Promise.all([
                this.fetchJson(`${this.dataBaseUrl}/modules_all.json`),
                this.fetchJson(`${this.dataBaseUrl}/metadata.json`).catch(() => null),
            ]);
        } catch (remoteErr) {
            console.warn('Remote data unavailable, using local sample:', remoteErr.message);
            try {
                [modules, metadata] = await Promise.all([
                    this.fetchJson('./sample-data.json'),
                    this.fetchJson('./metadata.json').catch(() => null),
                ]);
            } catch (localErr) {
                this.showError(`Cannot load data: ${localErr.message}`);
                return;
            }
        }

        if (metadata?.collection_date) {
            this.collectionDate = metadata.collection_date;
            this.showCollectionDate(metadata.collection_date);
        }

        this.rawModules = this.deduplicateModules(modules);

        document.getElementById('loadingDisplay').style.display = 'none';
        document.getElementById('moduleTable').style.display = 'table';
    }

    /**
     * Merge entries with the same (software, version, category) into one row,
     * collecting all architectures into an array.
     */
    deduplicateModules(modules) {
        const map = new Map();
        for (const m of modules) {
            const key = `${m.software}|||${m.version}|||${m.category}`;
            if (!map.has(key)) {
                map.set(key, { ...m, architectures: [m.architecture] });
            } else {
                const entry = map.get(key);
                if (!entry.architectures.includes(m.architecture)) {
                    entry.architectures.push(m.architecture);
                }
            }
        }
        // Sort architectures within each entry alphabetically
        for (const entry of map.values()) {
            entry.architectures.sort();
        }
        return Array.from(map.values());
    }

    showCollectionDate(isoDate) {
        const d = new Date(isoDate);
        const formatted = d.toLocaleString('de-DE', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit',
        });
        const el = document.getElementById('collectionDate');
        if (el) el.textContent = `Datenstand: ${formatted} Uhr`;
    }

    // -- filters ------------------------------------------------------------

    populateFilters() {
        // Collect all individual architectures present after dedup
        const archSet = new Set(this.rawModules.flatMap(m => m.architectures));
        const architectures = [...archSet].sort();
        const categories = [...new Set(this.rawModules.map(m => m.category))].sort();

        const archSelect = document.getElementById('architectureFilter');
        archSelect.innerHTML = '<option value="">Alle Architekturen</option>';
        for (const arch of architectures) {
            const opt = document.createElement('option');
            opt.value = arch;
            opt.textContent = arch;
            archSelect.appendChild(opt);
        }

        const catSelect = document.getElementById('categoryFilter');
        catSelect.innerHTML = '<option value="">Alle Kategorien</option>';
        for (const cat of categories) {
            const opt = document.createElement('option');
            opt.value = cat;
            opt.textContent = cat;
            catSelect.appendChild(opt);
        }
    }

    filterAndDisplay() {
        const archFilter  = document.getElementById('architectureFilter').value;
        const catFilter   = document.getElementById('categoryFilter').value;
        const searchTerm  = document.getElementById('searchInput').value.toLowerCase();

        this.filteredModules = this.rawModules.filter(m => {
            // A module matches the arch filter if any of its architectures match
            const matchesArch   = !archFilter  || m.architectures.includes(archFilter);
            const matchesCat    = !catFilter   || m.category === catFilter;
            const matchesSearch = !searchTerm  ||
                m.software.toLowerCase().includes(searchTerm) ||
                m.description.toLowerCase().includes(searchTerm);
            return matchesArch && matchesCat && matchesSearch;
        });

        this.sortModules();
        this.displayModules();
        this.updateStats();
    }

    // -- sorting ------------------------------------------------------------

    sortModules() {
        const direction = this.sortDirection === 'asc' ? 1 : -1;
        // column 3 = architecture: sort by first arch in sorted array
        const getVal = (m, col) => {
            if (col === 3) return m.architectures[0] || '';
            return (['software', 'version', 'category', '', 'description'][col] &&
                    m[['software', 'version', 'category', '', 'description'][col]]) || '';
        };

        this.filteredModules.sort((a, b) => {
            const aVal = getVal(a, this.sortColumn).toLowerCase();
            const bVal = getVal(b, this.sortColumn).toLowerCase();
            if (aVal < bVal) return -1 * direction;
            if (aVal > bVal) return  1 * direction;
            return 0;
        });
    }

    // -- display ------------------------------------------------------------

    archBadges(architectures) {
        return architectures
            .map(a => `<span class="architecture-tag arch-${this.escapeHtml(a)}">${this.escapeHtml(a)}</span>`)
            .join(' ');
    }

    displayModules() {
        const tbody     = document.getElementById('moduleTableBody');
        const noResults = document.getElementById('noResultsDisplay');

        if (this.filteredModules.length === 0) {
            tbody.innerHTML = '';
            noResults.style.display = 'block';
            return;
        }
        noResults.style.display = 'none';

        tbody.innerHTML = this.filteredModules.map(m => `
            <tr>
                <td><strong>${this.escapeHtml(m.software)}</strong></td>
                <td><code>${this.escapeHtml(m.version)}</code></td>
                <td><span class="category-tag">${this.escapeHtml(m.category)}</span></td>
                <td class="arch-cell">${this.archBadges(m.architectures)}</td>
                <td>${this.escapeHtml(m.description)}</td>
            </tr>
        `).join('');
    }

    updateStats() {
        const total    = this.rawModules.length;
        const filtered = this.filteredModules.length;
        const archSet  = new Set(this.filteredModules.flatMap(m => m.architectures));

        let text = `${filtered} von ${total} Module angezeigt | Architekturen: ${archSet.size}`;
        if (this.collectionDate) {
            const d = new Date(this.collectionDate);
            text += ` | Stand: ${d.toLocaleDateString('de-DE')}`;
        }
        document.getElementById('statsDisplay').textContent = text;
    }

    showError(message) {
        document.getElementById('errorDisplay').innerHTML =
            `<div class="error">${this.escapeHtml(message)}</div>`;
        document.getElementById('loadingDisplay').style.display = 'none';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }
}

// Global sort handler
function sortTable(column) {
    const b = window.moduleBrowser;
    b.sortDirection = (b.sortColumn === column && b.sortDirection === 'asc') ? 'desc' : 'asc';
    b.sortColumn = column;
    b.filterAndDisplay();
}

document.addEventListener('DOMContentLoaded', () => {
    window.moduleBrowser = new ModuleBrowser();
});

if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('./sw.js')
            .catch(e => console.warn('SW registration failed:', e));
    });
}