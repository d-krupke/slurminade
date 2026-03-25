"""
The internal datastructure to save all the slurmified functions.
Not relevant for endusers.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, ClassVar

from .execute_cmds import call_slurminade_to_get_function_ids

# Module-level logger for consistent logging
_logger = logging.getLogger("slurminade.function_map")


class FunctionMap:
    """
    The function map assigns functions an id and stores them to be called later.
    This id is reproducible such that the slurm node can retrieve the function
    it is supposed to call just by the id.
    """

    # Needed to save the entry point at the slurm node.
    # The slurm node just executes the file content of a script, so the file name is lost.
    # slurminade will set this value in the beginning to reconstruct it.
    entry_point: str | None = None
    _data: ClassVar[dict[str, Callable]] = {}
    _ids: ClassVar[set[str] | None] = set()

    @staticmethod
    def get_id(func: Callable) -> str:
        """
        Returns the unique id of a function. Necessary to slurmify it.
        Probably not needed by the enduser.
        It uses the function name and its file, which should be sufficient unless you
        do not overwrite a function (which is bad anyway).
        :param func: The function you want the id of.
        :return: The id as string.
        """
        file = inspect.getfile(func)
        if file == "<string>":  # on the slurm node, the functions in the entry point
            # are named `<string>`.
            if not FunctionMap.entry_point:
                msg = "No entry point known."
                raise RuntimeError(msg)
            file = FunctionMap.entry_point
        path = Path(file).resolve()
        return f"{path}:{getattr(func, '__name__', repr(func))}"

    @staticmethod
    def get_readable_name(func_id: str) -> str:
        return func_id.rsplit(":", maxsplit=1)[-1]

    @staticmethod
    def check_compatibility(func: Callable) -> None:
        """
        Throw if the function cannot be assigned an id.
        :param func: The function to be checked.
        :return: None
        """
        name = getattr(func, "__name__", "")
        if (
            not name
            or name == "<lambda>"
            or not inspect.getfile(func)
        ):
            msg = "Can only slurmify proper functions."
            raise ValueError(msg)

    @staticmethod
    def register(func: Callable[..., Any], allow_overwrite: bool = False) -> str:
        """
        Register a function, allowing it to be called just by its id.

        Args:
            func: The function to be stored (must be a proper function)
            allow_overwrite: Whether to allow overwriting existing registrations

        Returns:
            The function's unique ID
        """
        FunctionMap.check_compatibility(func)
        func_id = FunctionMap.get_id(func)

        if func_id in FunctionMap._data and not allow_overwrite:
            _logger.error("Attempted to register duplicate function: %s", func_id)
            msg = "Multiple function definitions!"
            raise RuntimeError(msg)

        FunctionMap._data[func_id] = func
        _logger.debug("Registered slurmified function: %s", func_id)
        _logger.debug("Total registered functions: %d", len(FunctionMap._data))
        return func_id

    @staticmethod
    def exists(func_id: str) -> bool:
        return func_id in FunctionMap._data

    @staticmethod
    def call(
        func_id: str, args: Iterable, kwargs: dict[str, Any]
    ) -> Any:
        """
        Calls a function by its id.
        :param func_id: The id of the function to be called.
        :param args: The positional arguments.
        :param kwargs: The keyword arguments.
        :return: The return value of the function.
        """
        if func_id not in FunctionMap._data:
            msg = f"Function '{func_id}' unknown!"
            raise KeyError(msg)
        return FunctionMap._data[func_id](*args, **kwargs)

    @staticmethod
    def check_id(func_id: str, entry_point: Path) -> bool:
        if FunctionMap._ids is None:
            return True
        if func_id in FunctionMap._ids:
            return True
        try:
            # Try to identify the available function ids when the entry point is known.
            # This can help detect some bugs early on.
            FunctionMap._ids = call_slurminade_to_get_function_ids(entry_point)
        except Exception as e:
            logging.getLogger("slurminade").warning(
                "Cannot verify function ids before submitting to slurm: %s. This is not critical, things will just be more difficult to debug in case you make an error.",
                e,
            )
            FunctionMap._ids = None
            return True
        logging.getLogger("slurminade").info(
            "Entry point '%s' has functions %s",
            entry_point,
            list(FunctionMap._ids),
        )
        return func_id in FunctionMap._ids

    @staticmethod
    def get_all_ids() -> list[str]:
        return list(FunctionMap._data.keys())


def set_entry_point(entry_point: str | Path) -> None:
    """
    This function usually is not necessary for endusers.
    Set a manual entry point. This can allow you to use slurmify from the interactive
    interpreter.
    :param entry_point: A path to the entry point file.
    :return: None
    """
    entry_point = Path(entry_point)
    if not entry_point.is_file() or not str(entry_point).endswith(".py"):
        msg = f"Illegal entry point ({entry_point})."
        raise ValueError(msg)
    entry_point = entry_point.resolve()
    FunctionMap.entry_point = str(entry_point)
    # SlurmFunction.dispatcher.entry_point = entry_point


def get_entry_point() -> Path:
    if FunctionMap.entry_point is None:
        import __main__

        # check if attribute __file__ is available
        if not hasattr(__main__, "__file__"):
            msg = "No entry point known."
            raise FileNotFoundError(msg)

        entry_point = __main__.__file__
        if not Path(entry_point).is_file() or Path(entry_point).suffix != ".py":
            msg = "No entry point known."
            raise FileNotFoundError(msg)

        set_entry_point(entry_point)
    assert FunctionMap.entry_point is not None
    path = Path(FunctionMap.entry_point)
    if not path.exists():
        msg = f"Entry point {path} does not exist."
        raise FileNotFoundError(msg)
    return path
