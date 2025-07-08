#!/usr/bin/env python3
"""
Playground Organizer - Automatically organize files by access frequency
"""

import os
import time
import json
import shutil
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import subprocess
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class PlaygroundOrganizer:
    def __init__(self, playground_path):
        self.logger = logging.getLogger(__name__)
        self.playground_path = Path(playground_path)
        self.logger.info(f"Initializing PlaygroundOrganizer with path: {self.playground_path}")
        
        config_filename = os.getenv("PLAYGROUND_CONFIG_FILE", ".playground-config.json")
        self.config_file = self.playground_path / config_filename
        self.access_log = self.playground_path / '.access-log.json'
        
        # Time thresholds (in days) - can be overridden by environment variables
        self.thresholds = {
            'current': int(os.getenv("CURRENT_THRESHOLD", "30")),    # Last 30 days
            'recent': int(os.getenv("RECENT_THRESHOLD", "180")),     # Last 6 months  
            'old': int(os.getenv("OLD_THRESHOLD", "365")),           # Last year
            # Older than 1 year goes to 'archive'
        }
        
        self.load_config()
    
    def _estimate_directory_size(self, path):
        """Fast estimate directory size based on patterns"""
        try:
            name = path.name.lower()
            
            # Quick estimates based on common directory patterns
            if any(pattern in name for pattern in ['node_modules', 'venv', 'env', '.git']):
                return 200 * 1024 * 1024  # 200MB for package/venv dirs
            elif any(pattern in name for pattern in ['__pycache__', '.cache', 'build', 'dist']):
                return 50 * 1024 * 1024   # 50MB for cache dirs
            elif any(pattern in name for pattern in ['models', 'hugging_face', 'datasets']):
                return 500 * 1024 * 1024  # 500MB for ML model dirs
            elif any(pattern in name for pattern in ['test', 'example', 'demo']):
                return 5 * 1024 * 1024    # 5MB for test dirs
            else:
                # Quick scan of first few items only
                file_count = 0
                dir_count = 0
                try:
                    for item in path.iterdir():
                        if item.is_file():
                            file_count += 1
                        elif item.is_dir():
                            dir_count += 1
                        
                        # Stop after checking 20 items for speed
                        if (file_count + dir_count) > 20:
                            break
                except (OSError, PermissionError):
                    pass
                
                # Simple estimation based on counts
                estimated_size = (file_count * 100 * 1024) + (dir_count * 10 * 1024 * 1024)
                return max(estimated_size, 1024 * 1024)  # Minimum 1MB
                
        except Exception as e:
            self.logger.debug(f"Error estimating directory size for {path}: {e}")
            return 10 * 1024 * 1024  # 10MB default estimate
    
    def load_config(self):
        """Load or create configuration"""
        # Define theme mappings
        default_theme_mappings = {
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
        
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
                
                # Ensure all required keys exist in loaded config
                config_updated = False
                if 'theme_mappings' not in self.config:
                    self.config['theme_mappings'] = default_theme_mappings
                    config_updated = True
                if 'use_symlinks' not in self.config:
                    self.config['use_symlinks'] = True
                    config_updated = True
                if 'symlink_base_dir' not in self.config:
                    self.config['symlink_base_dir'] = 'organized'
                    config_updated = True
                if 'organization_modes' not in self.config:
                    self.config['organization_modes'] = ['time', 'theme']
                    config_updated = True
                    
                if config_updated:
                    self.save_config()
        else:
            # Get excluded directories from environment variable or use defaults
            exclude_dirs_env = os.getenv("EXCLUDE_DIRS", ".git,node_modules,.DS_Store,__pycache__,.env")
            excluded_dirs = [dir.strip() for dir in exclude_dirs_env.split(',') if dir.strip()]
            
            self.config = {
                'tracking_enabled': True,
                'auto_organize': False,
                'excluded_dirs': excluded_dirs,
                'last_organized': None,
                'use_symlinks': True,
                'symlink_base_dir': 'organized',
                'theme_mappings': default_theme_mappings,
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
            self.logger.debug(f"Getting stats for: {path}")
            stat_result = path.stat()
            
            # Get size for files and directories
            if path.is_dir():
                # Use fast directory size estimation (skip du command for performance)
                dir_size = self._estimate_directory_size(path)
                self.logger.debug(f"Estimated directory size for {path}: {dir_size} bytes")
            else:
                # For files, use actual file size
                dir_size = stat_result.st_size
                self.logger.debug(f"File size for {path}: {dir_size} bytes")
            
            file_stats = {
                'atime': stat_result.st_atime,  # Access time
                'mtime': stat_result.st_mtime,  # Modification time  
                'ctime': stat_result.st_ctime,  # Creation time
                'size': dir_size,
                'path': str(path)
            }
            self.logger.debug(f"Successfully got stats for {path}: {file_stats}")
            return file_stats
        except (OSError, PermissionError) as e:
            self.logger.error(f"Permission/OS error getting stats for {path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error getting stats for {path}: {e}")
            return None
    
    def detect_theme(self, path):
        """Detect the theme of a file or directory based on its name and extension"""
        name_lower = path.name.lower()
        
        # For files, also consider the extension
        if path.is_file():
            # File extension based detection
            suffix = path.suffix.lower()
            if suffix in ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.go', '.rs', '.rb', '.php']:
                return 'development'
            elif suffix in ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.avi', '.mp3', '.wav', '.mov']:
                return 'media'
            elif suffix in ['.sql', '.db', '.sqlite', '.json', '.csv', '.parquet']:
                return 'data'
            elif suffix in ['.md', '.txt', '.doc', '.docx', '.pdf']:
                return 'learning'
        
        # Name-based detection for both files and directories
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
        self.logger.info("Starting analyze_access_patterns")
        now = time.time()
        results = {
            'current': [],
            'recent': [], 
            'old': [],
            'archive': []
        }
        
        try:
            self.logger.info(f"Scanning directory: {self.playground_path}")
            if not self.playground_path.exists():
                self.logger.error(f"Playground path does not exist: {self.playground_path}")
                return results
                
            if not self.playground_path.is_dir():
                self.logger.error(f"Playground path is not a directory: {self.playground_path}")
                return results
                
            items = list(self.playground_path.iterdir())
            self.logger.info(f"Found {len(items)} items in playground directory")
            
            for item in items:
                self.logger.debug(f"Processing item: {item}")
                
                # Skip most hidden files and directories, but include some important ones
                if item.name.startswith('.'):
                    # Include some important hidden files
                    important_hidden = ['.gitignore', '.env.example', '.npmignore', '.dockerignore', 
                                      '.editorconfig', '.prettierrc', '.eslintrc', '.gitattributes']
                    if item.name not in important_hidden:
                        self.logger.debug(f"Skipping hidden item: {item}")
                        continue
                    
                # Skip excluded directories (only applies to directories)
                if item.is_dir() and item.name in self.config['excluded_dirs']:
                    self.logger.debug(f"Skipping excluded directory: {item}")
                    continue
                    
                try:
                    stats = self.get_file_stats(item)
                    if not stats:
                        self.logger.warning(f"Failed to get stats for: {item}")
                        continue
                        
                    # Use the most recent of access or modification time
                    last_used = max(stats['atime'], stats['mtime'])
                    days_since_used = (now - last_used) / (24 * 3600)
                    
                    stats['days_since_used'] = days_since_used
                    stats['last_used_date'] = datetime.fromtimestamp(last_used).strftime('%Y-%m-%d')
                    
                    # Categorize by access frequency
                    if days_since_used <= self.thresholds['current']:
                        results['current'].append(stats)
                        category = 'current'
                    elif days_since_used <= self.thresholds['recent']:
                        results['recent'].append(stats)
                        category = 'recent'
                    elif days_since_used <= self.thresholds['old']:
                        results['old'].append(stats)
                        category = 'old'
                    else:
                        results['archive'].append(stats)
                        category = 'archive'
                        
                    self.logger.debug(f"Categorized {item.name} as {category} ({days_since_used:.1f} days)")
                    
                except Exception as e:
                    self.logger.error(f"Error processing item {item}: {e}")
                    continue
            
            # Sort each category by most recently used
            for category in results:
                results[category].sort(key=lambda x: x['days_since_used'])
                
            total_files = sum(len(files) for files in results.values())
            self.logger.info(f"Analysis complete. Found {total_files} files total")
            for category, files in results.items():
                self.logger.info(f"  {category}: {len(files)} files")
                
        except Exception as e:
            self.logger.error(f"Error in analyze_access_patterns: {e}")
            raise
            
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
        
        actions = []
        
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
                
                action = f"Create theme symlink: {path.name} -> {theme}/{path.name}"
                actions.append(action)
                print(f"  • {path.name:30} -> {theme:15} {size_mb:8.1f}MB")
                
                if not dry_run:
                    if self.create_symlink(path, target_link):
                        print(f"    ✓ Created symlink: {target_link}")
        
        if not dry_run:
            print(f"\nTheme organization complete. Symlinks created in: {theme_base}")
        
        return actions
    
    def organize_with_symlinks(self, dry_run=True):
        """Organize files by time with symbolic links instead of moving"""
        analysis = self.analyze_access_patterns()
        symlink_base = self.playground_path / self.config['symlink_base_dir'] / 'by-time'
        
        print(f"{'DRY RUN - ' if dry_run else ''}Symlink Organization by Time:")
        print("=" * 50)
        
        actions = []
        
        for category, files in analysis.items():
            if not files:
                continue
            
            print(f"\n⏰ {category.upper()} ({len(files)} items):")
            category_dir = symlink_base / category
            
            for file_info in files:
                path = Path(file_info['path'])
                target_link = category_dir / path.name
                size_mb = file_info['size'] / (1024 * 1024)
                
                action = f"Create symlink: {path.name} -> {category}/{path.name}"
                actions.append(action)
                print(f"  • {path.name:30} {file_info['last_used_date']:12} {size_mb:8.1f}MB")
                
                if not dry_run:
                    category_dir.mkdir(parents=True, exist_ok=True)
                    if self.create_symlink(path, target_link):
                        print(f"    ✓ Created symlink: {target_link}")
        
        if not dry_run:
            print(f"\nTime-based organization complete. Symlinks created in: {symlink_base}")
        
        return actions
    
    def start_file_watcher(self):
        """Start monitoring file access using fswatch"""
        print("Starting file access monitoring...")
        print("Press Ctrl+C to stop")
        
        try:
            # Use fswatch to monitor file access
            fswatch_path = os.getenv("FSWATCH_PATH", "fswatch")
            cmd = [
                fswatch_path, 
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