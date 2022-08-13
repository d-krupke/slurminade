"""
The dispatcher distribute function calls to slurm or the local machine.
It can be accessed with `get_dispatcher` and set with `set_dispatcher`.
This allows to change the behaviour of the distribution, e.g., we use it for batch:
Batch simply wraps the dispatcher by a buffered version.
"""
import abc
import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
import typing

import simple_slurm

from slurminade.conf import _get_conf
from slurminade.function_map import FunctionMap, get_entry_point
from slurminade.options import SlurmOptions


class FunctionCall:
    """
    A function call to be dispatched.
    """

    def __init__(self, func_id, args, kwargs):
        self.func_id = func_id  # the function id, as in FunctionMap
        self.args = args  # the positional arguments for the call
        self.kwargs = kwargs  # the keyword arguments for the call

    def to_json(self) -> typing.Dict:
        """
        Convert call to a json object that can be passed to slurm.
        :return: json object.
        """
        return {"func_id": self.func_id, "args": self.args, "kwargs": self.kwargs}


class Dispatcher(abc.ABC):
    """
    Abstract dispatcher to be inherited by all concrete dispatchers.
    For implementing a dispatcher you have to implement `_dispatch`, `srun` and `sbatch`.

    """

    @abc.abstractmethod
    def _dispatch(
        self, funcs: typing.Iterable[FunctionCall], options: SlurmOptions
    ) -> int:
        """
        Define how to dispatch a number of function calls.
        :param funcs: The function calls to be dispatched.
        :param options: The slurm options to be used.
        :return: The job id. Use -1 if not applicable (e.g., because buffered)
        """
        pass

    @abc.abstractmethod
    def srun(
        self,
        command: str,
        conf: typing.Optional[SlurmOptions] = None,
        simple_slurm_kwargs: dict = None,
    ) -> int:
        """
        Define how you want to execute an `srun` command. This command is directly
        executed and only terminates after completion.
        :param command: A system command, e.g. `echo hello world > foobar.txt`.
        :param conf: The slurm configuration.
        :param simple_slurm_kwargs: Additional options for simple_slurm.
        :return: Job id
        """
        pass

    @abc.abstractmethod
    def sbatch(
        self,
        command: str,
        conf: typing.Optional[SlurmOptions] = None,
        simple_slurm_kwargs: dict = None,
    ) -> int:
        """
        Define how you want to execute an `sbatch` command. The command is scheduled
        and the function return immediately.
        :param command: A system command, e.g. `echo hello world > foobar.txt`.
        :param conf: The slurm configuration.
        :param simple_slurm_kwargs: Additional options for simple_slurm.
        :return: Job id.
        """
        pass

    def __call__(
        self,
        funcs: typing.Union[FunctionCall, typing.Iterable[FunctionCall]],
        options: SlurmOptions,
    ) -> int:
        """
        Dispatches a function call or a number of function calls.
        :param funcs: The function calls to be distributed.
        :param options: The slurm options to be used.
        :return: Job id.
        """
        if isinstance(funcs, FunctionCall):
            funcs = [funcs]
        return self._dispatch(funcs, options)

    def is_sequential(self):
        """
        Return true if the dispatcher works sequential. In this case, the dependencies
        are trivially fulfilled. Slurm does not work sequentially, because this
        would destroy its purpose. In some cases however, you do not want to use
        slurm for compatibility reasons, without chaning the script. In these cases,
        this function tells slurminade not to be too strict about dependencies.
        :return: True is tasks are executed sequentially, false if not.
        """
        return False


class TestDispatcher(Dispatcher):
    """
    A dummy dispatcher that just prints the output. Primarily for debugging and testing.
    """

    def __init__(self):
        super().__init__()
        self.calls = []
        self.sbatches = []
        self.sruns = []

    def _dispatch(
        self, funcs: typing.Iterable[FunctionCall], options: SlurmOptions
    ) -> int:
        funcs = list(funcs)
        print(
            f"{sys.executable} -m slurminade.execute"
            f" {shlex.quote(get_entry_point())}"
            f" {shlex.quote(json.dumps([f.to_json() for f in funcs]))}"
        )
        self.calls.append(funcs)
        return -1

    def srun(self, command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
        self.sruns.append(command)
        print("SRUN", command)

    def sbatch(self, command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
        self.sbatches.append(command)
        print("SBATCH", command)

    def is_sequential(self):
        return True


class SlurmDispatcher(Dispatcher):
    """
    The most important dispatcher: Distributing function calls to slurm.
    """

    def __init__(self):
        super().__init__()
        if not shutil.which("sbatch"):
            raise RuntimeError("Slurm could not be found.")

    def _create_slurm_api(self, special_slurm_opts):
        conf = _get_conf(special_slurm_opts)
        slurm = simple_slurm.Slurm(**conf)
        return slurm

    def _dispatch(
        self, funcs: typing.Iterable[FunctionCall], options: SlurmOptions
    ) -> int:
        slurm = self._create_slurm_api(options)
        return slurm.sbatch(
            f"{sys.executable} -m slurminade.execute"
            f" {shlex.quote(get_entry_point())}"
            f" {shlex.quote(json.dumps([f.to_json() for f in funcs]))}"
        )

    def sbatch(self, command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
        conf = _get_conf(conf)
        slurm = simple_slurm.Slurm(**conf)
        if simple_slurm_kwargs:
            return slurm.sbatch(command, **simple_slurm_kwargs)
        else:
            return slurm.sbatch(command)

    def srun(self, command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
        conf = _get_conf(conf)
        slurm = simple_slurm.Slurm(**conf)
        if simple_slurm_kwargs:
            return slurm.srun(command, **simple_slurm_kwargs)
        else:
            return slurm.srun(command)


class SubprocessDispatcher(Dispatcher):
    """
    A dispatcher for debugging that distributes function calls using subprocesses.
    Thus, it uses the same serialization mechanisms, but without a slurm dependency.
    Completely useless for productive purposes. Use `DirectCallDispatcher` if you
    don't want to use slurm.
    Despite using subprocesses, it does not parallelize but works sequential.
    """

    def _dispatch(
        self, funcs: typing.Iterable[FunctionCall], options: SlurmOptions
    ) -> int:
        os.system(
            f"{sys.executable} -m slurminade.execute"
            f" {shlex.quote(get_entry_point())}"
            f" {shlex.quote(json.dumps([f.to_json() for f in funcs]))}"
        )
        return -1

    def srun(self, command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
        subprocess.run(command, check=True)

    def sbatch(self, command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
        self.srun(command)

    def is_sequential(self):
        return True


class DirectCallDispatcher(Dispatcher):
    """
    A dispatcher that calls functions as if we would not use slurminade.
    This allows compatibility of scripts also on computers not integrated into
    the slurm network.
    """

    def _dispatch(
        self, funcs: typing.Iterable[FunctionCall], options: SlurmOptions
    ) -> int:
        for func in funcs:
            FunctionMap.call(func.func_id, func.args, func.kwargs)
        return -1

    def srun(self, command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
        subprocess.run(command, check=True)

    def sbatch(self, command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
        self.srun(command)

    def is_sequential(self):
        return True


# The current dispatcher. Use with `get_dispatcher` and `set_dispatcher`.
__dispatcher: typing.Optional[Dispatcher] = None


def get_dispatcher() -> Dispatcher:
    """
    Returns the current dispatcher. Creates a dispatcher if none is available.
    First tries to create the slurm-dispatcher (as this is the primary purpose of
    slurminade). If no slurm-environment can be found, it creates a DirectCallDispatcher
    to allow compatibility.
    :return: The dispatcher.
    """
    global __dispatcher
    if __dispatcher is None:
        try:
            __dispatcher = SlurmDispatcher()
        except RuntimeError as re:
            logging.getLogger("slurminade").warning(str(re))
            logging.getLogger("slurminade").warning("Using direct calls.")
            __dispatcher = DirectCallDispatcher()
    return __dispatcher


def set_dispatcher(dispatcher: Dispatcher) -> None:
    """
    Replaces the dispatcher. Can be used to enforce a specific dispatcher.
    :param dispatcher: The dispatcher to be used.
    :return: None
    """
    global __dispatcher
    __dispatcher = dispatcher
    assert dispatcher == get_dispatcher()


def dispatch(
    funcs: typing.Union[FunctionCall, typing.Iterable[FunctionCall]],
    options: SlurmOptions,
) -> int:
    """
    Distribute function calls with the current dispatcher.
    :param funcs: The functions calls to be distributed.
    :param options: The slurm options to be used.
    :return: The job id.
    """
    return get_dispatcher()(funcs, options)


def srun(
    command: str,
    conf: typing.Union[SlurmOptions, typing.Dict, None] = None,
    simple_slurm_kwargs: dict = None,
) -> int:
    """
    Call srun with the current dispatcher. This command is directly
    executed and only terminates after completion.
    :param command: A system command, e.g. `echo hello world > foobar.txt`.
    :param conf: The slurm configuration.
    :param simple_slurm_kwargs: Additional options for simple_slurm.
    :return: Job id
    """
    if not isinstance(conf, SlurmOptions):
        conf = SlurmOptions(**conf)
    return get_dispatcher().srun(command, conf, simple_slurm_kwargs)


def sbatch(
    command: str,
    conf: typing.Union[SlurmOptions, typing.Dict, None] = None,
    simple_slurm_kwargs: dict = None,
) -> int:
    """
    The command is scheduled and the function returns immediately.
    :param command: A system command, e.g. `echo hello world > foobar.txt`.
    :param conf: The slurm configuration.
    :param simple_slurm_kwargs: Additional options for simple_slurm.
    :return: Job id.
    """
    if not isinstance(conf, SlurmOptions):
        conf = SlurmOptions(**conf)
    return get_dispatcher().sbatch(command, conf, simple_slurm_kwargs)
