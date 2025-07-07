#!/usr/bin/env python3
"""
Test runner for playground organization system
"""

import unittest
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_unit_tests():
    """Run unit tests"""
    print("Running unit tests...")
    loader = unittest.TestLoader()
    suite = loader.discover('unit', pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()

def run_integration_tests():
    """Run integration tests"""
    print("\nRunning integration tests...")
    loader = unittest.TestLoader()
    suite = loader.discover('integration', pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()

def run_e2e_tests():
    """Run end-to-end tests"""
    print("\nRunning end-to-end tests...")
    loader = unittest.TestLoader()
    suite = loader.discover('e2e', pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()

def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("PLAYGROUND ORGANIZER TEST SUITE")
    print("=" * 60)
    
    # Change to tests directory
    os.chdir(Path(__file__).parent)
    
    results = []
    
    # Run each test suite
    results.append(run_unit_tests())
    results.append(run_integration_tests())
    results.append(run_e2e_tests())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    test_types = ['Unit Tests', 'Integration Tests', 'End-to-End Tests']
    for i, (test_type, passed) in enumerate(zip(test_types, results)):
        status = "PASSED" if passed else "FAILED"
        print(f"{test_type:20} {status}")
    
    all_passed = all(results)
    overall_status = "PASSED" if all_passed else "FAILED"
    print(f"\nOverall Status: {overall_status}")
    
    return all_passed

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run playground organizer tests')
    parser.add_argument('--unit', action='store_true', help='Run only unit tests')
    parser.add_argument('--integration', action='store_true', help='Run only integration tests')
    parser.add_argument('--e2e', action='store_true', help='Run only end-to-end tests')
    
    args = parser.parse_args()
    
    # Change to tests directory
    os.chdir(Path(__file__).parent)
    
    success = True
    
    if args.unit:
        success = run_unit_tests()
    elif args.integration:
        success = run_integration_tests()
    elif args.e2e:
        success = run_e2e_tests()
    else:
        success = run_all_tests()
    
    sys.exit(0 if success else 1)