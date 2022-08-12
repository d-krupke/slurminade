import inspect
import shutil
import subprocess
import json
import os
import typing

import simple_slurm

from .dispatcher import Dispatcher, FunctionCall, dispatch, get_dispatcher
from .function_map import FunctionMap
from .guard import guard_recursive_distribution
from .conf import _get_conf
from .options import SlurmOptions


class SlurmFunction:

    @staticmethod
    def set_entry_point(entry_point: str) -> None:
        """
        This function usually is not necessary for endusers.
        Set a manual entry point. This can allow you to use slurmify from the interactive
        interpreter.
        :param entry_point: A path to the entry point file.
        :return: None
        """
        if not os.path.isfile(entry_point) or not entry_point.endswith(".py"):
            raise ValueError("Illegal entry point.")
        entry_point = os.path.abspath(entry_point)
        FunctionMap.entry_point = entry_point
        #SlurmFunction.dispatcher.entry_point = entry_point

    def __init__(self, special_slurm_opts: typing.Dict, func: typing.Callable,
                 func_id: str):
        self.special_slurm_opts = SlurmOptions(**special_slurm_opts)
        self.func = func
        self.func_id = func_id

    def update_options(self, conf: typing.Dict[str, typing.Any]):
        self.special_slurm_opts.update(conf)

    def _add_dependencies(self, job_ids):
        opt = "afterany:" + ":".join(str(jid) for jid in job_ids)
        if "dependency" in self.special_slurm_opts:
            # There are already dependencies. Trying to extend them.
            if isinstance(self.special_slurm_opts["dependency"], dict):
                dependecy_dict = self.special_slurm_opts["dependency"]
                if "afterany" in dependecy_dict:
                    dependecy_dict["afterany"] += ":" + ":".join(
                        str(jid) for jid in job_ids)
                else:
                    dependecy_dict["afterany"] = ":".join(str(jid) for jid in job_ids)
            elif isinstance(self.special_slurm_opts["dependency"], str):
                self.special_slurm_opts["dependency"] += "," + opt
            else:
                # Could not extend dependencies because I have no idea what is going on.
                raise RuntimeError("Key 'dependency' has unexpected type.")
        else:
            self.special_slurm_opts["dependency"] = opt

    def wait_for(self, job_ids: typing.Union[int, typing.Iterable[int]]) \
            -> "SlurmFunction":
        sfunc = SlurmFunction(self.special_slurm_opts, self.func, self.func_id)
        if isinstance(job_ids, int):
            job_ids = [job_ids]
        if any(jid<0 for jid in job_ids) and not get_dispatcher().is_sequential():
            raise RuntimeError("Invalid job id. Not every dispatcher can directly return"
                               " job ids, because it may not directly distribute them or"
                               " doesn't distribute them at all.")
        sfunc._add_dependencies(job_ids)
        return sfunc

    def _check(self, args, kwargs):
        """
        Check if the arguments match the function signature.
        """
        inspect.signature(self.func).bind(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def distribute(self, *args, **kwargs):
        """
        Try to distribute function call. If slurm is not available, a direct function
        call will be performed.
        Call with function arguments.
        :return: True if distributed to slurm.
        """
        self._check(args, kwargs)
        guard_recursive_distribution()
        return dispatch([FunctionCall(self.func_id, args, kwargs)],
                        self.special_slurm_opts)

    @staticmethod
    def call(func_id, *args, **kwargs):
        return FunctionMap.call(func_id, args, kwargs)


def slurmify(f=None, **args) -> typing.Callable[[typing.Callable], SlurmFunction]:
    """
    Decorator: Make a function distributable to slurm.
    Usage:
    ```
    @slurimfy()
    def func(a, b):
        pass
    ```
    :param f: Function
    :param args: Special slurm options for this function.
    :return: A decorated function, callable with slurm.
    """

    if f:  # use default parameters
        func_id = FunctionMap.register(f)
        return SlurmFunction({}, f, func_id)
    else:

        def dec(func) -> SlurmFunction:
            func_id = FunctionMap.register(func)
            return SlurmFunction(args, func, func_id)

        return dec
