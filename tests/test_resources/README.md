# Test Resources Directory

This directory contains mock files and folders used for testing the playground organizer functionality.

## Structure

- Mock playground directories are created here during test execution
- Test data generators store their output here
- Results from mock restructuring operations are stored here
- Each test creates its own subdirectory to avoid conflicts

## Usage

Test files automatically create and clean up their resources in this directory:
- Unit tests: `unit_test_<pid>/`
- Integration tests: `integration_test_<pid>/`
- E2E tests: `e2e_test_<pid>/`
- Generator tests: `generator_<pid>/`

## Cleanup

Test resources are automatically cleaned up after each test run. If you need to manually clean up, you can safely delete the contents of this directory.