# AI Hints

This file contains information learned during development to help AI assistants work with this project more effectively.

## Running Unit Tests

### Command

To run unit tests in a Docker container using the Astral UV container:

```bash
docker run --rm \
  -v "$(pwd):/workspace:ro" \
  -e HOME=/tmp \
  -e XDG_CACHE_HOME=/tmp/.cache \
  -e PYTHONUNBUFFERED=1 \
  ghcr.io/astral-sh/uv:python3.13-bookworm \
  bash -c "
    git config --global --add safe.directory /workspace && \
    mkdir -p /tmp/project && \
    cd /workspace && \
    git ls-files -z | xargs -0 -I {} cp --parents {} /tmp/project/ && \
    cd /tmp/project && \
    uv venv && \
    uv pip install -e '.[dev]' --quiet && \
    uv run pytest tests/unit
  "
```

### Key Points

1. **Use Python 3.13 in Astral UV container**: `ghcr.io/astral-sh/uv:python3.13-bookworm`

2. **Copy only git-tracked files**: Use `git ls-files -z | xargs -0 -I {} cp --parents {}` to avoid copying:

   - `.venv` (has macOS-specific compiled extensions that won't work in Linux container)
   - `__pycache__`, `.pytest_cache`, etc.
   - Other .gitignored files

   When creating new files, these won't be tracked by git yet, so the above statement will not copy them.
   In this case, use a combination of the above statement, and separate copy statements for individual new files and/or directories.

3. **Work in writable location**: Copy files to `/tmp/project` since the workspace is mounted read-only

4. **Install with dev dependencies**: Use `uv pip install -e '.[dev]'` to get pytest and other test dependencies

5. **Run with uv**: Use `uv run pytest tests/unit` to ensure proper environment activation

### Why This Approach?

- The local `.venv` folder contains packages compiled for macOS that won't work in the Linux container
- Copying the `.venv` causes issues with binary extensions like greenlet (used by Playwright)
- A clean install in the container ensures all dependencies are compiled for the correct platform
- Using `git ls-files` ensures we only copy source code and configuration files, not build artifacts

## Running Type Checks

### Pyright (PyLance)

To run type checks using Pyright (same type checker that PyLance uses in VS Code):

```bash
docker run --rm \
  -v "$(pwd):/workspace:ro" \
  -e HOME=/tmp \
  -e XDG_CACHE_HOME=/tmp/.cache \
  ghcr.io/astral-sh/uv:python3.13-bookworm \
  bash -c "
    git config --global --add safe.directory /workspace && \
    mkdir -p /tmp/project && \
    cd /workspace && \
    git ls-files -z | xargs -0 -I {} cp --parents {} /tmp/project/ && \
    cd /tmp/project && \
    uv venv && \
    uv pip install -e '.[dev]' --quiet && \
    uv pip install pyright --quiet && \
    uv run pyright src tests
  "
```

### Key Points

1. **Install pyright**: Add `uv pip install pyright --quiet` before running the check
2. **Run on source and tests**: `uv run pyright src tests` checks both directories
3. **Same environment as tests**: Uses the same setup as unit tests for consistency

### Type Checking Best Practices

- **TypedDict optional keys**: Use `.get()` instead of bracket notation for optional keys
  ```python
  # BAD - PyLance error for optional keys
  value = typed_dict["optional_key"]
  
  # GOOD - Safe access for optional keys
  value = typed_dict.get("optional_key")
  ```
- **Run pyright locally**: Catches type errors before they show up in VS Code
- **Fix type errors early**: Type errors can indicate real bugs, not just type issues
