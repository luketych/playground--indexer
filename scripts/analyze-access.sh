#!/bin/bash

# Quick access pattern analyzer for playground directory
# Usage: ./analyze-access.sh [playground_path]

PLAYGROUND_PATH="${1:-/Users/luketych/Dev/_playground}"

echo "🔍 Analyzing access patterns in: $PLAYGROUND_PATH"
echo "=================================================="

# Current time in epoch
NOW=$(date +%s)

# Time thresholds (in seconds)
CURRENT_THRESHOLD=$((30 * 24 * 3600))     # 30 days
RECENT_THRESHOLD=$((180 * 24 * 3600))     # 6 months  
OLD_THRESHOLD=$((365 * 24 * 3600))        # 1 year

# Arrays to store results
declare -a CURRENT_DIRS=()
declare -a RECENT_DIRS=()
declare -a OLD_DIRS=()
declare -a ARCHIVE_DIRS=()

# Function to get human readable time difference
human_time_diff() {
    local diff=$1
    local days=$((diff / 86400))
    
    if [ $days -lt 1 ]; then
        echo "today"
    elif [ $days -lt 7 ]; then
        echo "${days}d ago"
    elif [ $days -lt 30 ]; then
        local weeks=$((days / 7))
        echo "${weeks}w ago"
    elif [ $days -lt 365 ]; then
        local months=$((days / 30))
        echo "${months}m ago"
    else
        local years=$((days / 365))
        echo "${years}y ago"
    fi
}

# Function to get directory size
get_dir_size() {
    du -sh "$1" 2>/dev/null | cut -f1
}

echo "Scanning directories..."

# Process each directory
for dir in "$PLAYGROUND_PATH"/*; do
    if [ ! -d "$dir" ]; then
        continue
    fi
    
    # Skip hidden directories and common build artifacts
    basename_dir=$(basename "$dir")
    if [[ $basename_dir == .* ]] || [[ $basename_dir == "node_modules" ]]; then
        continue
    fi
    
    # Get access time (use the more recent of access or modification time)
    ATIME=$(stat -f "%a" "$dir" 2>/dev/null)
    MTIME=$(stat -f "%m" "$dir" 2>/dev/null)
    
    if [ -z "$ATIME" ] || [ -z "$MTIME" ]; then
        continue
    fi
    
    # Use the more recent time
    LAST_USED=$((ATIME > MTIME ? ATIME : MTIME))
    TIME_DIFF=$((NOW - LAST_USED))
    
    SIZE=$(get_dir_size "$dir")
    HUMAN_TIME=$(human_time_diff $TIME_DIFF)
    
    # Create entry with: "path|size|time_diff|human_time"
    ENTRY="$dir|$SIZE|$TIME_DIFF|$HUMAN_TIME"
    
    # Categorize by access frequency
    if [ $TIME_DIFF -le $CURRENT_THRESHOLD ]; then
        CURRENT_DIRS+=("$ENTRY")
    elif [ $TIME_DIFF -le $RECENT_THRESHOLD ]; then
        RECENT_DIRS+=("$ENTRY")
    elif [ $TIME_DIFF -le $OLD_THRESHOLD ]; then
        OLD_DIRS+=("$ENTRY")
    else
        ARCHIVE_DIRS+=("$ENTRY")
    fi
done

# Function to display category
display_category() {
    local category_name="$1"
    local dirs_var="$2"
    local emoji="$3"
    
    if [ ${#dirs_ref[@]} -eq 0 ]; then
        return
    fi
    
    echo ""
    echo "$emoji $category_name (${#dirs_ref[@]} items):"
    echo "----------------------------------------"
    
    # Sort by time difference (most recent first)
    IFS=$'\n' sorted=($(sort -t'|' -k3,3n <<<"${dirs_ref[*]}"))
    unset IFS
    
    for entry in "${sorted[@]}"; do
        IFS='|' read -r path size time_diff human_time <<< "$entry"
        basename_path=$(basename "$path")
        printf "  %-30s %8s  %s\n" "$basename_path" "$size" "$human_time"
    done
}

# Display results
display_category "CURRENT (last 30 days)" CURRENT_DIRS "🟢"
display_category "RECENT (last 6 months)" RECENT_DIRS "🟡" 
display_category "OLD (last year)" OLD_DIRS "🟠"
display_category "ARCHIVE (1+ years)" ARCHIVE_DIRS "🔴"

# Summary
echo ""
echo "📊 SUMMARY:"
echo "==========="
printf "Current:  %3d directories\n" ${#CURRENT_DIRS[@]}
printf "Recent:   %3d directories\n" ${#RECENT_DIRS[@]}
printf "Old:      %3d directories\n" ${#OLD_DIRS[@]}
printf "Archive:  %3d directories\n" ${#ARCHIVE_DIRS[@]}
echo ""

# Suggestions
if [ ${#ARCHIVE_DIRS[@]} -gt 0 ]; then
    echo "💡 SUGGESTIONS:"
    echo "==============="
    echo "• Consider archiving ${#ARCHIVE_DIRS[@]} old directories to free up space"
    echo "• Review 'OLD' category for unused projects"
    if [ ${#CURRENT_DIRS[@]} -gt 20 ]; then
        echo "• You have many active projects - consider consolidating similar ones"
    fi
fi

echo ""
echo "🔧 To organize automatically:"
echo "python3 playground-organizer.py --organize"
echo "python3 playground-organizer.py --organize --execute  # Actually move files"