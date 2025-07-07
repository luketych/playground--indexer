# 🗂️ Playground Organization System

Automatically organize your playground directories by **access frequency** and **themes**. Keep active projects accessible while archiving old ones, and create thematic views using symbolic links.

## 📋 Quick Start

```bash
# 1. Analyze what you have
python3 playground-organizer.py --report

# 2. Preview organization (dry run)
python3 playground-organizer.py --organize

# 3. Execute organization
python3 playground-organizer.py --organize --execute

# OR organize by themes using symlinks
python3 playground-organizer.py --theme --execute

# OR create both time and theme organizations
python3 playground-organizer.py --both --execute
```

## 📁 How It Works

### Time-based Organization
Files are organized into 4 categories:

- **🟢 current/** - Last 30 days (active projects)
- **🟡 recent/** - 30 days to 6 months (occasionally used)
- **🟠 old/** - 6 months to 1 year (rarely accessed)
- **🔴 archive/** - Over 1 year (candidates for deletion)

### Theme-based Organization (Symlinks)
Projects are automatically categorized by themes:

- **🤖 ai/** - AI/ML projects (gpt, llm, claude, etc.)
- **⚡ productivity/** - Task management, calendars, organizers
- **📈 stocks/** - Finance, trading, investment projects
- **💻 development/** - Dev tools, APIs, coding utilities
- **📊 data/** - Databases, analytics, data processing
- **🎬 media/** - Video, audio, images, entertainment
- **🛠️ tools/** - Utilities, automation, helpers
- **📚 learning/** - Courses, tutorials, educational content
- **📁 misc/** - Uncategorized projects

## 🛠️ Main Commands

```bash
# Generate detailed report
python3 playground-organizer.py --report

# Organize files (preview)
python3 playground-organizer.py --organize

# Execute organization
python3 playground-organizer.py --organize --execute

# Monitor file access in real-time
python3 playground-organizer.py --watch

# Organize by themes using symlinks
python3 playground-organizer.py --theme

# Use symlinks instead of moving files
python3 playground-organizer.py --organize --symlinks

# Create both time and theme organizations
python3 playground-organizer.py --both
```

## 🚨 Safety

- **Dry run by default** - Shows what would move without actually moving
- **No overwrites** - Detects and prevents duplicate file conflicts
- **Reversible** - Simply move files back from organized folders to undo
- **Symlinks preserve originals** - Theme organization uses symlinks, keeping files in place
- **Non-destructive** - Original directory structure remains intact

---

### More Details

- [Advanced Usage](#advanced-usage)
- [Configuration](#configuration)
- [Automation](#automation)
- [Troubleshooting](#troubleshooting)

## Advanced Usage

### Shell Scripts
Quick alternatives for specific tasks:

```bash
./auto-organize.sh              # Basic organization
./file-watcher.sh              # Real-time monitoring
./quick-analyze.sh             # Fast analysis
./analyze-access.sh            # Detailed access patterns
```

### Access Detection Methods

1. **File System Timestamps** - Uses `atime` (last accessed) and `mtime` (last modified)
2. **Real-time Monitoring** - Optional `fswatch` integration for tracking actual file opens
3. **Directory Sizes** - Calculates space usage to identify large projects

## Configuration

### Python Configuration (`.playground-config.json`)
```json
{
  "tracking_enabled": true,
  "auto_organize": false,
  "excluded_dirs": [".git", "node_modules", ".DS_Store"],
  "use_symlinks": true,
  "symlink_base_dir": "organized",
  "theme_mappings": {
    "ai": ["gpt", "llm", "claude", "openai", "anthropic"],
    "productivity": ["todo", "task", "calendar", "notes"],
    "stocks": ["stock", "trading", "finance", "market"],
    "development": ["dev", "code", "programming", "api"],
    "data": ["data", "database", "sql", "analytics"],
    "media": ["video", "audio", "image", "media"],
    "tools": ["tool", "utility", "helper", "script"],
    "learning": ["course", "tutorial", "learn", "education"],
    "misc": []
  },
  "thresholds": {
    "current": 30,
    "recent": 180,
    "old": 365
  }
}
```

### Shell Script Configuration
Edit thresholds at the top of `auto-organize.sh`:
```bash
CURRENT_THRESHOLD=$((30 * 24 * 3600))   # 30 days
RECENT_THRESHOLD=$((180 * 24 * 3600))   # 6 months
OLD_THRESHOLD=$((365 * 24 * 3600))      # 1 year
```

## Automation

### Daily Cleanup (Cron)
```bash
# Add to crontab (crontab -e)
0 2 * * * cd /Users/luketych/Dev/_playground && python3 playground-organizer.py --organize --execute
```

### Weekly Reports
```bash
0 9 * * 1 cd /Users/luketych/Dev/_playground && python3 playground-organizer.py --report
```

### Background Monitoring
```bash
# Add to .bashrc/.zshrc
nohup /Users/luketych/Dev/_playground/file-watcher.sh > /dev/null 2>&1 &
```

## Troubleshooting

### Missing fswatch
```bash
brew install fswatch
```

### Permission Errors
```bash
chmod +x *.sh
```

### Slow Size Calculation
```bash
python3 playground-organizer.py --report --no-sizes
```