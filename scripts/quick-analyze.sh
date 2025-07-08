#!/bin/bash

# Quick and simple access pattern analyzer
PLAYGROUND_PATH="${1:-/Users/luketych/Dev/_playground}"

echo "🔍 Access Pattern Analysis: $PLAYGROUND_PATH"
echo "=============================================="

NOW=$(date +%s)

echo ""
echo "🟢 CURRENT (last 30 days):"
find "$PLAYGROUND_PATH" -maxdepth 1 -type d -neweraa -30 2>/dev/null | while read dir; do
    if [[ $(basename "$dir") != .* ]] && [[ $(basename "$dir") != "_playground" ]]; then
        size=$(du -sh "$dir" 2>/dev/null | cut -f1)
        printf "  %-25s %8s\n" "$(basename "$dir")" "$size"
    fi
done

echo ""
echo "🟡 RECENT (30 days - 6 months):"
find "$PLAYGROUND_PATH" -maxdepth 1 -type d ! -neweraa -30 -neweraa -180 2>/dev/null | while read dir; do
    if [[ $(basename "$dir") != .* ]] && [[ $(basename "$dir") != "_playground" ]]; then
        size=$(du -sh "$dir" 2>/dev/null | cut -f1)
        printf "  %-25s %8s\n" "$(basename "$dir")" "$size"
    fi
done

echo ""
echo "🔴 OLD (6+ months ago):"
find "$PLAYGROUND_PATH" -maxdepth 1 -type d ! -neweraa -180 2>/dev/null | while read dir; do
    if [[ $(basename "$dir") != .* ]] && [[ $(basename "$dir") != "_playground" ]]; then
        size=$(du -sh "$dir" 2>/dev/null | cut -f1)
        atime=$(stat -f "%a" "$dir" 2>/dev/null)
        if [ -n "$atime" ]; then
            days_ago=$(( (NOW - atime) / 86400 ))
            printf "  %-25s %8s  (%d days ago)\n" "$(basename "$dir")" "$size" "$days_ago"
        fi
    fi
done

echo ""
echo "💾 LARGEST DIRECTORIES:"
du -sh "$PLAYGROUND_PATH"/* 2>/dev/null | sort -hr | head -10