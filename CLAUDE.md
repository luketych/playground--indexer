# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Python Scripts
```bash
# Generate detailed access report
python3 playground-organizer.py --report

# Analyze access patterns 
python3 playground-organizer.py --analyze

# Organize files by time (dry run)
python3 playground-organizer.py --organize

# Actually execute time-based organization
python3 playground-organizer.py --organize --execute

# Organize by themes using symlinks (dry run)
python3 playground-organizer.py --theme

# Execute theme-based organization
python3 playground-organizer.py --theme --execute

# Organize by time using symlinks instead of moving
python3 playground-organizer.py --organize --symlinks --execute

# Create both time and theme organizations
python3 playground-organizer.py --both --execute

# Start real-time file monitoring
python3 playground-organizer.py --watch
```

### Shell Scripts
```bash
# Make scripts executable if needed
chmod +x *.sh

# Quick analysis
./quick-analyze.sh

# Detailed access analysis  
./analyze-access.sh

# Organize files (dry run)
./auto-organize.sh

# Execute organization
./auto-organize.sh /Users/luketych/Dev/_playground false

# Start file access monitoring
./file-watcher.sh
```

## Architecture

This is a playground organization system that automatically categorizes directories in multiple ways:

### Time-based Organization
- **current/** - Files accessed within last 30 days
- **recent/** - Files accessed within last 6 months  
- **old/** - Files accessed within last year
- **archive/** - Files older than 1 year

### Theme-based Organization (via Symlinks)
- **organized/by-theme/ai/** - AI/ML related projects
- **organized/by-theme/productivity/** - Productivity tools and apps
- **organized/by-theme/stocks/** - Finance and trading related
- **organized/by-theme/development/** - Development tools and APIs
- **organized/by-theme/data/** - Data analysis and databases
- **organized/by-theme/media/** - Media files and projects
- **organized/by-theme/tools/** - Utilities and automation
- **organized/by-theme/learning/** - Educational content
- **organized/by-theme/misc/** - Uncategorized projects

### Core Components

1. **playground-organizer.py** - Main Python script with full functionality
   - Uses file system timestamps (atime/mtime) to determine access patterns
   - Calculates directory sizes using `du -sk`
   - Supports dry-run and execution modes
   - Can monitor real-time file access using fswatch
   - Creates symbolic links for theme-based organization
   - Detects themes based on directory names and keywords
   - Supports dual organization (time + theme simultaneously)

2. **Shell Scripts** - Simplified versions for specific tasks
   - `auto-organize.sh` - Basic file organization
   - `file-watcher.sh` - Real-time access monitoring
   - `quick-analyze.sh` - Fast analysis without size calculation
   - `analyze-access.sh` - Detailed access pattern analysis

### Dependencies

- Python 3.x (available: Python 3.13.3)
- fswatch (available: /opt/homebrew/bin/fswatch) - for real-time monitoring
- Standard Unix utilities: du, find, stat

### Configuration

- `.playground-config.json` - Python script configuration
- Thresholds: 30 days (current), 180 days (recent), 365 days (old)
- Excluded directories: .git, node_modules, .DS_Store, __pycache__
- Theme mappings: Configurable keywords for automatic theme detection
- Symlink settings: Base directory and organization modes

### Safety Features

- Dry run by default - never moves files unless `--execute` flag is used
- Duplicate detection prevents overwriting existing files
- Symbolic links preserve original file locations
- All operations can be reversed by removing symlinks or moving files back
- Original files remain untouched when using symlink organization