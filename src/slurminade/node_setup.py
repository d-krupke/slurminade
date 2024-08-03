import inspect
import typing

from .guard import on_slurm_node

_no_setup = False


def disable_setup():
    """
    Disable the setup function. This is useful for testing.
    """
    global _no_setup  # noqa: PLW0603
    _no_setup = True


def node_setup(func: typing.Callable):
    """
    Decorator: Call this function on the node before running any function calls.
    """
    if on_slurm_node() and not _no_setup:
        func()
    else:
        # check if the function has no arguments
        sig = inspect.signature(func)
        if sig.parameters:
            msg = "The node setup function must not have any arguments."
            raise ValueError(msg)
    return func
