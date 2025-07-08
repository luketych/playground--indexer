# Tools and Technologies

## Primary Tools

### uv - Python Package Manager
- **Purpose**: Modern Python package and project manager
- **Usage**: `uv run python script.py`, `uv add package`, `uv sync`
- **Benefits**: Fast dependency resolution, virtual environment management
- **Installation**: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### Python 3.13+
- **Purpose**: Programming language runtime
- **Managed by**: uv (handles version management automatically)
- **Configuration**: `.python-version` file specifies required version

### FastAPI
- **Purpose**: Modern web framework for building APIs
- **Usage**: Web UI backend server
- **Features**: Automatic API documentation, type hints, async support

### Uvicorn
- **Purpose**: ASGI server for running FastAPI applications
- **Usage**: Production-ready web server
- **Integration**: Used by uv for running web applications

### Jinja2
- **Purpose**: Template engine for HTML generation
- **Usage**: Frontend template rendering
- **Features**: Secure templating with auto-escaping

### pytest
- **Purpose**: Testing framework
- **Usage**: `uv run pytest tests/`
- **Features**: Fixtures, parametrized tests, detailed output

## System Dependencies

### fswatch (macOS)
- **Purpose**: File system monitoring
- **Installation**: `brew install fswatch`
- **Usage**: Real-time file access monitoring

### Standard Unix Tools
- `du` - Disk usage calculation
- `find` - File searching
- `stat` - File metadata

## Tools to Avoid

### python/python3 binary
- **Why avoid**: Bypasses uv's dependency management
- **Problem**: Can lead to import issues and dependency conflicts
- **Alternative**: Always use `uv run python` instead of `python` or `python3`

### pip
- **Why avoid**: Conflicts with uv's dependency resolution
- **Problem**: Can create inconsistent dependency states
- **Alternative**: Use `uv add package` instead of `pip install package`

### virtualenv/venv
- **Why avoid**: uv handles virtual environments automatically
- **Problem**: Manual environment management is error-prone
- **Alternative**: Let uv manage environments via `uv run` and `uv sync`

## Best Practices

1. **Always use uv commands**:
   - `uv run python script.py` instead of `python script.py`
   - `uv add package` instead of `pip install package`
   - `uv sync` to ensure dependencies are up to date

2. **Module execution**:
   - `uv run python -m module.name` for running modules
   - `uv run python -m pytest tests/` for testing

3. **Development workflow**:
   - `uv add --dev package` for development dependencies
   - `uv lock` to update lock file
   - `uv run` for all Python execution