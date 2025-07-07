#!/usr/bin/env python3
"""
Playground Organizer - Automatically organize files by access frequency
"""

import os
import time
import json
import shutil
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import subprocess

class PlaygroundOrganizer:
    def __init__(self, playground_path):
        self.playground_path = Path(playground_path)
        self.config_file = self.playground_path / '.playground-config.json'
        self.access_log = self.playground_path / '.access-log.json'
        
        # Time thresholds (in days)
        self.thresholds = {
            'current': 30,    # Last 30 days
            'recent': 180,    # Last 6 months  
            'old': 365,       # Last year
            # Older than 1 year goes to 'archive'
        }
        
        # Theme mappings for categorization
        self.theme_mappings = {
            'ai': ['gpt', 'llm', 'claude', 'openai', 'anthropic', 'ml', 'ai-', 'neural', 'model', 'transformer'],
            'productivity': ['todo', 'task', 'calendar', 'notes', 'productivity', 'planner', 'organize'],
            'stocks': ['stock', 'trading', 'finance', 'market', 'ticker', 'portfolio', 'investment'],
            'development': ['dev', 'code', 'programming', 'api', 'sdk', 'github', 'git'],
            'data': ['data', 'database', 'sql', 'analytics', 'etl', 'pipeline'],
            'media': ['video', 'audio', 'image', 'media', 'photo', 'music', 'movie'],
            'tools': ['tool', 'utility', 'helper', 'script', 'automation'],
            'learning': ['course', 'tutorial', 'learn', 'education', 'study', 'book'],
            'misc': []  # Catch-all category
        }
        
        self.load_config()
    
    def load_config(self):
        """Load or create configuration"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {
                'tracking_enabled': True,
                'auto_organize': False,
                'excluded_dirs': ['.git', 'node_modules', '.DS_Store', '__pycache__'],
                'last_organized': None,
                'use_symlinks': True,
                'symlink_base_dir': 'organized',
                'theme_mappings': self.theme_mappings,
                'organization_modes': ['time', 'theme']  # Can organize by time, theme, or both
            }
            self.save_config()
    
    def save_config(self):
        """Save configuration"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get_file_stats(self, path):
        """Get detailed file statistics including access time"""
        try:
            stat_result = path.stat()
            
            # Get directory size using du command
            dir_size = 0
            if path.is_dir():
                try:
                    result = subprocess.run(['du', '-sk', str(path)], 
                                          capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        # du -sk returns size in KB, convert to bytes
                        dir_size = int(result.stdout.split()[0]) * 1024
                except (subprocess.TimeoutExpired, ValueError, IndexError):
                    dir_size = 0
            else:
                dir_size = stat_result.st_size
            
            return {
                'atime': stat_result.st_atime,  # Access time
                'mtime': stat_result.st_mtime,  # Modification time  
                'ctime': stat_result.st_ctime,  # Creation time
                'size': dir_size,
                'path': str(path)
            }
        except (OSError, PermissionError):
            return None
    
    def detect_theme(self, path):
        """Detect the theme of a directory based on its name"""
        name_lower = path.name.lower()
        
        for theme, keywords in self.config['theme_mappings'].items():
            if theme == 'misc':
                continue
            for keyword in keywords:
                if keyword in name_lower:
                    return theme
        
        return 'misc'  # Default category
    
    def create_symlink(self, source, target):
        """Create a symbolic link from source to target"""
        try:
            if target.exists() or target.is_symlink():
                if target.is_symlink():
                    target.unlink()  # Remove existing symlink
                else:
                    return False  # Don't overwrite real files
            
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(source)
            return True
        except Exception as e:
            print(f"Error creating symlink {target}: {e}")
            return False
    
    def analyze_access_patterns(self):
        """Analyze all directories by access frequency"""
        now = time.time()
        results = {
            'current': [],
            'recent': [], 
            'old': [],
            'archive': []
        }
        
        for item in self.playground_path.iterdir():
            if not item.is_dir() or item.name.startswith('.'):
                continue
                
            if item.name in self.config['excluded_dirs']:
                continue
                
            stats = self.get_file_stats(item)
            if not stats:
                continue
                
            # Use the most recent of access or modification time
            last_used = max(stats['atime'], stats['mtime'])
            days_since_used = (now - last_used) / (24 * 3600)
            
            stats['days_since_used'] = days_since_used
            stats['last_used_date'] = datetime.fromtimestamp(last_used).strftime('%Y-%m-%d')
            
            # Categorize by access frequency
            if days_since_used <= self.thresholds['current']:
                results['current'].append(stats)
            elif days_since_used <= self.thresholds['recent']:
                results['recent'].append(stats)
            elif days_since_used <= self.thresholds['old']:
                results['old'].append(stats)
            else:
                results['archive'].append(stats)
        
        # Sort each category by most recently used
        for category in results:
            results[category].sort(key=lambda x: x['days_since_used'])
            
        return results
    
    def create_organization_structure(self, mode='time'):
        """Create the organized directory structure"""
        if mode == 'time':
            for category in ['current', 'recent', 'old', 'archive']:
                category_path = self.playground_path / category
                category_path.mkdir(exist_ok=True)
        elif mode == 'theme':
            theme_base = self.playground_path / self.config['symlink_base_dir'] / 'by-theme'
            theme_base.mkdir(parents=True, exist_ok=True)
            for theme in self.config['theme_mappings']:
                theme_path = theme_base / theme
                theme_path.mkdir(exist_ok=True)
        elif mode == 'both':
            self.create_organization_structure('time')
            self.create_organization_structure('theme')
    
    def organize_files(self, dry_run=True):
        """Organize files based on access patterns"""
        analysis = self.analyze_access_patterns()
        
        print(f"{'DRY RUN - ' if dry_run else ''}Organization Plan:")
        print("=" * 50)
        
        moves = []
        
        for category, files in analysis.items():
            if not files:
                continue
                
            print(f"\n{category.upper()} ({len(files)} items):")
            
            for file_info in files:
                path = Path(file_info['path'])
                target_dir = self.playground_path / category
                target_path = target_dir / path.name
                
                size_mb = file_info['size'] / (1024 * 1024)
                print(f"  • {path.name:30} {file_info['last_used_date']:12} {size_mb:8.1f}MB")
                
                if not dry_run and path != target_path:
                    moves.append((path, target_path))
        
        if not dry_run and moves:
            self.create_organization_structure()
            
            print(f"\nExecuting {len(moves)} moves...")
            for src, dst in moves:
                try:
                    if dst.exists():
                        print(f"  Warning: {dst} already exists, skipping {src}")
                        continue
                    shutil.move(str(src), str(dst))
                    print(f"  Moved: {src.name} -> {dst.parent.name}/")
                except Exception as e:
                    print(f"  Error moving {src}: {e}")
            
            self.config['last_organized'] = datetime.now().isoformat()
            self.save_config()
    
    def organize_by_theme(self, dry_run=True):
        """Organize files by theme using symbolic links"""
        theme_base = self.playground_path / self.config['symlink_base_dir'] / 'by-theme'
        
        print(f"{'DRY RUN - ' if dry_run else ''}Theme-based Organization:")
        print("=" * 50)
        
        theme_items = defaultdict(list)
        
        # Analyze all directories and categorize by theme
        for item in self.playground_path.iterdir():
            if not item.is_dir() or item.name.startswith('.'):
                continue
            
            if item.name in self.config['excluded_dirs'] or item.name == self.config['symlink_base_dir']:
                continue
            
            theme = self.detect_theme(item)
            stats = self.get_file_stats(item)
            if stats:
                stats['theme'] = theme
                theme_items[theme].append(stats)
        
        # Display and create symlinks
        for theme, items in theme_items.items():
            if not items:
                continue
            
            print(f"\n🏷️  {theme.upper()} ({len(items)} items):")
            theme_dir = theme_base / theme
            
            for item_info in items:
                path = Path(item_info['path'])
                target_link = theme_dir / path.name
                size_mb = item_info['size'] / (1024 * 1024)
                
                print(f"  • {path.name:30} -> {theme:15} {size_mb:8.1f}MB")
                
                if not dry_run:
                    if self.create_symlink(path, target_link):
                        print(f"    ✓ Created symlink: {target_link}")
        
        if not dry_run:
            print(f"\nTheme organization complete. Symlinks created in: {theme_base}")
    
    def organize_with_symlinks(self, dry_run=True):
        """Organize files by time with symbolic links instead of moving"""
        analysis = self.analyze_access_patterns()
        symlink_base = self.playground_path / self.config['symlink_base_dir'] / 'by-time'
        
        print(f"{'DRY RUN - ' if dry_run else ''}Symlink Organization by Time:")
        print("=" * 50)
        
        for category, files in analysis.items():
            if not files:
                continue
            
            print(f"\n⏰ {category.upper()} ({len(files)} items):")
            category_dir = symlink_base / category
            
            for file_info in files:
                path = Path(file_info['path'])
                target_link = category_dir / path.name
                size_mb = file_info['size'] / (1024 * 1024)
                
                print(f"  • {path.name:30} {file_info['last_used_date']:12} {size_mb:8.1f}MB")
                
                if not dry_run:
                    category_dir.mkdir(parents=True, exist_ok=True)
                    if self.create_symlink(path, target_link):
                        print(f"    ✓ Created symlink: {target_link}")
        
        if not dry_run:
            print(f"\nTime-based organization complete. Symlinks created in: {symlink_base}")
    
    def start_file_watcher(self):
        """Start monitoring file access using fswatch"""
        print("Starting file access monitoring...")
        print("Press Ctrl+C to stop")
        
        try:
            # Use fswatch to monitor file access
            cmd = [
                'fswatch', 
                '-a',  # Watch file accesses
                '-r',  # Recursive
                str(self.playground_path)
            ]
            
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            access_counts = defaultdict(int)
            
            while True:
                line = process.stdout.readline()
                if line:
                    file_path = line.strip()
                    if file_path:
                        # Log the access
                        access_counts[file_path] += 1
                        print(f"Accessed: {file_path}")
                        
                        # Update access log every 10 accesses
                        if sum(access_counts.values()) % 10 == 0:
                            self.update_access_log(access_counts)
                            
        except KeyboardInterrupt:
            print("\nStopping file monitor...")
            process.terminate()
            self.update_access_log(access_counts)
    
    def update_access_log(self, access_counts):
        """Update the access log file"""
        log_data = {}
        if self.access_log.exists():
            with open(self.access_log, 'r') as f:
                log_data = json.load(f)
        
        timestamp = datetime.now().isoformat()
        for path, count in access_counts.items():
            if path not in log_data:
                log_data[path] = []
            log_data[path].append({
                'timestamp': timestamp,
                'access_count': count
            })
        
        with open(self.access_log, 'w') as f:
            json.dump(log_data, f, indent=2)
    
    def generate_report(self):
        """Generate a detailed access report"""
        analysis = self.analyze_access_patterns()
        
        print("🗂️  PLAYGROUND ACCESS REPORT")
        print("=" * 60)
        
        total_items = sum(len(files) for files in analysis.values())
        total_size = sum(
            sum(f['size'] for f in files) 
            for files in analysis.values()
        ) / (1024**3)  # GB
        
        print(f"Total Items: {total_items}")
        print(f"Total Size: {total_size:.2f} GB")
        print(f"Last Analysis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        for category, files in analysis.items():
            if not files:
                continue
                
            category_size = sum(f['size'] for f in files) / (1024**3)
            avg_days = sum(f['days_since_used'] for f in files) / len(files)
            
            print(f"\n📁 {category.upper()}")
            print(f"   Items: {len(files):3d} | Size: {category_size:6.2f} GB | Avg Age: {avg_days:.0f} days")
            
            # Show top 5 largest or most recently used
            sorted_files = sorted(files, key=lambda x: x['size'], reverse=True)[:5]
            for f in sorted_files:
                name = Path(f['path']).name
                size_mb = f['size'] / (1024**2)
                print(f"     • {name:25} {f['last_used_date']:12} {size_mb:8.1f}MB")

def main():
    parser = argparse.ArgumentParser(description='Organize playground by access frequency')
    parser.add_argument('--path', default='/Users/luketych/Dev/_playground', 
                       help='Playground directory path')
    parser.add_argument('--analyze', action='store_true', 
                       help='Analyze access patterns')
    parser.add_argument('--organize', action='store_true', 
                       help='Organize files (dry run by default)')
    parser.add_argument('--execute', action='store_true', 
                       help='Actually execute the organization')
    parser.add_argument('--watch', action='store_true', 
                       help='Start file access monitoring')
    parser.add_argument('--report', action='store_true', 
                       help='Generate access report')
    parser.add_argument('--theme', action='store_true',
                       help='Organize by themes using symlinks')
    parser.add_argument('--symlinks', action='store_true',
                       help='Use symlinks instead of moving files')
    parser.add_argument('--both', action='store_true',
                       help='Create both time and theme organizations')
    
    args = parser.parse_args()
    
    organizer = PlaygroundOrganizer(args.path)
    
    if args.analyze or args.report:
        organizer.generate_report()
    elif args.organize:
        if args.symlinks:
            organizer.organize_with_symlinks(dry_run=not args.execute)
        else:
            organizer.organize_files(dry_run=not args.execute)
    elif args.theme:
        organizer.organize_by_theme(dry_run=not args.execute)
    elif args.both:
        print("Creating dual organization (time and theme)...\n")
        organizer.organize_with_symlinks(dry_run=not args.execute)
        print("\n" + "="*60 + "\n")
        organizer.organize_by_theme(dry_run=not args.execute)
    elif args.watch:
        organizer.start_file_watcher()
    else:
        organizer.generate_report()

if __name__ == '__main__':
    main()