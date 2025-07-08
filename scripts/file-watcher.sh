#!/bin/bash

# File access monitor for playground directory
# This will track which directories you actually access

PLAYGROUND_PATH="${1:-/Users/luketych/Dev/_playground}"
LOG_FILE="$PLAYGROUND_PATH/.access-log.txt"

echo "🔍 Starting file access monitor for: $PLAYGROUND_PATH"
echo "📝 Logging to: $LOG_FILE"
echo "⏹️  Press Ctrl+C to stop"
echo ""

# Create log file if it doesn't exist
touch "$LOG_FILE"

# Monitor file access using fswatch
fswatch -r -a "$PLAYGROUND_PATH" | while read FILE; do
    # Get just the top-level directory name
    REL_PATH="${FILE#$PLAYGROUND_PATH/}"
    TOP_DIR=$(echo "$REL_PATH" | cut -d'/' -f1)
    
    # Skip hidden files and our own log files
    if [[ "$TOP_DIR" == .* ]] || [[ "$TOP_DIR" == *".log"* ]]; then
        continue
    fi
    
    # Only log if it's a real directory access
    if [ -d "$PLAYGROUND_PATH/$TOP_DIR" ] && [ "$TOP_DIR" != "_playground" ]; then
        TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
        echo "$TIMESTAMP - Accessed: $TOP_DIR" | tee -a "$LOG_FILE"
    fi
done