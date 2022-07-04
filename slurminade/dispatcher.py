"""
Implements functionality to dispatch a function call. Not for the end user.
"""

import json
import os
import shlex
import subprocess
import sys
import typing

import simple_slurm

from slurminade.conf import _get_conf
from slurminade.guard import dispatch_guard


class _FunctionCall:
    """
    Encapsulate a function call to be dispatched.
    """

    def __init__(self, func_id: str, args: typing.List, kwargs: typing.Dict):
        self.func_id = func_id
        self.args = args
        self.kwargs = kwargs

    def get_arguments_as_json_string(self) -> str:
        data = {"args": self.args, "kwargs": self.kwargs}
        serialized = json.dumps(data)
        if len(serialized) > 300:
            print(
                f"WARNING: Using slurminade function with long"
                f" function arguments ({len(serialized)}). This can be inefficient."
            )
        return serialized

    def as_json(self):
        return {"func_id": self.func_id, "args": self.args, "kwargs": self.kwargs}


class Dispatcher:
    """
    The dispatcher will dispatch a function call either to slurm or to a local process.
    """

    def __init__(self):
        self._main_file = None

    def _init_main_file(self):
        if not self._main_file:
            import __main__

            self.set_default_entry_point(__main__.__file__)

    def set_default_entry_point(self, entry_file_path: str):
        """
        Change the entry point from the main file to some other path.
        You should barely need to use this method (only when the function definition
        is not loaded from the main file by default or you are calling from an
        interactive environment.
        :param entry_file_path: A path to an entry point python file.
        :return:
        """
        if not os.path.isfile(entry_file_path) or not entry_file_path.endswith(".py"):
            raise ValueError("Illegal entry point.")
        if entry_file_path:
            entry_file_path = os.path.normpath(os.path.abspath(entry_file_path))
        self._main_file = entry_file_path

    def _select_entry_point(self, manual_entry_file_path):
        if manual_entry_file_path:
            manual_entry_file_path = os.path.normpath(
                os.path.abspath(manual_entry_file_path)
            )
        self._init_main_file()
        if not manual_entry_file_path and not self.has_main_file():
            raise RuntimeError(
                "This call does not have an entry point. "
                "If you are using slurminade interactively, "
                "please specify the entry point (e.g., the file the "
                "function is defined."
            )
        return manual_entry_file_path if manual_entry_file_path else self._main_file

    def _create_slurm_api(self, special_slurm_opts):
        conf = _get_conf(special_slurm_opts)
        slurm = simple_slurm.Slurm(**conf)
        return slurm

    def dispatch_locally(
        self, func_call: _FunctionCall, entry_file_path: typing.Optional[str] = None
    ) -> None:
        """
        Dispatch function call to a local process. Good for testing/debugging or running
        without slurm.
        :param func_call: The function call to be executed.
        :param entry_file_path: The optional entry file path. E.g., executing this file
        should provide the necessary function definition.
        :return: None
        """
        entry_file_path = self._select_entry_point(entry_file_path)
        slurm_task = [
            sys.executable,
            "-m",
            "slurminade.execute",
            entry_file_path,
            func_call.func_id,
            func_call.get_arguments_as_json_string(),
        ]
        subprocess.run(slurm_task, shell=False, check=True)

    def dispatch_to_slurm(
        self,
        func_call: _FunctionCall,
        special_slurm_opts: dict,
        entry_file_path: typing.Optional[str] = None,
    ) -> None:
        """
        Dispatch a function call to slurm.
        :param func_call: The function call to execute on a slurm node.
        :param special_slurm_opts: Special options for slurm.
        :param entry_file_path: An optional entry point that allows the slurm node to
        find the desired function definition.
        :return: None
        """
        dispatch_guard()
        entry_file_path = self._select_entry_point(entry_file_path)
        slurm = self._create_slurm_api(special_slurm_opts)
        slurm.sbatch(
            f"{sys.executable} -m slurminade.execute"
            f" {entry_file_path}"
            f" {func_call.func_id}"
            f" {shlex.quote(func_call.get_arguments_as_json_string())}"
        )

    def dispatch_batch_to_slurm(
        self,
        func_calls: typing.List[_FunctionCall],
        special_slurm_opts: typing.Dict,
        entry_file_path: typing.Optional[str] = None,
    ):
        """
        Dispatch a batch of function calls to slurm.
        :param func_calls: The function calls to execute on a slurm node.
        :param special_slurm_opts: Special options for slurm.
        :param entry_file_path: An optional entry point that allows the slurm node to
        find the desired function definition.
        :return: None
        """
        dispatch_guard()
        entry_file_path = self._select_entry_point(entry_file_path)
        slurm = self._create_slurm_api(special_slurm_opts)
        slurm.sbatch(
            f"{sys.executable} -m slurminade.execute"
            f" {entry_file_path}"
            f" __BATCH__"
            f" {shlex.quote(json.dumps([f.as_json() for f in func_calls]))}"
        )

    def has_main_file(self) -> bool:
        """
        Return true if the current execution has a main file that can be used as entry
        point.
        :return: True if the code is saved in proper files.
        """
        self._init_main_file()
        return os.path.isfile(self._main_file) and self._main_file.endswith(".py")
