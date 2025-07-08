#!/usr/bin/env python3
"""
Playground Organization System

Automatically organize playground directories by access frequency and themes.
"""

import os
import sys
import json
import time
import argparse
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


class PlaygroundOrganizer:
    def __init__(self, base_dir: str = None, config_path: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.config_path = config_path or ".playground-config.json"
        self.config = self._load_config()
        
        # Time thresholds in seconds
        self.current_threshold = self.config.get("thresholds", {}).get("current", 30) * 24 * 3600
        self.recent_threshold = self.config.get("thresholds", {}).get("recent", 180) * 24 * 3600
        self.old_threshold = self.config.get("thresholds", {}).get("old", 365) * 24 * 3600
        
        # Excluded directories
        self.excluded_dirs = set(self.config.get("excluded_dirs", [
            ".git", "node_modules", ".DS_Store", "__pycache__", ".venv", "venv"
        ]))
        
        # Theme mappings
        self.theme_mappings = self.config.get("theme_mappings", {
            "ai": ["gpt", "llm", "claude", "openai", "anthropic", "ai", "ml", "machine-learning"],
            "productivity": ["todo", "task", "calendar", "notes", "productivity", "organizer"],
            "stocks": ["stock", "trading", "finance", "market", "crypto", "investment"],
            "development": ["dev", "code", "programming", "api", "developer", "development"],
            "data": ["data", "database", "sql", "analytics", "pipeline", "etl"],
            "media": ["video", "audio", "image", "media", "photo", "music"],
            "tools": ["tool", "utility", "helper", "script", "automation"],
            "learning": ["course", "tutorial", "learn", "education", "study", "training"],
            "misc": []
        })

    def _load_config(self) -> Dict:
        """Load configuration from JSON file."""
        config_file = self.base_dir / self.config_path
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config file {config_file}: {e}")
        
        return {}

    def _get_directory_info(self, dir_path: Path) -> Dict:
        """Get directory information including access times and size."""
        try:
            stat = dir_path.stat()
            info = {
                "path": dir_path,
                "name": dir_path.name,
                "atime": stat.st_atime,
                "mtime": stat.st_mtime,
                "size": 0,
                "last_access": max(stat.st_atime, stat.st_mtime)
            }
            
            # Calculate directory size
            try:
                result = subprocess.run(
                    ["du", "-sk", str(dir_path)], 
                    capture_output=True, 
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    info["size"] = int(result.stdout.split()[0]) * 1024  # Convert KB to bytes
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError):
                pass
            
            return info
        except OSError:
            return None

    def _classify_by_time(self, last_access: float) -> str:
        """Classify directory by last access time."""
        now = time.time()
        age = now - last_access
        
        if age <= self.current_threshold:
            return "current"
        elif age <= self.recent_threshold:
            return "recent"
        elif age <= self.old_threshold:
            return "old"
        else:
            return "archive"

    def _classify_by_theme(self, dir_name: str) -> str:
        """Classify directory by theme based on name."""
        dir_name_lower = dir_name.lower()
        
        for theme, keywords in self.theme_mappings.items():
            if theme == "misc":
                continue
            for keyword in keywords:
                if keyword in dir_name_lower:
                    return theme
        
        return "misc"

    def analyze_directories(self) -> List[Dict]:
        """Analyze all directories in the base directory."""
        directories = []
        
        for item in self.base_dir.iterdir():
            if not item.is_dir():
                continue
            if item.name in self.excluded_dirs:
                continue
            if item.name.startswith('.'):
                continue
            
            dir_info = self._get_directory_info(item)
            if dir_info:
                dir_info["time_category"] = self._classify_by_time(dir_info["last_access"])
                dir_info["theme"] = self._classify_by_theme(dir_info["name"])
                directories.append(dir_info)
        
        return sorted(directories, key=lambda x: x["last_access"], reverse=True)

    def generate_report(self, include_sizes: bool = True) -> str:
        """Generate a detailed report of directory analysis."""
        directories = self.analyze_directories()
        
        report = []
        report.append("📊 Playground Organization Report")
        report.append("=" * 50)
        report.append(f"Base Directory: {self.base_dir}")
        report.append(f"Total Directories: {len(directories)}")
        report.append("")
        
        # Time-based summary
        time_counts = {}
        for dir_info in directories:
            category = dir_info["time_category"]
            time_counts[category] = time_counts.get(category, 0) + 1
        
        report.append("📅 Time-based Categories:")
        for category in ["current", "recent", "old", "archive"]:
            count = time_counts.get(category, 0)
            emoji = {"current": "🟢", "recent": "🟡", "old": "🟠", "archive": "🔴"}[category]
            report.append(f"  {emoji} {category}: {count} directories")
        report.append("")
        
        # Theme-based summary
        theme_counts = {}
        for dir_info in directories:
            theme = dir_info["theme"]
            theme_counts[theme] = theme_counts.get(theme, 0) + 1
        
        report.append("🎯 Theme-based Categories:")
        for theme, count in sorted(theme_counts.items()):
            emoji = {"ai": "🤖", "productivity": "⚡", "stocks": "📈", "development": "💻", 
                    "data": "📊", "media": "🎬", "tools": "🛠️", "learning": "📚", "misc": "📁"}
            report.append(f"  {emoji.get(theme, '📁')} {theme}: {count} directories")
        report.append("")
        
        # Detailed directory listing
        report.append("📋 Directory Details:")
        report.append("-" * 50)
        
        for dir_info in directories:
            last_access = datetime.fromtimestamp(dir_info["last_access"])
            size_str = f"{dir_info['size'] / (1024*1024):.1f}MB" if include_sizes and dir_info["size"] > 0 else "N/A"
            
            report.append(f"📁 {dir_info['name']}")
            report.append(f"   Time: {dir_info['time_category']} | Theme: {dir_info['theme']}")
            report.append(f"   Last Access: {last_access.strftime('%Y-%m-%d %H:%M')}")
            if include_sizes:
                report.append(f"   Size: {size_str}")
            report.append("")
        
        return "\n".join(report)

    def organize_by_time(self, dry_run: bool = True, use_symlinks: bool = False) -> List[str]:
        """Organize directories by time categories."""
        directories = self.analyze_directories()
        actions = []
        
        # Create organization directories
        org_dirs = {}
        for category in ["current", "recent", "old", "archive"]:
            org_dir = self.base_dir / category
            org_dirs[category] = org_dir
            
            if not dry_run and not org_dir.exists():
                org_dir.mkdir(exist_ok=True)
                actions.append(f"Created directory: {org_dir}")
        
        # Move/link directories
        for dir_info in directories:
            source = dir_info["path"]
            category = dir_info["time_category"]
            target_dir = org_dirs[category]
            target = target_dir / source.name
            
            if target.exists():
                actions.append(f"SKIP (exists): {source.name} -> {category}/ (target exists)")
                continue
            
            if dry_run:
                link_type = "symlink" if use_symlinks else "move"
                actions.append(f"Would {link_type}: {source.name} -> {category}/")
            else:
                try:
                    if use_symlinks:
                        target.symlink_to(source.resolve())
                        actions.append(f"Symlinked: {source.name} -> {category}/")
                    else:
                        shutil.move(str(source), str(target))
                        actions.append(f"Moved: {source.name} -> {category}/")
                except (OSError, shutil.Error) as e:
                    actions.append(f"ERROR: Could not process {source.name}: {e}")
        
        return actions

    def organize_by_theme(self, dry_run: bool = True) -> List[str]:
        """Organize directories by themes using symlinks."""
        directories = self.analyze_directories()
        actions = []
        
        # Create theme organization structure
        theme_base = self.base_dir / "organized" / "by-theme"
        
        if not dry_run:
            theme_base.mkdir(parents=True, exist_ok=True)
            actions.append(f"Created theme base directory: {theme_base}")
        
        theme_dirs = {}
        for theme in self.theme_mappings.keys():
            theme_dir = theme_base / theme
            theme_dirs[theme] = theme_dir
            
            if not dry_run and not theme_dir.exists():
                theme_dir.mkdir(exist_ok=True)
                actions.append(f"Created theme directory: {theme_dir}")
        
        # Create symlinks
        for dir_info in directories:
            source = dir_info["path"]
            theme = dir_info["theme"]
            target_dir = theme_dirs[theme]
            target = target_dir / source.name
            
            if target.exists():
                actions.append(f"SKIP (exists): {source.name} -> {theme}/ (target exists)")
                continue
            
            if dry_run:
                actions.append(f"Would symlink: {source.name} -> by-theme/{theme}/")
            else:
                try:
                    target.symlink_to(source.resolve())
                    actions.append(f"Symlinked: {source.name} -> by-theme/{theme}/")
                except OSError as e:
                    actions.append(f"ERROR: Could not symlink {source.name}: {e}")
        
        return actions


def main():
    parser = argparse.ArgumentParser(description="Playground Organization System")
    parser.add_argument("--base-dir", help="Base directory to organize (default: current directory)")
    parser.add_argument("--report", action="store_true", help="Generate detailed report")
    parser.add_argument("--analyze", action="store_true", help="Analyze access patterns")
    parser.add_argument("--organize", action="store_true", help="Organize files by time")
    parser.add_argument("--theme", action="store_true", help="Organize files by theme")
    parser.add_argument("--both", action="store_true", help="Organize by both time and theme")
    parser.add_argument("--execute", action="store_true", help="Execute changes (default: dry run)")
    parser.add_argument("--symlinks", action="store_true", help="Use symlinks instead of moving")
    parser.add_argument("--no-sizes", action="store_true", help="Skip size calculation for faster analysis")
    parser.add_argument("--watch", action="store_true", help="Monitor file access in real-time")
    
    args = parser.parse_args()
    
    # Initialize organizer
    organizer = PlaygroundOrganizer(base_dir=args.base_dir)
    
    # Handle watch mode
    if args.watch:
        print("Real-time monitoring not yet implemented")
        return
    
    # Handle report
    if args.report or args.analyze:
        print(organizer.generate_report(include_sizes=not args.no_sizes))
        return
    
    # Handle organization
    dry_run = not args.execute
    
    if dry_run:
        print("🔍 DRY RUN MODE - No files will be moved")
        print("Use --execute to actually perform the operations")
        print("-" * 50)
    
    actions = []
    
    if args.both:
        # Organize by time first, then by theme
        actions.extend(organizer.organize_by_time(dry_run=dry_run, use_symlinks=args.symlinks))
        actions.extend(organizer.organize_by_theme(dry_run=dry_run))
    elif args.theme:
        actions.extend(organizer.organize_by_theme(dry_run=dry_run))
    elif args.organize:
        actions.extend(organizer.organize_by_time(dry_run=dry_run, use_symlinks=args.symlinks))
    else:
        # Default: show help
        parser.print_help()
        return
    
    # Print actions
    if actions:
        print(f"\n📋 {'Planned Actions' if dry_run else 'Completed Actions'}:")
        for action in actions:
            print(f"  {action}")
        print(f"\nTotal actions: {len(actions)}")
    else:
        print("No actions needed - all directories are already organized.")


if __name__ == "__main__":
    main()