#!/usr/bin/env python3
"""
Simple web server starter for debugging
"""

import uvicorn
from web_ui import app

if __name__ == "__main__":
    print("🚀 Starting Playground Organizer Web UI...")
    print("📁 Web interface will be available at: http://localhost:8000")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="debug"
    )