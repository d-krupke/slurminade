import inspect
import typing
from .guard import on_slurm_node

def node_setup(func: typing.Callable):
    """
    Decorator: Call this function on the node before running any function calls.
    """
    if on_slurm_node():
        func()
    else:
        # check if the function has no arguments
        sig = inspect.signature(func)
        if sig.parameters:
            msg = "The node setup function must not have any arguments."
            raise ValueError(msg)
    return func
