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

3. **Work in writable location**: Copy files to `/tmp/project` since the workspace is mounted read-only

4. **Install with dev dependencies**: Use `uv pip install -e '.[dev]'` to get pytest and other test dependencies

5. **Run with uv**: Use `uv run pytest tests/unit` to ensure proper environment activation

### Why This Approach?

- The local `.venv` folder contains packages compiled for macOS that won't work in the Linux container
- Copying the `.venv` causes issues with binary extensions like greenlet (used by Playwright)
- A clean install in the container ensures all dependencies are compiled for the correct platform
- Using `git ls-files` ensures we only copy source code and configuration files, not build artifacts
