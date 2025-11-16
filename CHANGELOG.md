# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Coverage reporting configuration with pytest-cov
- Comprehensive test suite for configuration management (test_conf.py)
- Comprehensive test suite for SlurmOptions class (test_options.py)
- Optional development dependencies in pyproject.toml
- CONTRIBUTING.md with detailed development guidelines
- CHANGELOG.md for tracking project changes
- Support for Python 3.11, 3.12, and 3.13
- Better type annotations in options.py
- Improved error messages for SlurmOptions hashing failures

### Changed
- **BREAKING**: Minimum Python version raised from 3.8 to 3.9
- **BREAKING**: SlurmOptions refactored from dict inheritance to composition pattern
  - Still provides dict-like interface for backward compatibility
  - Better type safety and cleaner implementation
  - More descriptive error messages
- Replaced `os.system()` with `subprocess.run()` for better security and error handling
- Refactored `create_slurminade_command()` to return list instead of string
- Removed use of `shell=True` in subprocess calls where not needed
- Improved `shell()` function to handle both string and list commands safely
- Updated all tooling configurations for Python 3.9+ (ruff, mypy, pylint)
- Modernized build system with dynamic versioning via setuptools_scm
- Updated CI/CD pipeline (GitHub Actions):
  - Added separate lint and test jobs
  - Added mypy type checking to CI
  - Added ruff linting to CI
  - Extended Python version matrix to 3.9-3.13
  - Added coverage upload to Codecov
  - Updated actions to v4/v5 (latest versions)
- Updated pre-commit hooks to latest versions:
  - black: 23.3.0 → 24.10.0
  - ruff: v0.5.1 → v0.8.4
  - mypy: v1.3.0 → v1.13.0
  - prettier: v3.0.0-alpha.9 → v3.3.3
  - pre-commit-hooks: v4.4.0 → v5.0.0
- Project status from Alpha to Beta in classifiers
- Extended keywords in package metadata

### Fixed
- **CRITICAL**: Fixed `set_default_configuration()` bug where global state wasn't being modified
- Security: Improved command injection protection in subprocess calls
- Type safety: SlurmOptions now raises clear TypeError for unhashable values

### Improved
- Test coverage increased from ~50% to ~53%
- Code quality with modern linting rules
- Type annotations coverage
- Documentation and inline comments
- Error handling and validation

### Development
- Added comprehensive coverage configuration in pyproject.toml
- Configured pytest-cov with branch coverage
- Set up HTML coverage reports
- Improved development workflow documentation

## [1.1.2] - 2024-11-15

### Fixed
- Fixed some old job ids instead of references
- Lots of cleaning up
- Comments

## [1.1.1] - Previous Release

### Fixed
- Bug when there is some unexpected output such as deprecation warnings on import

## [1.1.0] - Previous Release

### Added
- Slurminade can now be called from iPython

### Changed
- `exec` has been renamed `shell` to prevent confusion with Python's built-in exec

## [1.0.1] - Previous Release

### Changed
- Dispatcher now returns job references instead of job ids

## [0.10.1] - Previous Release

### Fixed
- Listing functions will no longer execute setup functions

## [0.10.0] - Previous Release

### Changed
- `Batch` is now named `JobBundling`

### Added
- Method `join` for easier synchronization
- `shell` allows executing commands with uniform syntax
- Functions can be called with `distribute_and_wait`
- Check command: `python3 -m slurminade.check --partition YOUR_PARTITION --constraint YOUR_CONSTRAINT`

---

## Upgrade Guide

### From 1.1.x to 2.0.0 (unreleased)

#### Python Version

Minimum Python version is now 3.9. If you're using Python 3.8, you must upgrade to Python 3.9 or higher.

```bash
# Check your Python version
python --version
```

#### SlurmOptions Changes

`SlurmOptions` no longer inherits from `dict`, but still provides a dict-like interface.
Most code should work without changes, but if you relied on `isinstance(opts, dict)`:

**Before:**
```python
if isinstance(opts, dict):
    process_dict(opts)
```

**After:**
```python
if isinstance(opts, (dict, SlurmOptions)):
    process_dict(opts.as_dict() if isinstance(opts, SlurmOptions) else opts)
```

Or simply use the dict-like interface:
```python
# These still work
opts["partition"]
opts.get("memory", "4GB")
opts.items()
```

#### Unhashable Values

`SlurmOptions` now raises a clear `TypeError` if you try to hash it with unhashable values:

```python
opts = SlurmOptions(partition="test", bad_list=[1, 2, 3])
hash(opts)  # TypeError: Cannot hash SlurmOptions with unhashable values...
```

**Fix:** Use hashable types (strings, numbers, tuples) instead of lists/dicts.

[unreleased]: https://github.com/d-krupke/slurminade/compare/v1.1.2...HEAD
[1.1.2]: https://github.com/d-krupke/slurminade/releases/tag/v1.1.2
