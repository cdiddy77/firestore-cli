# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python CLI tool for interacting with Google Firestore databases. It provides two main commands:
- `fsquery`: Query and read documents from Firestore collections
- `fsupdate`: Create, update, or delete Firestore documents

The project is published to PyPI as `firestore-cli` and uses Poetry for dependency management alongside setuptools for builds.

## Development Commands

### Setup
```bash
# Install dependencies (uses Poetry)
poetry install

# Activate virtual environment
poetry shell
# OR if using pre-created .venv:
source .venv/bin/activate
```

### Building and Publishing
```bash
# Build package for distribution
poetry run python -m build

# Publish to PyPI (handles version bumping, build, and upload)
# Options: --version {patch|minor|major}
./publish.sh --version patch
```

### Testing with Local Emulator
```bash
# Set environment variable for local Firestore emulator (port 8080 example)
export FIRESTORE_EMULATOR_HOST="127.0.0.1:8080"

# Test fsquery command
fsquery --credentials /path/to/credentials.json --path collection-name

# Test fsupdate command
fsupdate --credentials /path/to/credentials.json --path collection-name --add --doc document.json
```

## Code Architecture

### Entry Points
The package defines two CLI commands in `pyproject.toml` under `[project.scripts]`:
- `fsquery` → `firestore_cli.fsquery:main`
- `fsupdate` → `firestore_cli.fsupdate:main`

### Core Modules

**`firestore_cli/fsquery.py`** (7394 bytes, ~196 lines)
- Main query interface using Click for argument parsing
- `execute_query()`: Handles collection/collection group queries, filtering with FieldFilter, ordering, and limits
- `FirestoreEncoder` (custom JSONEncoder): Critical for serializing Firestore-specific types:
  - `DocumentReference`: Follows references recursively up to specified depth (controlled by `--recursion` flag)
  - `DocumentSnapshot`: Converts to dictionary representation
  - `DatetimeWithNanoseconds`: Converts to RFC 3339 format
  - Includes circular reference protection via recursion depth tracking
- `convert_string()`: Helper to parse type-prefixed values (e.g., "int:42", "bool:true", "float:3.14")
- Query format: `--where "field operation value"` (space-separated, supports multiple --where flags)
- Document ID queries bypass stream() and use direct document().get()

**`firestore_cli/fsupdate.py`** (2022 bytes, ~70 lines)
- CRUD operations interface using Click
- `execute_update()`: Routes to set/add/update/delete operations
- Operations require `--doc` path to JSON file (except delete)
- Returns operation results directly (document ID for add, write result for others)

**Shared initialization**: Both modules use `initialize_firestore()` to handle:
- Certificate-based authentication (`--credentials` path)
- Application Default Credentials (fallback)
- Firebase Admin SDK initialization

### Credentials Handling
Two methods supported (in order of precedence):
1. `--credentials` CLI option pointing to JSON credentials file
2. `GOOGLE_APPLICATION_CREDENTIALS` environment variable

### Reference Dereferencing Feature
The `--recursion` flag in fsquery controls how DocumentReference fields are handled:
- `0` (default): References output as strings `"ref: path/to/doc"`
- `>0`: Fetches referenced documents and embeds them inline, decrements counter per level
- When recursion limit reached: Outputs as `"xref: path/to/doc"`
- Includes basic circular reference protection (though not perfect per code comments)

### Build System Dual Configuration
The project uses both Poetry and setuptools:
- `[tool.poetry]`: Poetry-specific configuration for development
- `[project]`: Standard Python packaging metadata (PEP 621)
- `[build-system]`: Uses setuptools as the actual build backend
- Version must be synchronized manually between `[tool.poetry]` and `[project]` sections (handled by publish.sh script)

### Publishing Workflow
The `publish.sh` script automates:
1. Version increment via `poetry version {patch|minor|major}`
2. Sync version in `[project]` section using sed
3. Clean dist directory
4. Build with `python -m build`
5. Upload to PyPI with twine using `.pypirc` config file
6. Cleanup temporary files

## Key Implementation Details

- No unit tests currently exist in the repository
- Query operations use Firebase Admin SDK's `FieldFilter` for WHERE clauses
- Output is always JSON format (with optional `--out` file writing)
- The FirestoreEncoder.recursion is a class variable shared across all instances - set before json.dumps() call
- Type conversion in queries supports int:, bool:, float: prefixes to handle non-string values
- Collection group queries use `db.collection_group()` instead of `db.collection()`
