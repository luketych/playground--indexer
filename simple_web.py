#!/usr/bin/env python3
"""
Simple Web UI for Playground Organizer - Read Only
"""

import os
import sys
import json
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from datetime import datetime
import time
import subprocess

app = FastAPI(title="Playground Organizer", description="Read-only web UI for file viewing")

# Serve static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Simple file analyzer (without importing the full class)
def analyze_directory(base_path):
    """Simple directory analysis"""
    base_path = Path(base_path)
    files = []
    
    excluded_dirs = {'.git', 'node_modules', '.DS_Store', '__pycache__', '.venv', 'venv'}
    
    for item in base_path.iterdir():
        if not item.is_dir() or item.name.startswith('.') or item.name in excluded_dirs:
            continue
            
        try:
            stat = item.stat()
            last_access = max(stat.st_atime, stat.st_mtime)
            
            # Get size
            size = 0
            try:
                result = subprocess.run(['du', '-sk', str(item)], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    size = int(result.stdout.split()[0]) * 1024
            except:
                pass
            
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
            
            theme_keywords = {
                'ai': ['gpt', 'llm', 'claude', 'openai', 'anthropic', 'ml', 'ai'],
                'productivity': ['todo', 'task', 'calendar', 'notes', 'productivity'],
                'stocks': ['stock', 'trading', 'finance', 'market', 'crypto'],
                'development': ['dev', 'code', 'programming', 'api', 'github'],
                'data': ['data', 'database', 'sql', 'analytics', 'pipeline'],
                'media': ['video', 'audio', 'image', 'media', 'photo', 'music'],
                'tools': ['tool', 'utility', 'helper', 'script', 'automation'],
                'learning': ['course', 'tutorial', 'learn', 'education', 'study']
            }
            
            for theme_name, keywords in theme_keywords.items():
                if any(keyword in name_lower for keyword in keywords):
                    theme = theme_name
                    break
            
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

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main page"""
    html_file = Path(__file__).parent / "templates" / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    else:
        return HTMLResponse("""
        <html><body>
        <h1>Playground Organizer</h1>
        <p>Template files not found. Please check the installation.</p>
        </body></html>
        """)

@app.get("/api/files")
async def get_files():
    """Get all files with analysis"""
    try:
        base_path = Path.cwd()
        files = analyze_directory(base_path)
        
        # Calculate categories
        categories = {"current": 0, "recent": 0, "old": 0, "archive": 0}
        for file in files:
            categories[file["time_category"]] += 1
        
        return JSONResponse({
            "files": files,
            "total_files": len(files),
            "playground_path": str(base_path),
            "categories": categories
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    """Get statistics"""
    try:
        files = analyze_directory(Path.cwd())
        
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
        
        return JSONResponse({
            "total_files": len(files),
            "total_size": total_size,
            "total_size_gb": round(total_size / (1024**3), 2),
            "categories": categories,
            "playground_path": str(Path.cwd()),
            "last_updated": datetime.now().isoformat()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/organize")
async def preview_organize(request: Request):
    """Preview organization (read-only)"""
    try:
        data = await request.json()
        mode = data.get("mode", "time")
        
        # This is read-only, so just return a preview message
        files = analyze_directory(Path.cwd())
        
        if mode == "time":
            actions = [f"Would organize {f['name']} -> {f['time_category']}/" for f in files[:10]]
        elif mode == "theme":
            actions = [f"Would create symlink {f['name']} -> by-theme/{f['theme']}/" for f in files[:10]]
        else:  # both
            actions = [f"Would organize {f['name']} -> {f['time_category']}/ and by-theme/{f['theme']}/" for f in files[:10]]
        
        if len(files) > 10:
            actions.append(f"... and {len(files) - 10} more files")
        
        return JSONResponse({
            "success": True,
            "actions": actions,
            "mode": mode,
            "executed": False,
            "total_actions": len(files),
            "note": "Web UI is read-only - no files were moved or changed"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("🚀 Starting Simple Playground Organizer Web UI...")
    print("📁 Web interface available at: http://localhost:8000")
    print("ℹ️  Read-only mode: Files are displayed but not modified")
    
    uvicorn.run(app, host="127.0.0.1", port=8000)