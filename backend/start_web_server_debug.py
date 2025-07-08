#!/usr/bin/env python3
"""
Simple web server starter for debugging
"""

import os
import uvicorn
from dotenv import load_dotenv
from .start_web_server import app

# Load environment variables from .env file
load_dotenv()

def main():
    # Get configuration from environment variables
    host = os.getenv("WEB_SERVER_DEBUG_HOST", "127.0.0.1")
    port = int(os.getenv("WEB_SERVER_DEBUG_PORT", "8000"))
    log_level = os.getenv("WEB_SERVER_DEBUG_LOG_LEVEL", "debug")
    
    print("🚀 Starting Playground Organizer Web UI (Debug Mode)...")
    print(f"📁 Web interface will be available at: http://localhost:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level
    )

if __name__ == "__main__":
    main()