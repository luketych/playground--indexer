#!/usr/bin/env python3
"""
Tests for playground-organizer.py
"""

import os
import sys
import tempfile
import shutil
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
# import pytest  # Optional, only used if available

# Import the module from the package structure
import sys
sys.path.insert(0, 'src')
from playground_organizer import PlaygroundOrganizer


class TestPlaygroundOrganizer:
    """Test cases for PlaygroundOrganizer class"""

    def setup_method(self):
        """Set up test environment before each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.organizer = PlaygroundOrganizer(self.temp_path)
        
        # Create test directories with different themes
        self.test_dirs = [
            'ai-project',
            'gpt-experiment', 
            'stock-tracker',
            'todo-app',
            'data-pipeline',
            'video-editor',
            'dev-tools',
            'learning-course',
            'random-stuff'
        ]
        
        for dir_name in self.test_dirs:
            dir_path = self.temp_path / dir_name
            dir_path.mkdir()
            # Create a test file to give the directory some content
            (dir_path / 'test.txt').write_text('test content')
            
    def teardown_method(self):
        """Clean up after each test"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_theme_detection(self):
        """Test theme detection based on directory names"""
        test_cases = [
            ('ai-project', 'ai'),
            ('gpt-experiment', 'ai'),
            ('stock-tracker', 'stocks'),
            ('todo-app', 'productivity'),
            ('data-pipeline', 'data'),
            ('video-editor', 'media'),
            ('dev-tools', 'development'),
            ('learning-course', 'learning'),
            ('random-stuff', 'misc')
        ]
        
        for dir_name, expected_theme in test_cases:
            dir_path = self.temp_path / dir_name
            detected_theme = self.organizer.detect_theme(dir_path)
            assert detected_theme == expected_theme, f"Expected {expected_theme} for {dir_name}, got {detected_theme}"

    def test_organize_by_theme_dry_run(self):
        """Test --theme option with dry run"""
        with patch('builtins.print') as mock_print:
            self.organizer.organize_by_theme(dry_run=True)
            
            # Check that print was called with expected content
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any('DRY RUN - Theme-based Organization:' in call for call in print_calls)
            assert any('AI' in call for call in print_calls)
            assert any('STOCKS' in call for call in print_calls)
            assert any('PRODUCTIVITY' in call for call in print_calls)

    def test_organize_by_theme_execute(self):
        """Test --theme option with execution"""
        self.organizer.organize_by_theme(dry_run=False)
        
        # Check that the organized directory structure was created
        theme_base = self.temp_path / 'organized' / 'by-theme'
        assert theme_base.exists()
        
        # Check that theme directories were created
        expected_themes = ['ai', 'stocks', 'productivity', 'data', 'media', 'development', 'learning', 'misc']
        for theme in expected_themes:
            theme_dir = theme_base / theme
            assert theme_dir.exists(), f"Theme directory {theme} should exist"
        
        # Check that symlinks were created
        ai_dir = theme_base / 'ai'
        assert (ai_dir / 'ai-project').is_symlink()
        assert (ai_dir / 'gpt-experiment').is_symlink()
        
        stocks_dir = theme_base / 'stocks'
        assert (stocks_dir / 'stock-tracker').is_symlink()
        
        productivity_dir = theme_base / 'productivity'
        assert (productivity_dir / 'todo-app').is_symlink()

    def test_organize_with_symlinks_dry_run(self):
        """Test --symlinks option with dry run"""
        with patch('builtins.print') as mock_print:
            self.organizer.organize_with_symlinks(dry_run=True)
            
            # Check that print was called with expected content
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any('DRY RUN - Symlink Organization by Time:' in call for call in print_calls)
            assert any('CURRENT' in call or 'RECENT' in call or 'OLD' in call or 'ARCHIVE' in call for call in print_calls)

    def test_organize_with_symlinks_execute(self):
        """Test --symlinks option with execution"""
        self.organizer.organize_with_symlinks(dry_run=False)
        
        # Check that the organized directory structure was created
        time_base = self.temp_path / 'organized' / 'by-time'
        assert time_base.exists()
        
        # Check that time categories were created (at least one should exist)
        time_categories = ['current', 'recent', 'old', 'archive']
        category_exists = any((time_base / cat).exists() for cat in time_categories)
        assert category_exists, "At least one time category should exist"

    def test_both_option_dry_run(self):
        """Test --both option with dry run"""
        with patch('builtins.print') as mock_print:
            # Simulate the --both option behavior
            self.organizer.organize_with_symlinks(dry_run=True)
            self.organizer.organize_by_theme(dry_run=True)
            
            # Check that both organization methods were called
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any('DRY RUN - Symlink Organization by Time:' in call for call in print_calls)
            assert any('DRY RUN - Theme-based Organization:' in call for call in print_calls)

    def test_both_option_execute(self):
        """Test --both option with execution"""
        # Simulate the --both option behavior
        self.organizer.organize_with_symlinks(dry_run=False)
        self.organizer.organize_by_theme(dry_run=False)
        
        # Check that both organization structures were created
        organized_base = self.temp_path / 'organized'
        assert organized_base.exists()
        
        time_base = organized_base / 'by-time'
        theme_base = organized_base / 'by-theme'
        
        assert time_base.exists(), "Time-based organization should exist"
        assert theme_base.exists(), "Theme-based organization should exist"

    def test_create_symlink_functionality(self):
        """Test symlink creation functionality"""
        source_dir = self.temp_path / 'source-dir'
        source_dir.mkdir()
        
        target_dir = self.temp_path / 'target-dir'
        target_dir.mkdir()
        
        target_link = target_dir / 'link-to-source'
        
        # Test successful symlink creation
        result = self.organizer.create_symlink(source_dir, target_link)
        assert result is True
        assert target_link.is_symlink()
        assert target_link.resolve() == source_dir.resolve()
        
        # Test overwriting existing symlink
        result = self.organizer.create_symlink(source_dir, target_link)
        assert result is True
        assert target_link.is_symlink()

    def test_create_symlink_existing_file(self):
        """Test symlink creation when target already exists as a file"""
        source_dir = self.temp_path / 'source-dir'
        source_dir.mkdir()
        
        target_file = self.temp_path / 'existing-file.txt'
        target_file.write_text('existing content')
        
        # Should not overwrite existing file
        result = self.organizer.create_symlink(source_dir, target_file)
        assert result is False
        assert target_file.is_file()
        assert not target_file.is_symlink()

    @patch('subprocess.run')
    def test_get_file_stats_with_size(self, mock_subprocess):
        """Test file stats calculation including directory size"""
        # Mock subprocess to return directory size
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "1024\t/test/dir"
        
        test_dir = self.temp_path / 'test-dir'
        test_dir.mkdir()
        
        stats = self.organizer.get_file_stats(test_dir)
        
        assert stats is not None
        assert 'atime' in stats
        assert 'mtime' in stats
        assert 'ctime' in stats
        assert 'size' in stats
        assert stats['size'] == 1024 * 1024  # Should be converted from KB to bytes

    def test_theme_mappings_configuration(self):
        """Test that theme mappings are properly configured"""
        expected_themes = ['ai', 'productivity', 'stocks', 'development', 'data', 'media', 'tools', 'learning', 'misc']
        
        for theme in expected_themes:
            assert theme in self.organizer.config['theme_mappings']
        
        # Test that AI theme has expected keywords
        ai_keywords = self.organizer.config['theme_mappings']['ai']
        assert 'gpt' in ai_keywords
        assert 'ai-' in ai_keywords
        assert 'ml' in ai_keywords

    def test_excluded_directories(self):
        """Test that excluded directories are not processed"""
        # Create excluded directories
        excluded_dirs = ['.git', 'node_modules', '.DS_Store', '__pycache__']
        for dir_name in excluded_dirs:
            (self.temp_path / dir_name).mkdir()
        
        # Analyze patterns - excluded directories should not appear
        analysis = self.organizer.analyze_access_patterns()
        all_files = []
        for category in analysis.values():
            all_files.extend([Path(f['path']).name for f in category])
        
        for excluded_dir in excluded_dirs:
            assert excluded_dir not in all_files

    def test_configuration_persistence(self):
        """Test that configuration is saved and loaded correctly"""
        # Modify configuration
        self.organizer.config['custom_setting'] = 'test_value'
        self.organizer.save_config()
        
        # Create new organizer instance
        new_organizer = PlaygroundOrganizer(self.temp_path)
        
        # Check that configuration was loaded
        assert new_organizer.config['custom_setting'] == 'test_value'

    def test_organize_structure_creation(self):
        """Test creation of organization structures"""
        # Test time-based structure
        self.organizer.create_organization_structure('time')
        for category in ['current', 'recent', 'old', 'archive']:
            assert (self.temp_path / category).exists()
        
        # Test theme-based structure
        self.organizer.create_organization_structure('theme')
        theme_base = self.temp_path / 'organized' / 'by-theme'
        assert theme_base.exists()
        for theme in self.organizer.config['theme_mappings']:
            assert (theme_base / theme).exists()
        
        # Test both structures
        self.organizer.create_organization_structure('both')
        # Should have both time and theme structures


if __name__ == '__main__':
    # Run the tests
    import subprocess
    import sys
    
    try:
        # Try to run with pytest if available
        result = subprocess.run([sys.executable, '-m', 'pytest', __file__, '-v'], 
                              capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        sys.exit(result.returncode)
    except FileNotFoundError:
        # Fallback to running tests manually
        print("pytest not available, running tests manually...")
        
        # Create test instance and run tests
        test_instance = TestPlaygroundOrganizer()
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
        
        passed = 0
        failed = 0
        
        for method_name in test_methods:
            try:
                test_instance.setup_method()
                method = getattr(test_instance, method_name)
                method()
                test_instance.teardown_method()
                print(f"✓ {method_name}")
                passed += 1
            except Exception as e:
                print(f"✗ {method_name}: {e}")
                failed += 1
        
        print(f"\nResults: {passed} passed, {failed} failed")
        sys.exit(0 if failed == 0 else 1)