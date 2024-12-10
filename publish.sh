#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Default version increment type
VERSION_INCREMENT="patch"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --version)
            VERSION_INCREMENT="$2"
            shift 2
            ;;
        *)
            echo "Usage: $0 [--version {patch|minor|major}]"
            exit 1
            ;;
    esac
done

# Validate version increment type
if [[ ! "$VERSION_INCREMENT" =~ ^(patch|minor|major)$ ]]; then
    echo "Invalid version type: $VERSION_INCREMENT. Must be one of: patch, minor, major."
    exit 1
fi

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Poetry is not installed. Please install it first."
    exit 1
fi

# Check if Twine is installed
if ! poetry run python -c "import twine" &> /dev/null; then
    echo "Twine is not installed. Installing now..."
    poetry add --group dev twine
fi

# Increment version using Poetry
echo "Incrementing version ($VERSION_INCREMENT)..."
poetry version "$VERSION_INCREMENT"
NEW_VERSION=$(poetry version --short)

# Synchronize the [project] version in pyproject.toml
echo "Synchronizing [project] version in pyproject.toml to $NEW_VERSION..."
sed -i.bak "s/^version = \".*\"$/version = \"$NEW_VERSION\"/" pyproject.toml

# Remove the dist directory if it exists
if [ -d "dist" ]; then
    echo "Removing existing dist directory..."
    rm -rf dist
fi

# Build the package
echo "Building package version $NEW_VERSION..."
poetry run python -m build

# Upload the package to PyPI with the specified .pypirc file
if [ ! -f ".pypirc" ]; then
    echo "Error: .pypirc file not found in the project directory. Please create one."
    exit 1
fi

echo "Uploading package version $NEW_VERSION to PyPI using .pypirc..."
poetry run twine upload --config-file .pypirc dist/*

# Clean up backup file created by sed
rm -f pyproject.toml.bak

echo "Package version $NEW_VERSION has been successfully published, versions are in sync, and the .pypirc file was used for upload!"