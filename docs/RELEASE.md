# Release Guide

## Prerequisites

- PyPI token saved in GitHub repository secret `PYPI_API_TOKEN`.
- Version bumped in `pyproject.toml`.
- Changelog updated.

## Steps

1. Run full checks locally:
   - `make check`
2. Commit changes and push branch.
3. Create and push a version tag:
   - `git tag v0.1.0`
   - `git push origin v0.1.0`
4. GitHub Actions workflow `release` will:
   - build distribution files
   - upload to PyPI (if token exists)
   - create GitHub release with artifacts
