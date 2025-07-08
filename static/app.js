
class PlaygroundUI {
    constructor() {
        this.files = [];
        this.filteredFiles = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadData();
    }

    setupEventListeners() {
        document.getElementById('refresh-btn').addEventListener('click', () => this.loadData());
        document.getElementById('organize-time-btn').addEventListener('click', () => this.organizeFiles('time'));
        document.getElementById('organize-theme-btn').addEventListener('click', () => this.organizeFiles('theme'));
        document.getElementById('organize-both-btn').addEventListener('click', () => this.organizeFiles('both'));
        
        document.getElementById('search-filter').addEventListener('input', (e) => this.filterFiles());
        document.getElementById('category-filter').addEventListener('change', (e) => this.filterFiles());
        document.getElementById('theme-filter').addEventListener('change', (e) => this.filterFiles());
    }

    async loadData() {
        try {
            console.log('Loading data...');
            document.getElementById('loading').style.display = 'block';
            document.getElementById('files-grid').innerHTML = '';
            
            console.log('Fetching files and stats...');
            const [filesResponse, statsResponse] = await Promise.all([
                fetch('/api/files').then(r => {
                    console.log('Files response status:', r.status);
                    if (!r.ok) throw new Error(`Files API failed: ${r.status} ${r.statusText}`);
                    return r;
                }),
                fetch('/api/stats').then(r => {
                    console.log('Stats response status:', r.status);
                    if (!r.ok) throw new Error(`Stats API failed: ${r.status} ${r.statusText}`);
                    return r;
                })
            ]);
            
            console.log('Parsing JSON responses...');
            const filesData = await filesResponse.json();
            const statsData = await statsResponse.json();
            
            console.log('Files data:', filesData);
            console.log('Stats data:', statsData);
            
            this.files = filesData.files || [];
            this.filteredFiles = [...this.files];
            
            this.updateStats(statsData);
            this.updatePlaygroundPath(filesData.playground_path || 'Unknown');
            this.renderFiles();
            
            document.getElementById('loading').style.display = 'none';
            console.log('Data loaded successfully');
        } catch (error) {
            console.error('Error loading data:', error);
            document.getElementById('loading').innerHTML = `
                <div style="color: #e74c3c;">
                    <h3>Error Loading Data</h3>
                    <p>${error.message}</p>
                    <button onclick="location.reload()" class="btn">Reload Page</button>
                </div>
            `;
        }
    }

    updateStats(stats) {
        document.getElementById('total-files').textContent = stats.total_files;
        document.getElementById('total-size').textContent = stats.total_size_gb + ' GB';
        
        const categories = stats.categories || {};
        document.getElementById('current-count').textContent = categories.current?.count || 0;
        document.getElementById('recent-count').textContent = categories.recent?.count || 0;
        document.getElementById('old-count').textContent = categories.old?.count || 0;
        document.getElementById('archive-count').textContent = categories.archive?.count || 0;
    }

    updatePlaygroundPath(path) {
        document.getElementById('playground-path').textContent = path;
    }

    filterFiles() {
        const searchTerm = document.getElementById('search-filter').value.toLowerCase();
        const categoryFilter = document.getElementById('category-filter').value;
        const themeFilter = document.getElementById('theme-filter').value;

        this.filteredFiles = this.files.filter(file => {
            const matchesSearch = file.name.toLowerCase().includes(searchTerm);
            const matchesCategory = !categoryFilter || file.time_category === categoryFilter;
            const matchesTheme = !themeFilter || file.theme === themeFilter;
            
            return matchesSearch && matchesCategory && matchesTheme;
        });

        this.renderFiles();
    }

    renderFiles() {
        const grid = document.getElementById('files-grid');
        
        if (this.filteredFiles.length === 0) {
            grid.innerHTML = '<div style="text-align: center; color: #7f8c8d; grid-column: 1 / -1;">No files found matching your criteria</div>';
            return;
        }

        grid.innerHTML = this.filteredFiles.map(file => `
            <div class="file-card">
                <div class="file-header">
                    <div class="file-name">${file.name}</div>
                    <div class="file-badges">
                        <span class="badge ${file.time_category}">${file.time_category}</span>
                        <span class="badge ${file.theme}">${file.theme}</span>
                    </div>
                </div>
                <div class="file-info">
                    <div class="file-info-item">
                        <span>Size:</span>
                        <strong>${file.size_mb} MB</strong>
                    </div>
                    <div class="file-info-item">
                        <span>Last Used:</span>
                        <strong>${file.last_used}</strong>
                    </div>
                    <div class="file-info-item">
                        <span>Days Ago:</span>
                        <strong>${file.days_since_used}</strong>
                    </div>
                    <div class="file-info-item">
                        <span>Path:</span>
                        <strong title="${file.path}">${this.truncatePath(file.path)}</strong>
                    </div>
                </div>
            </div>
        `).join('');
    }

    truncatePath(path) {
        if (path.length <= 40) return path;
        return '...' + path.slice(-37);
    }

    async organizeFiles(mode) {
        try {
            console.log('Fetching preview for mode:', mode);
            const response = await fetch('/api/organize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    mode: mode
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            console.log('Organize result:', result);
            
            if (result.success) {
                const actionsList = result.actions.slice(0, 10).join('\n');
                const moreText = result.actions.length > 10 ? `\n... and ${result.actions.length - 10} more actions` : '';
                
                alert(`Preview of ${mode} organization:\n\n${actionsList}${moreText}\n\nNote: This is read-only mode - no files were changed.`);
            } else {
                alert('Preview failed: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error previewing organization:', error);
            alert('Error previewing organization: ' + error.message);
        }
    }
}

// Initialize the UI when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new PlaygroundUI();
});
