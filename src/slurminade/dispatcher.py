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
from tempfile import mkstemp

import simple_slurm

from .conf import _get_conf
from .function_map import FunctionMap, get_entry_point
from .guard import dispatch_guard
from .options import SlurmOptions

# MAX_ARG_STRLEN on a Linux system with PAGE_SIZE 4096 is 131072
DEFAULT_MAX_ARG_LENGTH = 100000


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

    def __str__(self) -> str:
        """
        Return a printable string representation of the call, useful for logging.
        """

        def arg_to_str(arg):
            if isinstance(arg, str):
                return f"'{arg}'"
            return str(arg)

        short_args = ", ".join(arg_to_str(a) for a in self.args)
        if len(short_args) > 200:
            short_args = short_args[:200] + "..."
        short_kwargs = ", ".join(f"{k}={arg_to_str(v)}" for k, v in self.kwargs.items())
        if len(short_kwargs) > 200:
            short_kwargs = short_kwargs[:200] + "..."
        args = ", ".join(a for a in [short_args, short_kwargs] if a)
        return f"{FunctionMap.get_readable_name(self.func_id)}({args})"


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

    @abc.abstractmethod
    def srun(
        self,
        command: str,
        conf: typing.Optional[SlurmOptions] = None,
        simple_slurm_kwargs: typing.Optional[typing.Dict] = None,
    ) -> int:
        """
        Define how you want to execute an `srun` command. This command is directly
        executed and only terminates after completion.
        :param command: A system command, e.g. `echo hello world > foobar.txt`.
        :param conf: The slurm configuration.
        :param simple_slurm_kwargs: Additional options for simple_slurm.
        :return: Job id
        """

    @abc.abstractmethod
    def sbatch(
        self,
        command: str,
        conf: typing.Optional[SlurmOptions] = None,
        simple_slurm_kwargs: typing.Optional[typing.Dict] = None,
    ) -> int:
        """
        Define how you want to execute an `sbatch` command. The command is scheduled
        and the function return immediately.
        :param command: A system command, e.g. `echo hello world > foobar.txt`.
        :param conf: The slurm configuration.
        :param simple_slurm_kwargs: Additional options for simple_slurm.
        :return: Job id.
        """

    def _log_dispatch(self, funcs: typing.List[FunctionCall], options: SlurmOptions):
        if len(funcs) == 1:
            logging.getLogger("slurminade").info(
                f"Dispatching task with options {options}: {funcs[0]}"
            )
        else:
            logging.getLogger("slurminade").info(
                f"Dispatching task consisting of {len(funcs)} function calls with options {options}: {', '.join([str(f) for f in funcs])}"
            )

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
        funcs = list(funcs)
        self._log_dispatch(funcs, options)
        return self._dispatch(funcs, options)

    def is_sequential(self):
        """
        Return true if the dispatcher works sequential. In this case, the dependencies
        are trivially fulfilled. Slurm does not work sequentially, because this
        would destroy its purpose. In some cases however, you do not want to use
        slurm for compatibility reasons, without changing the script. In these cases,
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
        self.max_arg_length = DEFAULT_MAX_ARG_LENGTH

    def _dispatch(
        self, funcs: typing.Iterable[FunctionCall], options: SlurmOptions
    ) -> int:
        dispatch_guard()
        funcs = list(funcs)
        command = create_slurminade_command(funcs, self.max_arg_length)
        logging.getLogger("slurminade").info(command)
        self.calls.append(funcs)
        self._cleanup(command)
        return -1

    def _cleanup(self, command):
        args = shlex.split(command)
        if args[-2] != "temp":
            return
        filename = args[-1]
        if os.path.exists(filename):
            os.remove(filename)

    def srun(
        self,
        command: str,
        conf: typing.Optional[typing.Dict] = None,
        simple_slurm_kwargs: typing.Optional[typing.Dict] = None,
    ):
        dispatch_guard()
        self.sruns.append(command)
        print("SRUN", command)

    def sbatch(
        self,
        command: str,
        conf: typing.Optional[typing.Dict] = None,
        simple_slurm_kwargs: typing.Optional[typing.Dict] = None,
    ):
        dispatch_guard()
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
            msg = "Slurm could not be found."
            raise RuntimeError(msg)
        self.max_arg_length = DEFAULT_MAX_ARG_LENGTH

    def _create_slurm_api(self, special_slurm_opts):
        conf = _get_conf(special_slurm_opts)
        slurm = simple_slurm.Slurm(**conf)
        return slurm

    def _job_name(self, funcs: typing.List[FunctionCall]) -> str:
        func_names = list({FunctionMap.get_readable_name(f.func_id) for f in funcs})
        if len(funcs) == 1:
            return f"slurminade:{func_names[0]}"
        else:
            return f"slurminade[batch]:{func_names[0]}..."

    def _dispatch(
        self, funcs: typing.Iterable[FunctionCall], options: SlurmOptions
    ) -> int:
        dispatch_guard()
        if "job_name" not in options:
            funcs = list(funcs)
            # This is complicated to prevent warnings about the type
            options = SlurmOptions(**options.as_dict())
            options["job_name"] = self._job_name(funcs)
        slurm = self._create_slurm_api(options)
        command = create_slurminade_command(funcs, self.max_arg_length)
        logging.getLogger("slurminade").debug(command)
        return slurm.sbatch(command)

    def sbatch(
        self,
        command: str,
        conf: typing.Optional[typing.Dict] = None,
        simple_slurm_kwargs: typing.Optional[typing.Dict] = None,
    ):
        dispatch_guard()
        conf = _get_conf(conf)
        slurm = simple_slurm.Slurm(**conf)
        if simple_slurm_kwargs:
            return slurm.sbatch(command, **simple_slurm_kwargs)
        else:
            return slurm.sbatch(command)

    def srun(
        self,
        command: str,
        conf: typing.Optional[typing.Dict] = None,
        simple_slurm_kwargs: typing.Optional[typing.Dict] = None,
    ):
        dispatch_guard()
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

    def __init__(self):
        super().__init__()
        self.max_arg_length = DEFAULT_MAX_ARG_LENGTH

    def _dispatch(
        self, funcs: typing.Iterable[FunctionCall], options: SlurmOptions
    ) -> int:
        dispatch_guard()
        command = create_slurminade_command(funcs, self.max_arg_length)
        os.system(command)
        return -1

    def srun(
        self,
        command: str,
        conf: typing.Optional[typing.Dict] = None,
        simple_slurm_kwargs: typing.Optional[typing.Dict] = None,
    ):
        dispatch_guard()
        subprocess.run(command, check=True)

    def sbatch(
        self,
        command: str,
        conf: typing.Optional[typing.Dict] = None,
        simple_slurm_kwargs: typing.Optional[typing.Dict] = None,
    ):
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
        dispatch_guard()
        for func in funcs:
            FunctionMap.call(func.func_id, func.args, func.kwargs)
        return -1

    def srun(
        self,
        command: str,
        conf: typing.Optional[typing.Dict] = None,
        simple_slurm_kwargs: typing.Optional[typing.Dict] = None,
    ):
        dispatch_guard()
        subprocess.run(command, check=True)

    def sbatch(
        self,
        command: str,
        conf: typing.Optional[typing.Dict] = None,
        simple_slurm_kwargs: typing.Optional[typing.Dict] = None,
    ):
        self.srun(command)

    def is_sequential(self):
        return True


def create_slurminade_command(
    funcs: typing.Iterable[FunctionCall], max_arg_length: int
) -> str:
    """
    Creates a terminal command that calls the Python module `slurminade.execute` with the
    provided function calls as an argument. If the total length of the function calls
    exceeds the maximum allowed length of a command line argument, a temporary file is
    created to pass the function calls instead.
    :param funcs: The function calls to be dispatched.
    :param max_arg_length: The maximum allowed length of a command line argument.
    :returns: A string representing the command to be executed in the terminal.
    """
    command = f"{sys.executable} -m slurminade.execute {shlex.quote(get_entry_point())}"

    # Serialize function calls as JSON
    serialized_calls = json.dumps([f.to_json() for f in funcs])

    if len(shlex.quote(serialized_calls)) > max_arg_length:
        # The argument is too long, create temporary file for the JSON
        fd, filename = mkstemp(prefix="slurminade_", suffix=".json", text=True, dir=".")
        with os.fdopen(fd, "w") as f:
            f.write(serialized_calls)
        command += f" temp {shlex.quote(filename)}"
    else:
        command += f" arg {shlex.quote(serialized_calls)}"
    return command


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
    simple_slurm_kwargs: typing.Optional[typing.Dict] = None,
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
        if conf is None:
            conf = {}
        conf = SlurmOptions(**conf)
    return get_dispatcher().srun(command, conf, simple_slurm_kwargs)


def sbatch(
    command: str,
    conf: typing.Union[SlurmOptions, typing.Dict, None] = None,
    simple_slurm_kwargs: typing.Optional[typing.Dict] = None,
) -> int:
    """
    The command is scheduled and the function returns immediately.
    :param command: A system command, e.g. `echo hello world > foobar.txt`.
    :param conf: The slurm configuration.
    :param simple_slurm_kwargs: Additional options for simple_slurm.
    :return: Job id.
    """
    if not isinstance(conf, SlurmOptions):
        if conf is None:
            conf = {}
        conf = SlurmOptions(**conf)
    return get_dispatcher().sbatch(command, conf, simple_slurm_kwargs)
