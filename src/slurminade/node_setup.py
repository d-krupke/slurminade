"""
Node setup functionality for executing initialization code on Slurm nodes.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable

from .guard import on_slurm_node

# Module-level logger for node setup operations
_logger = logging.getLogger("slurminade.node_setup")

_no_setup = False


def disable_setup() -> None:
    """
    Disable the setup function.

    This is useful for testing or when you want to skip node initialization.
    """
    global _no_setup  # noqa: PLW0603
    _logger.info("Node setup disabled")
    _no_setup = True


def node_setup(func: Callable[[], None]) -> Callable[[], None]:
    """
    Decorator: Call this function on the node before running any function calls.

    The decorated function will be executed once on each Slurm node before
    any distributed tasks are run. This is useful for setting up the environment,
    loading modules, or initializing resources.

    Args:
        func: Setup function to call (must take no arguments)

    Returns:
        The decorated function

    Raises:
        ValueError: If the setup function has any parameters

    Example:
        @node_setup
        def setup_environment():
            import os
            os.environ['MY_VAR'] = 'value'
    """
    name = getattr(func, "__name__", repr(func))
    if on_slurm_node() and not _no_setup:
        _logger.info("Executing node setup function: %s", name)
        func()
        _logger.debug("Node setup completed: %s", name)
    else:
        # check if the function has no arguments
        sig = inspect.signature(func)
        if sig.parameters:
            _logger.error("Node setup function %s has parameters", name)
            msg = "The node setup function must not have any arguments."
            raise ValueError(msg)
        _logger.debug("Registered node setup function: %s", name)
    return func
