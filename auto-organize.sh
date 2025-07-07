#!/bin/bash

# Automatic playground organizer based on access patterns
# This will actually move files into organized subdirectories

PLAYGROUND_PATH="${1:-/Users/luketych/Dev/_playground}"
DRY_RUN="${2:-true}"

if [ "$DRY_RUN" = "false" ]; then
    echo "🚀 EXECUTING organization (files will be moved)"
else
    echo "🧪 DRY RUN mode (showing what would be moved)"
fi

echo "📁 Organizing: $PLAYGROUND_PATH"
echo "================================"

# Create organization directories
mkdir -p "$PLAYGROUND_PATH"/{current,recent,old,archive}

NOW=$(date +%s)
CURRENT_THRESHOLD=$((30 * 24 * 3600))     # 30 days
RECENT_THRESHOLD=$((180 * 24 * 3600))     # 6 months  
OLD_THRESHOLD=$((365 * 24 * 3600))        # 1 year

moved_count=0

for dir in "$PLAYGROUND_PATH"/*; do
    if [ ! -d "$dir" ]; then
        continue
    fi
    
    basename_dir=$(basename "$dir")
    
    # Skip organization directories and hidden files
    if [[ $basename_dir == "current" ]] || [[ $basename_dir == "recent" ]] || \
       [[ $basename_dir == "old" ]] || [[ $basename_dir == "archive" ]] || \
       [[ $basename_dir == .* ]]; then
        continue
    fi
    
    # Get access time (use the more recent of access or modification time)
    ATIME=$(stat -f "%a" "$dir" 2>/dev/null)
    MTIME=$(stat -f "%m" "$dir" 2>/dev/null)
    
    if [ -z "$ATIME" ] || [ -z "$MTIME" ]; then
        continue
    fi
    
    LAST_USED=$((ATIME > MTIME ? ATIME : MTIME))
    TIME_DIFF=$((NOW - LAST_USED))
    
    # Determine target directory
    if [ $TIME_DIFF -le $CURRENT_THRESHOLD ]; then
        TARGET_DIR="current"
        CATEGORY="CURRENT"
    elif [ $TIME_DIFF -le $RECENT_THRESHOLD ]; then
        TARGET_DIR="recent"
        CATEGORY="RECENT"
    elif [ $TIME_DIFF -le $OLD_THRESHOLD ]; then
        TARGET_DIR="old"
        CATEGORY="OLD"
    else
        TARGET_DIR="archive"
        CATEGORY="ARCHIVE"
    fi
    
    TARGET_PATH="$PLAYGROUND_PATH/$TARGET_DIR/$basename_dir"
    
    # Skip if already in the right place
    if [ "$dir" = "$TARGET_PATH" ]; then
        continue
    fi
    
    SIZE=$(du -sh "$dir" 2>/dev/null | cut -f1)
    DAYS_AGO=$((TIME_DIFF / 86400))
    
    echo "📦 $CATEGORY: $basename_dir ($SIZE, ${DAYS_AGO}d ago)"
    
    if [ "$DRY_RUN" = "false" ]; then
        if [ -e "$TARGET_PATH" ]; then
            echo "   ⚠️  Warning: $TARGET_PATH already exists, skipping"
        else
            mv "$dir" "$TARGET_PATH"
            echo "   ✅ Moved to $TARGET_DIR/"
            ((moved_count++))
        fi
    else
        echo "   📍 Would move to $TARGET_DIR/"
        ((moved_count++))
    fi
done

echo ""
echo "📊 Summary:"
echo "==========="
if [ "$DRY_RUN" = "false" ]; then
    echo "✅ Moved $moved_count directories"
else
    echo "📋 Would move $moved_count directories"
    echo ""
    echo "To actually execute the moves, run:"
    echo "$0 $PLAYGROUND_PATH false"
fi