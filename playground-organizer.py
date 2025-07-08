#!/usr/bin/env python3
"""
Playground Organization System CLI

This is the main entry point for the playground organizer.
It imports from the backend package for the actual implementation.
"""

import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import from the backend package
from backend.src.playground_organizer import PlaygroundOrganizer

if __name__ == "__main__":
    # Import main function from the package
    from backend.src.playground_organizer.playground_organizer import main
    main()