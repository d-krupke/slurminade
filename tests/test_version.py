"""Verify that __version__ in __init__.py matches pyproject.toml."""

from pathlib import Path

import slurminade


def test_version_matches_pyproject():
    """The version string in code must stay in sync with pyproject.toml."""
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    # Find the version line in pyproject.toml
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("version") and "=" in stripped:
            # Parse: version = "1.2.0"
            pyproject_version = stripped.split("=", 1)[1].strip().strip('"')
            break
    else:
        msg = "Could not find 'version' in pyproject.toml"
        raise AssertionError(msg)

    assert slurminade.__version__ == pyproject_version, (
        f"Version mismatch: __init__.py has {slurminade.__version__!r}, "
        f"pyproject.toml has {pyproject_version!r}"
    )
