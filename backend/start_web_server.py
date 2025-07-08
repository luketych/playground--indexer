#!/usr/bin/env python3
"""
Web UI for Playground Organizer
"""

import os
import sys
import logging
import traceback
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the main playground organizer module
sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.src.playground_organizer.playground_organizer import PlaygroundOrganizer

app = FastAPI(
    title=os.getenv("APP_TITLE", "Playground Organizer"), 
    description=os.getenv("APP_DESCRIPTION", "Web UI for file organization")
)

# Setup static files and templates
static_dir = Path(__file__).parent.parent / "frontend" / "static"
templates_dir = Path(__file__).parent.parent / "frontend" / "templates"

# Create directories if they don't exist
static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# Global organizer instance
organizer = None

def get_organizer():
    """Get or create organizer instance"""
    global organizer
    if organizer is None:
        # Point to the actual playground directory (parent of __indexer)
        playground_path = Path(__file__).parent.parent.parent
        logger.info(f"Initializing organizer with path: {playground_path}")
        try:
            organizer = PlaygroundOrganizer(playground_path)
            logger.info("Organizer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize organizer: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    return organizer

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/files")
async def get_files():
    """Get all files with their analysis"""
    try:
        logger.info("Starting /api/files endpoint")
        org = get_organizer()
        logger.info(f"Got organizer instance, playground path: {org.playground_path}")
        
        logger.info("Calling analyze_access_patterns()")
        analysis = org.analyze_access_patterns()
        logger.info(f"Analysis completed, found {sum(len(files) for files in analysis.values())} files")
        
        # Flatten the analysis into a single list with categories
        files = []
        for category, file_list in analysis.items():
            logger.info(f"Processing category '{category}' with {len(file_list)} files")
            for file_info in file_list:
                try:
                    file_path = Path(file_info["path"])
                    file_data = {
                        "name": file_path.name,
                        "path": file_info["path"],
                        "size": file_info["size"],
                        "size_mb": round(file_info["size"] / (1024 * 1024), 2),
                        "last_used": file_info["last_used_date"],
                        "days_since_used": round(file_info["days_since_used"], 1),
                        "time_category": category,
                        "theme": org.detect_theme(file_path),
                        "is_directory": file_path.is_dir(),
                        "file_extension": file_path.suffix.lower() if file_path.is_file() else "",
                        "atime": file_info["atime"],
                        "mtime": file_info["mtime"],
                        "ctime": file_info["ctime"]
                    }
                    files.append(file_data)
                except Exception as file_error:
                    logger.error(f"Error processing file {file_info.get('path', 'unknown')}: {file_error}")
                    continue
        
        logger.info(f"Successfully processed {len(files)} files")
        return JSONResponse({
            "files": files,
            "total_files": len(files),
            "playground_path": str(org.playground_path),
            "categories": {
                "current": len(analysis["current"]),
                "recent": len(analysis["recent"]),
                "old": len(analysis["old"]),
                "archive": len(analysis["archive"])
            }
        })
    except Exception as e:
        logger.error(f"Error in /api/files endpoint: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/themes")
async def get_themes():
    """Get theme statistics"""
    try:
        org = get_organizer()
        analysis = org.analyze_access_patterns()
        
        theme_stats = {}
        for category, file_list in analysis.items():
            for file_info in file_list:
                theme = org.detect_theme(Path(file_info["path"]))
                if theme not in theme_stats:
                    theme_stats[theme] = {"count": 0, "size": 0}
                theme_stats[theme]["count"] += 1
                theme_stats[theme]["size"] += file_info["size"]
        
        # Convert size to MB
        for theme in theme_stats:
            theme_stats[theme]["size_mb"] = round(theme_stats[theme]["size"] / (1024 * 1024), 2)
        
        return JSONResponse(theme_stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/organize")
async def organize_files(request: Request):
    """Preview organization without making file system changes - READ ONLY"""
    try:
        logger.info("Starting /api/organize endpoint")
        data = await request.json()
        mode = data.get("mode", "time")  # time, theme, or both
        logger.info(f"Organization mode: {mode}")
        
        org = get_organizer()
        logger.info(f"Got organizer, config keys: {list(org.config.keys())}")
        actions = []
        
        # ALWAYS run in dry-run mode - web UI is READ ONLY
        if mode == "time":
            logger.info("Calling organize_with_symlinks(dry_run=True)")
            actions = org.organize_with_symlinks(dry_run=True)
        elif mode == "theme":
            logger.info("Calling organize_by_theme(dry_run=True)")
            actions = org.organize_by_theme(dry_run=True)
        elif mode == "both":
            logger.info("Calling both organize_with_symlinks and organize_by_theme")
            actions.extend(org.organize_with_symlinks(dry_run=True))
            actions.extend(org.organize_by_theme(dry_run=True))
        
        logger.info(f"Generated {len(actions)} actions")
        return JSONResponse({
            "success": True,
            "actions": actions,
            "mode": mode,
            "executed": False,  # Never execute from web UI
            "total_actions": len(actions),
            "note": "Web UI is read-only - no files were moved or changed"
        })
    except Exception as e:
        logger.error(f"Error in /api/organize endpoint: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    try:
        org = get_organizer()
        return JSONResponse({
            "config": org.config,
            "playground_path": str(org.playground_path),
            "thresholds": org.thresholds
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config")
async def update_config(request: Request):
    """Update configuration"""
    try:
        data = await request.json()
        org = get_organizer()
        
        # Update configuration
        if "thresholds" in data:
            org.thresholds.update(data["thresholds"])
        
        if "config" in data:
            org.config.update(data["config"])
        
        # Save configuration
        org.save_config()
        
        return JSONResponse({"success": True, "message": "Configuration updated"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    """Get overall statistics"""
    try:
        org = get_organizer()
        analysis = org.analyze_access_patterns()
        
        total_files = sum(len(files) for files in analysis.values())
        total_size = sum(
            sum(f["size"] for f in files) 
            for files in analysis.values()
        )
        
        stats = {
            "total_files": total_files,
            "total_size": total_size,
            "total_size_gb": round(total_size / (1024**3), 2),
            "categories": {},
            "playground_path": str(org.playground_path),
            "last_updated": datetime.now().isoformat()
        }
        
        for category, files in analysis.items():
            if files:
                category_size = sum(f["size"] for f in files)
                avg_days = sum(f["days_since_used"] for f in files) / len(files)
                stats["categories"][category] = {
                    "count": len(files),
                    "size": category_size,
                    "size_mb": round(category_size / (1024**2), 2),
                    "avg_days": round(avg_days, 1)
                }
        
        return JSONResponse(stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def create_templates():
    """Create HTML templates"""
    index_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Playground Organizer</title>
    <link href="/static/style.css" rel="stylesheet">
</head>
<body>
    <div class="container">
        <header>
            <h1>🗂️ Playground Organizer</h1>
            <p id="playground-path">Loading...</p>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Files</h3>
                <span id="total-files">-</span>
            </div>
            <div class="stat-card">
                <h3>Total Size</h3>
                <span id="total-size">-</span>
            </div>
            <div class="stat-card current">
                <h3>🟢 Current</h3>
                <span id="current-count">-</span>
            </div>
            <div class="stat-card recent">
                <h3>🟡 Recent</h3>
                <span id="recent-count">-</span>
            </div>
            <div class="stat-card old">
                <h3>🟠 Old</h3>
                <span id="old-count">-</span>
            </div>
            <div class="stat-card archive">
                <h3>🔴 Archive</h3>
                <span id="archive-count">-</span>
            </div>
        </div>

        <div class="controls">
            <button id="refresh-btn" class="btn">🔄 Refresh</button>
            <button id="organize-time-btn" class="btn">📅 Preview Time Organization</button>
            <button id="organize-theme-btn" class="btn">🏷️ Preview Theme Organization</button>
            <button id="organize-both-btn" class="btn">📊 Preview Both</button>
        </div>
        
        <div class="info-banner">
            ℹ️ <strong>Read-Only Mode:</strong> This web UI only displays and analyzes your files. No files are moved, deleted, or modified.
        </div>

        <div class="filter-controls">
            <input type="text" id="search-filter" placeholder="Search files..." />
            <select id="category-filter">
                <option value="">All Categories</option>
                <option value="current">Current</option>
                <option value="recent">Recent</option>
                <option value="old">Old</option>
                <option value="archive">Archive</option>
            </select>
            <select id="theme-filter">
                <option value="">All Themes</option>
                <option value="ai">AI</option>
                <option value="productivity">Productivity</option>
                <option value="stocks">Stocks</option>
                <option value="development">Development</option>
                <option value="data">Data</option>
                <option value="media">Media</option>
                <option value="tools">Tools</option>
                <option value="learning">Learning</option>
                <option value="misc">Misc</option>
            </select>
        </div>

        <div class="files-container">
            <div id="loading">Loading files...</div>
            <div id="files-grid" class="files-grid"></div>
        </div>
    </div>

    <script src="/static/app.js"></script>
</body>
</html>
"""
    
    (templates_dir / "index.html").write_text(index_html)

def create_static_files():
    """Create CSS and JS files"""
    
    css_content = """
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background-color: #f5f5f5;
    color: #333;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

header {
    text-align: center;
    margin-bottom: 30px;
}

header h1 {
    font-size: 2.5em;
    margin-bottom: 10px;
    color: #2c3e50;
}

#playground-path {
    color: #7f8c8d;
    font-size: 0.9em;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.stat-card {
    background: white;
    padding: 20px;
    border-radius: 10px;
    text-align: center;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    transition: transform 0.2s;
}

.stat-card:hover {
    transform: translateY(-2px);
}

.stat-card h3 {
    font-size: 0.9em;
    margin-bottom: 10px;
    color: #7f8c8d;
}

.stat-card span {
    font-size: 1.8em;
    font-weight: bold;
    color: #2c3e50;
}

.stat-card.current span { color: #27ae60; }
.stat-card.recent span { color: #f39c12; }
.stat-card.old span { color: #e67e22; }
.stat-card.archive span { color: #e74c3c; }

.controls {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    justify-content: center;
    flex-wrap: wrap;
}

.btn {
    padding: 10px 20px;
    border: none;
    border-radius: 5px;
    background: #3498db;
    color: white;
    cursor: pointer;
    font-size: 14px;
    transition: background-color 0.2s;
}

.btn:hover {
    background: #2980b9;
}

.filter-controls {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    justify-content: center;
    flex-wrap: wrap;
}

.filter-controls input, .filter-controls select {
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 5px;
    font-size: 14px;
}

#loading {
    text-align: center;
    padding: 40px;
    color: #7f8c8d;
    font-size: 1.2em;
}

.files-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
}

.file-card {
    background: white;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    transition: transform 0.2s;
}

.file-card:hover {
    transform: translateY(-2px);
}

.file-card.clickable {
    cursor: pointer;
    border: 2px solid transparent;
    transition: all 0.2s ease;
}

.file-card.clickable:hover {
    border-color: #3498db;
    transform: translateY(-2px);
}

.file-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 15px;
}

.file-name {
    font-weight: bold;
    font-size: 1.1em;
    color: #2c3e50;
    word-break: break-all;
}

.file-badges {
    display: flex;
    gap: 5px;
    flex-shrink: 0;
}

.badge {
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.8em;
    font-weight: bold;
    color: white;
}

.badge.current { background: #27ae60; }
.badge.recent { background: #f39c12; }
.badge.old { background: #e67e22; }
.badge.archive { background: #e74c3c; }

.badge.ai { background: #9b59b6; }
.badge.productivity { background: #1abc9c; }
.badge.stocks { background: #34495e; }
.badge.development { background: #2ecc71; }
.badge.data { background: #3498db; }
.badge.media { background: #e91e63; }
.badge.tools { background: #95a5a6; }
.badge.learning { background: #ff9800; }
.badge.misc { background: #bdc3c7; }

.info-banner {
    background: #e8f4fd;
    border: 1px solid #bee5eb;
    color: #0c5460;
    padding: 15px;
    border-radius: 5px;
    margin-bottom: 20px;
    text-align: center;
    font-size: 0.9em;
}

.file-info {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    font-size: 0.9em;
    color: #7f8c8d;
}

.file-info-item {
    display: flex;
    justify-content: space-between;
}

.file-info-item strong {
    color: #2c3e50;
}

@media (max-width: 768px) {
    .container {
        padding: 10px;
    }
    
    .stats-grid {
        grid-template-columns: repeat(2, 1fr);
    }
    
    .files-grid {
        grid-template-columns: 1fr;
    }
    
    .controls {
        flex-direction: column;
        align-items: center;
    }
    
    .filter-controls {
        flex-direction: column;
        align-items: center;
    }
}
"""
    
    js_content = """
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
            <div class="file-card clickable" onclick="window.openDirectory('${file.path}')">
                <div class="file-header">
                    <div class="file-name">${this.getFileIcon(file)} ${file.name}</div>
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

    getFileIcon(file) {
        if (file.is_directory) {
            return '📁';
        }
        
        // File icons based on extension
        const ext = file.file_extension;
        if (['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.go', '.rs', '.rb', '.php'].includes(ext)) {
            return '💻';
        } else if (['.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico'].includes(ext)) {
            return '🖼️';
        } else if (['.mp4', '.avi', '.mov', '.mkv', '.webm'].includes(ext)) {
            return '🎬';
        } else if (['.mp3', '.wav', '.flac', '.ogg'].includes(ext)) {
            return '🎵';
        } else if (['.pdf', '.doc', '.docx'].includes(ext)) {
            return '📄';
        } else if (['.txt', '.md', '.readme'].includes(ext)) {
            return '📝';
        } else if (['.json', '.yaml', '.yml', '.xml'].includes(ext) || 
                   file.name.includes('config') || file.name.includes('.env') || 
                   ['.gitignore', '.npmignore', '.dockerignore', '.prettierrc', '.eslintrc'].includes(file.name)) {
            return '⚙️';
        } else if (['.sql', '.db', '.sqlite'].includes(ext)) {
            return '🗄️';
        } else if (['.csv', '.xlsx', '.xls'].includes(ext)) {
            return '📊';
        } else if (['.zip', '.tar', '.gz', '.rar', '.7z'].includes(ext)) {
            return '📦';
        } else {
            return '📄';
        }
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
                const actionsList = result.actions.slice(0, 10).join('\\n');
                const moreText = result.actions.length > 10 ? `\\n... and ${result.actions.length - 10} more actions` : '';
                
                alert(`Preview of ${mode} organization:\\n\\n${actionsList}${moreText}\\n\\nNote: This is read-only mode - no files were changed.`);
            } else {
                alert('Preview failed: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error previewing organization:', error);
            alert('Error previewing organization: ' + error.message);
        }
    }
}

// Global function to open directories in Finder/Explorer
window.openDirectory = function(path) {
    // Show an info dialog since we can't actually open directories from web
    alert(`Directory: ${path}\\n\\nThis is a read-only web interface. To open this directory, use your file manager or terminal:\\n\\nTerminal: cd "${path}"\\nFinder: open "${path}"`);
};

// Initialize the UI when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new PlaygroundUI();
});
"""
    
    (static_dir / "style.css").write_text(css_content)
    (static_dir / "app.js").write_text(js_content)

def main():
    """Main function to run the web UI"""
    # Create necessary files
    create_templates()
    create_static_files()
    
    # Get configuration from environment variables
    host = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_SERVER_PORT", "8000"))
    reload = os.getenv("WEB_SERVER_RELOAD", "true").lower() == "true"
    log_level = os.getenv("WEB_SERVER_LOG_LEVEL", "info")
    
    # Configure logging level for playground organizer
    organizer_log_level = os.getenv("ORGANIZER_LOG_LEVEL", "INFO")
    logging.getLogger("backend.src.playground_organizer.playground_organizer").setLevel(organizer_log_level)
    
    print("🚀 Starting Playground Organizer Web UI...")
    print(f"📁 Web interface will be available at: http://localhost:{port}")
    print("🔄 Press Ctrl+C to stop the server")
    print(f"🔧 Log level: {log_level}, Organizer log level: {organizer_log_level}")
    
    # Run the FastAPI server
    uvicorn.run(
        "backend.start_web_server:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level
    )

if __name__ == "__main__":
    main()