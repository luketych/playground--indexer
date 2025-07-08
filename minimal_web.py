#!/usr/bin/env python3
"""
Minimal Web Server for Testing
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import urllib.parse
from pathlib import Path
import time
import subprocess
from datetime import datetime

class PlaygroundHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.serve_index()
        elif self.path == '/explorer':
            self.serve_explorer()
        elif self.path == '/api/files':
            self.serve_files_api()
        elif self.path == '/api/stats':
            self.serve_stats_api()
        elif self.path.startswith('/api/browse'):
            self.serve_browse_api()
        elif self.path.startswith('/static/'):
            self.serve_static()
        else:
            self.send_error(404)
    
    def do_POST(self):
        if self.path == '/api/organize':
            self.serve_organize_api()
        else:
            self.send_error(404)
    
    def serve_index(self):
        html_file = Path('templates/index.html')
        if html_file.exists():
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html_file.read_bytes())
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<h1>Playground Organizer</h1><p>Templates not found</p>')
    
    def serve_static(self):
        file_path = Path(self.path[1:])  # Remove leading /
        if file_path.exists():
            self.send_response(200)
            if file_path.suffix == '.css':
                self.send_header('Content-type', 'text/css')
            elif file_path.suffix == '.js':
                self.send_header('Content-type', 'application/javascript')
            else:
                self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(file_path.read_bytes())
        else:
            self.send_error(404)
    
    def serve_explorer(self):
        """Serve the file explorer page"""
        html_content = self.get_explorer_html()
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_content.encode())
    
    def serve_browse_api(self):
        """API for browsing directory contents"""
        try:
            # Parse the path from the URL
            import urllib.parse
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            # Get the path parameter
            browse_path = query_params.get('path', [''])[0]
            if not browse_path:
                # Default to playground directory
                browse_path = str(Path.home() / "Dev" / "_playground")
            
            target_path = Path(browse_path)
            
            # Security check - don't allow browsing outside playground
            playground_base = Path.home() / "Dev" / "_playground"
            try:
                target_path.resolve().relative_to(playground_base.resolve())
            except ValueError:
                # Path is outside playground, restrict to playground
                target_path = playground_base
            
            if not target_path.exists() or not target_path.is_dir():
                raise ValueError(f"Invalid directory: {target_path}")
            
            items = []
            
            # Add parent directory link if not at root
            if target_path != playground_base:
                items.append({
                    "name": "..",
                    "type": "parent",
                    "path": str(target_path.parent),
                    "size": 0,
                    "modified": "",
                    "is_dir": True
                })
            
            # List directory contents
            for item in sorted(target_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                try:
                    stat = item.stat()
                    
                    # Skip hidden files and system directories
                    if item.name.startswith('.'):
                        continue
                    
                    item_type = "directory" if item.is_dir() else "file"
                    
                    # Get file size
                    if item.is_file():
                        size = stat.st_size
                    else:
                        # For directories, try to get a quick size estimate
                        try:
                            result = subprocess.run(['du', '-s', str(item)], 
                                                  capture_output=True, text=True, timeout=2)
                            if result.returncode == 0:
                                size = int(result.stdout.split()[0]) * 1024  # Convert KB to bytes
                            else:
                                size = 0
                        except:
                            size = 0
                    
                    items.append({
                        "name": item.name,
                        "type": item_type,
                        "path": str(item),
                        "size": size,
                        "size_human": self.format_file_size(size),
                        "modified": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                        "is_dir": item.is_dir(),
                        "extension": item.suffix.lower() if item.is_file() else ""
                    })
                    
                except (OSError, PermissionError):
                    continue
            
            response = {
                "current_path": str(target_path),
                "parent_path": str(target_path.parent) if target_path != playground_base else None,
                "items": items,
                "total_items": len(items)
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_error(500, str(e))
    
    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def get_explorer_html(self):
        """Generate the file explorer HTML"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Explorer - Playground Organizer</title>
    <link href="/static/style.css" rel="stylesheet">
    <style>
        .explorer-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .explorer-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding: 15px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .breadcrumb {
            display: flex;
            align-items: center;
            font-family: monospace;
            background: #f8f9fa;
            padding: 8px 12px;
            border-radius: 5px;
            font-size: 14px;
        }
        
        .breadcrumb-part {
            cursor: pointer;
            color: #007bff;
            text-decoration: underline;
        }
        
        .breadcrumb-part:hover {
            background: #e9ecef;
            padding: 2px 4px;
            border-radius: 3px;
        }
        
        .explorer-controls {
            display: flex;
            gap: 10px;
        }
        
        .view-toggle {
            display: flex;
            background: #f8f9fa;
            border-radius: 5px;
            overflow: hidden;
        }
        
        .view-toggle button {
            padding: 8px 12px;
            border: none;
            background: transparent;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        .view-toggle button.active {
            background: #007bff;
            color: white;
        }
        
        .explorer-content {
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        /* Grid View */
        .grid-view {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            padding: 20px;
        }
        
        .grid-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 15px;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            text-align: center;
        }
        
        .grid-item:hover {
            background: #f8f9fa;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        
        .grid-item.directory {
            border-color: #007bff;
        }
        
        .grid-item-icon {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .grid-item-name {
            font-weight: bold;
            margin-bottom: 5px;
            word-break: break-word;
        }
        
        .grid-item-info {
            font-size: 0.8em;
            color: #6c757d;
        }
        
        /* List View */
        .list-view {
            display: none;
        }
        
        .list-view.active {
            display: block;
        }
        
        .list-header {
            display: grid;
            grid-template-columns: 40px 1fr 100px 120px;
            gap: 15px;
            padding: 15px 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
            font-weight: bold;
            color: #495057;
        }
        
        .list-item {
            display: grid;
            grid-template-columns: 40px 1fr 100px 120px;
            gap: 15px;
            padding: 12px 20px;
            border-bottom: 1px solid #f8f9fa;
            cursor: pointer;
            transition: background-color 0.2s;
            align-items: center;
        }
        
        .list-item:hover {
            background: #f8f9fa;
        }
        
        .list-item.directory {
            background: rgba(0, 123, 255, 0.05);
        }
        
        .list-item-icon {
            font-size: 1.5em;
            text-align: center;
        }
        
        .list-item-name {
            font-weight: 500;
            word-break: break-word;
        }
        
        .list-item-size {
            text-align: right;
            font-family: monospace;
            color: #6c757d;
        }
        
        .list-item-modified {
            font-family: monospace;
            color: #6c757d;
            font-size: 0.9em;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #6c757d;
        }
        
        .nav-links {
            display: flex;
            gap: 15px;
        }
        
        .nav-link {
            color: #007bff;
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 5px;
            transition: background-color 0.2s;
        }
        
        .nav-link:hover {
            background: #e9ecef;
        }
    </style>
</head>
<body>
    <div class="explorer-container">
        <div class="explorer-header">
            <div>
                <h1>📁 File Explorer</h1>
                <div class="breadcrumb" id="breadcrumb">Loading...</div>
            </div>
            <div class="explorer-controls">
                <div class="nav-links">
                    <a href="/" class="nav-link">📊 Dashboard</a>
                    <a href="/explorer" class="nav-link">📁 Explorer</a>
                </div>
                <div class="view-toggle">
                    <button id="grid-view-btn" class="active">⊞ Grid</button>
                    <button id="list-view-btn">☰ List</button>
                </div>
            </div>
        </div>

        <div class="explorer-content">
            <div id="loading" class="loading">Loading directory contents...</div>
            
            <div id="grid-view" class="grid-view" style="display: none;">
                <!-- Grid items will be populated here -->
            </div>
            
            <div id="list-view" class="list-view">
                <div class="list-header">
                    <div></div>
                    <div>Name</div>
                    <div>Size</div>
                    <div>Modified</div>
                </div>
                <div id="list-items">
                    <!-- List items will be populated here -->
                </div>
            </div>
        </div>
    </div>

    <script>
        class FileExplorer {
            constructor() {
                this.currentPath = '';
                this.currentView = 'grid';
                this.items = [];
                this.init();
            }

            init() {
                this.setupEventListeners();
                this.loadDirectory();
            }

            setupEventListeners() {
                document.getElementById('grid-view-btn').addEventListener('click', () => this.setView('grid'));
                document.getElementById('list-view-btn').addEventListener('click', () => this.setView('list'));
            }

            setView(view) {
                this.currentView = view;
                
                // Update button states
                document.getElementById('grid-view-btn').classList.toggle('active', view === 'grid');
                document.getElementById('list-view-btn').classList.toggle('active', view === 'list');
                
                // Show/hide views
                document.getElementById('grid-view').style.display = view === 'grid' ? 'grid' : 'none';
                document.getElementById('list-view').classList.toggle('active', view === 'list');
                
                this.renderItems();
            }

            async loadDirectory(path = '') {
                try {
                    document.getElementById('loading').style.display = 'block';
                    document.getElementById('grid-view').style.display = 'none';
                    document.getElementById('list-view').classList.remove('active');
                    
                    const url = `/api/browse${path ? `?path=${encodeURIComponent(path)}` : ''}`;
                    const response = await fetch(url);
                    
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    this.currentPath = data.current_path;
                    this.items = data.items;
                    
                    this.updateBreadcrumb();
                    this.renderItems();
                    
                    document.getElementById('loading').style.display = 'none';
                    this.setView(this.currentView);
                    
                } catch (error) {
                    console.error('Error loading directory:', error);
                    document.getElementById('loading').innerHTML = `
                        <div style="color: #e74c3c;">
                            <h3>Error Loading Directory</h3>
                            <p>${error.message}</p>
                            <button onclick="location.reload()" class="btn">Reload</button>
                        </div>
                    `;
                }
            }

            updateBreadcrumb() {
                const breadcrumb = document.getElementById('breadcrumb');
                const playgroundBase = this.currentPath.includes('_playground') ? 
                    this.currentPath.substring(0, this.currentPath.indexOf('_playground') + 12) : this.currentPath;
                
                const relativePath = this.currentPath.replace(playgroundBase, '').replace(/^[\\/]/, '');
                const parts = relativePath ? relativePath.split('/') : [];
                
                let html = `<span class="breadcrumb-part" onclick="explorer.loadDirectory('${playgroundBase}')">🏠 playground</span>`;
                
                let currentPath = playgroundBase;
                for (const part of parts) {
                    currentPath += '/' + part;
                    html += ` / <span class="breadcrumb-part" onclick="explorer.loadDirectory('${currentPath}')">${part}</span>`;
                }
                
                breadcrumb.innerHTML = html;
            }

            renderItems() {
                if (this.currentView === 'grid') {
                    this.renderGridView();
                } else {
                    this.renderListView();
                }
            }

            renderGridView() {
                const container = document.getElementById('grid-view');
                
                container.innerHTML = this.items.map(item => `
                    <div class="grid-item ${item.type}" onclick="explorer.handleItemClick('${item.path}', ${item.is_dir})">
                        <div class="grid-item-icon">${this.getItemIcon(item)}</div>
                        <div class="grid-item-name">${item.name}</div>
                        <div class="grid-item-info">
                            ${item.size_human || ''}<br>
                            ${item.modified || ''}
                        </div>
                    </div>
                `).join('');
            }

            renderListView() {
                const container = document.getElementById('list-items');
                
                container.innerHTML = this.items.map(item => `
                    <div class="list-item ${item.type}" onclick="explorer.handleItemClick('${item.path}', ${item.is_dir})">
                        <div class="list-item-icon">${this.getItemIcon(item)}</div>
                        <div class="list-item-name">${item.name}</div>
                        <div class="list-item-size">${item.size_human || ''}</div>
                        <div class="list-item-modified">${item.modified || ''}</div>
                    </div>
                `).join('');
            }

            getItemIcon(item) {
                if (item.type === 'parent') return '↩️';
                if (item.is_dir) return '📁';
                
                const ext = item.extension;
                if (['.js', '.ts', '.jsx', '.tsx'].includes(ext)) return '📜';
                if (['.py'].includes(ext)) return '🐍';
                if (['.md', '.txt'].includes(ext)) return '📝';
                if (['.json', '.yaml', '.yml'].includes(ext)) return '⚙️';
                if (['.png', '.jpg', '.jpeg', '.gif', '.svg'].includes(ext)) return '🖼️';
                if (['.mp4', '.mov', '.avi'].includes(ext)) return '🎬';
                if (['.mp3', '.wav', '.flac'].includes(ext)) return '🎵';
                if (['.zip', '.tar', '.gz'].includes(ext)) return '📦';
                
                return '📄';
            }

            handleItemClick(path, isDir) {
                if (isDir) {
                    this.loadDirectory(path);
                } else {
                    // For files, you could implement a preview or download
                    console.log('File clicked:', path);
                }
            }
        }

        // Initialize the explorer
        const explorer = new FileExplorer();
    </script>
</body>
</html>
        '''
    
    def serve_files_api(self):
        try:
            files = self.analyze_directory()
            base_path = Path.home() / "Dev" / "_playground"
            if not base_path.exists():
                base_path = Path.cwd()
                
            categories = {"current": 0, "recent": 0, "old": 0, "archive": 0}
            for file in files:
                categories[file["time_category"]] += 1
            
            response = {
                "files": files,
                "total_files": len(files),
                "playground_path": str(base_path),
                "categories": categories
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        except Exception as e:
            self.send_error(500, str(e))
    
    def serve_stats_api(self):
        try:
            files = self.analyze_directory()
            base_path = Path.home() / "Dev" / "_playground"
            if not base_path.exists():
                base_path = Path.cwd()
                
            total_size = sum(f["size"] for f in files)
            categories = {}
            
            for category in ["current", "recent", "old", "archive"]:
                cat_files = [f for f in files if f["time_category"] == category]
                if cat_files:
                    cat_size = sum(f["size"] for f in cat_files)
                    avg_days = sum(f["days_since_used"] for f in cat_files) / len(cat_files)
                    categories[category] = {
                        "count": len(cat_files),
                        "size": cat_size,
                        "size_mb": round(cat_size / (1024**2), 2),
                        "avg_days": round(avg_days, 1)
                    }
            
            response = {
                "total_files": len(files),
                "total_size": total_size,
                "total_size_gb": round(total_size / (1024**3), 2),
                "categories": categories,
                "playground_path": str(base_path),
                "last_updated": datetime.now().isoformat()
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        except Exception as e:
            self.send_error(500, str(e))
    
    def serve_organize_api(self):
        try:
            files = self.analyze_directory()
            actions = [f"Would organize {f['name']} -> {f['time_category']}/" for f in files[:10]]
            if len(files) > 10:
                actions.append(f"... and {len(files) - 10} more files")
            
            response = {
                "success": True,
                "actions": actions,
                "mode": "preview",
                "executed": False,
                "total_actions": len(files),
                "note": "Web UI is read-only - no files were moved or changed"
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        except Exception as e:
            self.send_error(500, str(e))
    
    def analyze_directory(self):
        """Simple directory analysis"""
        base_path = Path.home() / "Dev" / "_playground"
        
        # Fallback to current directory if playground doesn't exist
        if not base_path.exists():
            base_path = Path.cwd()
            
        files = []
        
        excluded_dirs = {'.git', 'node_modules', '.DS_Store', '__pycache__', '.venv', 'venv', 'static', 'templates'}
        
        for item in base_path.iterdir():
            if not item.is_dir() or item.name.startswith('.') or item.name in excluded_dirs:
                continue
                
            try:
                stat = item.stat()
                last_access = max(stat.st_atime, stat.st_mtime)
                
                # Get size (simplified)
                size = stat.st_size if item.is_file() else 1024  # Default for dirs
                
                # Classify by time
                now = time.time()
                days_ago = (now - last_access) / (24 * 3600)
                
                if days_ago <= 30:
                    time_category = "current"
                elif days_ago <= 180:
                    time_category = "recent"
                elif days_ago <= 365:
                    time_category = "old"
                else:
                    time_category = "archive"
                
                # Classify by theme
                name_lower = item.name.lower()
                theme = "misc"
                
                if any(k in name_lower for k in ['ai', 'gpt', 'llm', 'claude', 'ml']):
                    theme = "ai"
                elif any(k in name_lower for k in ['todo', 'task', 'productivity']):
                    theme = "productivity"
                elif any(k in name_lower for k in ['stock', 'finance', 'trading']):
                    theme = "stocks"
                elif any(k in name_lower for k in ['dev', 'code', 'programming']):
                    theme = "development"
                elif any(k in name_lower for k in ['data', 'database', 'analytics']):
                    theme = "data"
                elif any(k in name_lower for k in ['video', 'audio', 'media']):
                    theme = "media"
                elif any(k in name_lower for k in ['tool', 'utility', 'script']):
                    theme = "tools"
                elif any(k in name_lower for k in ['course', 'learn', 'tutorial']):
                    theme = "learning"
                
                files.append({
                    "name": item.name,
                    "path": str(item),
                    "size": size,
                    "size_mb": round(size / (1024 * 1024), 2),
                    "last_used": datetime.fromtimestamp(last_access).strftime('%Y-%m-%d'),
                    "days_since_used": round(days_ago, 1),
                    "time_category": time_category,
                    "theme": theme,
                    "atime": stat.st_atime,
                    "mtime": stat.st_mtime,
                    "ctime": stat.st_ctime
                })
            except Exception as e:
                print(f"Error processing {item}: {e}")
                continue
        
        return files

if __name__ == "__main__":
    server = HTTPServer(('127.0.0.1', 8000), PlaygroundHandler)
    print("🚀 Starting Minimal Playground Organizer Web UI...")
    print("📁 Web interface available at: http://127.0.0.1:8000")
    print("ℹ️  Read-only mode: Files are displayed but not modified")
    print("🔄 Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
        server.shutdown()