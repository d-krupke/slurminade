# Contributing to Slurminade

Thank you for your interest in contributing to Slurminade! This document provides guidelines and information for contributors.

## Code of Conduct

Please be respectful and constructive in all interactions. We aim to foster an open and welcoming environment.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- A GitHub account

### Development Setup

1. **Fork and clone the repository:**
   ```bash
   git fork https://github.com/d-krupke/slurminade
   cd slurminade
   ```

2. **Install development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

3. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

## Development Workflow

### Running Tests

Run the full test suite:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=slurminade --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Code Quality

We use several tools to maintain code quality:

- **Ruff**: Fast Python linter
- **Black**: Code formatting
- **mypy**: Static type checking
- **pytest**: Testing framework

Run linting:
```bash
ruff check src tests
```

Run type checking:
```bash
mypy src tests
```

Format code:
```bash
ruff format src tests
```

### Pre-commit Hooks

Pre-commit hooks will automatically run on `git commit`. To run manually:
```bash
pre-commit run --all-files
```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-xyz` - New features
- `fix/issue-123` - Bug fixes
- `docs/update-readme` - Documentation updates
- `refactor/cleanup-xyz` - Code refactoring

### Commit Messages

Write clear, concise commit messages:

```
type: Short description (max 50 chars)

Longer explanation if needed (wrap at 72 chars).
Include context, motivation, and implementation details.

Fixes #123
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Pull Request Process

1. **Create a feature branch** from `main`
2. **Make your changes** with tests
3. **Ensure all tests pass** and coverage doesn't decrease
4. **Update documentation** if needed
5. **Submit a pull request** with:
   - Clear title and description
   - Reference to related issues
   - Screenshots (if UI changes)
   - Test results

### Pull Request Checklist

- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] Code follows project style (ruff, black)
- [ ] Type hints added for new code
- [ ] No decrease in test coverage
- [ ] CHANGELOG.md updated (for significant changes)

## Testing Guidelines

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use descriptive test names
- One assertion per test (when possible)
- Use fixtures for common setup

Example:
```python
def test_slurmoptions_basic():
    """Test basic SlurmOptions creation and access."""
    opts = SlurmOptions(partition="test", memory="4GB")
    assert opts["partition"] == "test"
    assert opts["memory"] == "4GB"
```

### Test Coverage

- Aim for >80% coverage for new code
- Focus on critical paths and edge cases
- Don't test for 100% - focus on meaningful coverage

## Code Style

### Python Style

- Follow PEP 8
- Use type hints for all public APIs
- Maximum line length: flexible (ruff will handle)
- Use docstrings for modules, classes, and functions

### Docstring Format

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """
    Brief description of what the function does.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When invalid input is provided
    """
    pass
```

## Project Structure

```
slurminade/
├── src/slurminade/      # Source code
│   ├── __init__.py      # Public API
│   ├── bundling.py      # Job bundling logic
│   ├── conf.py          # Configuration management
│   ├── dispatcher.py    # Task dispatchers
│   ├── function.py      # Function decoration
│   ├── options.py       # Slurm options handling
│   └── ...
├── tests/               # Test files
├── examples/            # Example scripts
├── docs/                # Documentation
└── pyproject.toml       # Project configuration
```

## Release Process

(For maintainers only)

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create and push git tag:
   ```bash
   git tag v1.2.0
   git push origin v1.2.0
   ```
4. GitHub Actions will automatically publish to PyPI

## Getting Help

- **Issues**: https://github.com/d-krupke/slurminade/issues
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: https://slurminade.readthedocs.io/

## Areas for Contribution

We welcome contributions in these areas:

### High Priority
- [ ] Improve test coverage (especially for dispatcher and execute modules)
- [ ] Add more comprehensive type annotations
- [ ] Performance optimizations
- [ ] Better error messages

### Medium Priority
- [ ] Additional examples and use cases
- [ ] Documentation improvements
- [ ] Support for more Slurm features
- [ ] Integration tests

### Low Priority
- [ ] Code refactoring
- [ ] Developer tools
- [ ] CI/CD improvements

## Design Principles

When contributing, please keep these principles in mind:

1. **Simplicity**: Keep the API simple and intuitive
2. **Compatibility**: Maintain backward compatibility when possible
3. **Safety**: Prevent users from accidentally DDoSing infrastructure
4. **Flexibility**: Support both Slurm and non-Slurm environments
5. **Minimal Dependencies**: Only add dependencies when truly necessary

## Questions?

Don't hesitate to ask! Open an issue or discussion if you're unsure about anything.

Thank you for contributing to Slurminade! 🎉
