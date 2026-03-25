"""
This file saves the default configuration for slurm.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from .options import SlurmOptions

CONFIG_NAME = ".slurminade_default.json"

# Module-level logger for consistent logging
_logger = logging.getLogger("slurminade.conf")

__default_conf: dict[str, Any] = {}


def _load_conf(path: Path) -> dict[str, Any]:
    """
    Load configuration from a JSON file.

    Args:
        path: Path to the configuration file

    Returns:
        Dictionary of configuration options, empty dict if file doesn't exist or fails
    """
    try:
        if path.is_file():
            _logger.debug("Loading configuration from %s", path)
            with path.open() as f:
                conf = json.load(f)
                _logger.debug("Loaded %d configuration keys from %s", len(conf), path)
                return conf
        else:
            _logger.debug("Configuration file not found: %s", path)
            return {}
    except Exception as e:
        _logger.error(
            "Could not open default configuration %s: %s", path, e
        )
    return {}


def update_default_configuration(
    conf: dict[str, Any] | None = None, **kwargs: Any
) -> None:
    """
    Adds or updates the default configuration.

    Args:
        conf: A dictionary with the configuration
        **kwargs: Configuration parameters (alternative to giving a dictionary)
    """
    if conf:
        _logger.debug("Updating configuration with %d keys from dict", len(conf))
        _logger.debug("Configuration update: %s", conf)
        __default_conf.update(conf)
    if kwargs:
        _logger.debug("Updating configuration with %d keys from kwargs", len(kwargs))
        _logger.debug("Configuration update: %s", kwargs)
        __default_conf.update(kwargs)


def _load_default_conf() -> None:
    """Load default configuration from standard locations."""
    _logger.debug("Loading default configuration from standard locations")

    # Try home directory
    path = Path.home() / CONFIG_NAME
    update_default_configuration(_load_conf(path))

    # Try XDG_CONFIG_HOME
    if "XDG_CONFIG_HOME" in os.environ:
        path = Path(os.environ["XDG_CONFIG_HOME"]) / "slurminade" / CONFIG_NAME
        update_default_configuration(_load_conf(path))

    # Try current directory
    update_default_configuration(_load_conf(Path(CONFIG_NAME)))

    _logger.debug("Default configuration loaded with %d keys", len(__default_conf))


_load_default_conf()


def set_default_configuration(
    conf: dict[str, Any] | None = None, **kwargs: Any
) -> None:
    """
    Replaces the default configuration.

    This will overwrite the default configuration with the given one.

    Args:
        conf: A dictionary with the configuration
        **kwargs: Configuration parameters (alternative to giving a dictionary)
    """
    global __default_conf  # noqa: PLW0603
    _logger.debug("Resetting default configuration")
    __default_conf = {}
    update_default_configuration(conf, **kwargs)


def _get_conf(
    conf: SlurmOptions | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Get merged configuration (default + override).

    Args:
        conf: Optional configuration to merge with defaults

    Returns:
        Merged configuration dictionary
    """
    if conf is None:
        override: dict[str, Any] = {}
    elif isinstance(conf, SlurmOptions):
        override = conf.as_dict()
    else:
        override = conf
    conf_ = __default_conf.copy()
    conf_.update(override)
    return conf_
