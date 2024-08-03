"""
The dispatcher distribute function calls to slurm or the local machine.
It can be accessed with `get_dispatcher` and set with `set_dispatcher`.
This allows to change the behaviour of the distribution, e.g., we use it for batch:
Batch simply wraps the dispatcher by a buffered version.
"""

import abc
import logging
import os
import shlex
import shutil
import subprocess
import typing
from pathlib import Path
from typing import Any, Dict, Optional

import simple_slurm

from .conf import _get_conf
from .execute_cmds import create_slurminade_command
from .function_call import FunctionCall
from .function_map import FunctionMap, get_entry_point
from .guard import dispatch_guard
from .job_reference import JobReference
from .options import SlurmOptions

# MAX_ARG_STRLEN on a Linux system with PAGE_SIZE 4096 is 131072
DEFAULT_MAX_ARG_LENGTH = 100000


class Dispatcher(abc.ABC):
    """
    Abstract dispatcher to be inherited by all concrete dispatchers.
    For implementing a dispatcher you have to implement `_dispatch`, `srun` and `sbatch`.

    """

    @abc.abstractmethod
    def _dispatch(
        self,
        funcs: typing.Iterable[FunctionCall],
        options: SlurmOptions,
        entry_point: Path,
        block: bool = False,
    ) -> JobReference:
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
    ) -> JobReference:
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
    ) -> JobReference:
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
        entry_point: Path,
        block: bool = False,
    ) -> JobReference:
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
        return self._dispatch(funcs, options, entry_point, block)

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

    def join(self):
        if self.is_sequential():
            # Already sequential, nothing to do
            return
        msg = "Joining is not implemented for this dispatcher."
        raise NotImplementedError(msg)


class TestJobReference(JobReference):
    def get_job_id(self) -> None:
        return None

    def get_exit_code(self) -> None:
        return None

    def get_info(self) -> Dict[str, Any]:
        return {"info": "test"}


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
        self,
        funcs: typing.Iterable[FunctionCall],
        options: SlurmOptions,  # noqa: ARG002
        entry_point: Path,
        block: bool = False,  # noqa: ARG002
    ) -> JobReference:
        dispatch_guard()
        funcs = list(funcs)
        command = create_slurminade_command(
            get_entry_point(), funcs, self.max_arg_length
        )
        logging.getLogger("slurminade").info(command)
        self.calls.append(funcs)
        self._cleanup(command)
        return TestJobReference()

    def _cleanup(self, command):
        args = shlex.split(command)
        if args[-2] != "temp":
            return
        filename = Path(args[-1])
        if filename.exists():
            filename.unlink()

    def srun(
        self,
        command: str,
        conf: typing.Optional[typing.Dict] = None,  # noqa: ARG002
        simple_slurm_kwargs: typing.Optional[typing.Dict] = None,  # noqa: ARG002
    ):
        dispatch_guard()
        self.sruns.append(command)
        logging.getLogger("slurminade").info("[test output] SRUN %s", command)
        return TestJobReference()

    def sbatch(
        self,
        command: str,
        conf: typing.Optional[typing.Dict] = None,  # noqa: ARG002
        simple_slurm_kwargs: typing.Optional[typing.Dict] = None,  # noqa: ARG002
    ):
        dispatch_guard()
        self.sbatches.append(command)
        logging.getLogger("slurminade").info("[test output] SBATCH %s", command)
        return TestJobReference()

    def is_sequential(self):
        return True


class SlurmJobReference(JobReference):
    def __init__(self, job_id, exit_code, mode: str):
        self.job_id = job_id
        self.exit_code = exit_code
        self.mode = mode

    def get_job_id(self) -> int:
        return self.job_id

    def get_exit_code(self) -> Optional[int]:
        return self.exit_code

    def get_info(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "exit_code": self.exit_code,
            "on_slurm": True,
            "mode": self.mode,
        }


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
        self._all_job_ids = []
        self._join_dependencies = []

    def _create_slurm_api(self, special_slurm_opts):
        conf = _get_conf(special_slurm_opts)
        return simple_slurm.Slurm(**conf)

    def _job_name(self, funcs: typing.List[FunctionCall]) -> str:
        func_names = list({FunctionMap.get_readable_name(f.func_id) for f in funcs})
        if len(funcs) == 1:
            return f"slurminade:{func_names[0]}"
        return f"slurminade[batch]:{func_names[0]}..."

    def _dispatch(
        self,
        funcs: typing.Iterable[FunctionCall],
        options: SlurmOptions,
        entry_point: Path,
        block: bool = False,
    ) -> SlurmJobReference:
        dispatch_guard()
        if "job_name" not in options:
            funcs = list(funcs)
            # This is complicated to prevent warnings about the type
            options = SlurmOptions(**options.as_dict())
            options["job_name"] = self._job_name(funcs)
        options = SlurmOptions(**options)
        if self._join_dependencies:
            options.add_dependencies(self._join_dependencies, "afterany")
        slurm = self._create_slurm_api(options)
        command = create_slurminade_command(entry_point, funcs, self.max_arg_length)
        logging.getLogger("slurminade").debug(command)
        if block:
            ret = slurm.srun(command)
            logging.getLogger("slurminade").info(
                "Returned from srun with exit code %s", ret
            )
            return SlurmJobReference(None, ret, "srun")
        jid = slurm.sbatch(command)
        self._all_job_ids.append(jid)
        return SlurmJobReference(jid, None, "sbatch")

    def sbatch(
        self,
        command: str,
        conf: typing.Optional[typing.Dict] = None,
        simple_slurm_kwargs: typing.Optional[typing.Dict] = None,
    ) -> SlurmJobReference:
        dispatch_guard()
        conf = _get_conf(conf)
        slurm = simple_slurm.Slurm(**conf)
        logging.getLogger("slurminade").debug("SBATCH %s", command)
        if simple_slurm_kwargs:
            jid = slurm.sbatch(command, **simple_slurm_kwargs)
        else:
            jid = slurm.sbatch(command)
        self._all_job_ids.append(jid)
        return SlurmJobReference(jid, None, "sbatch")

    def join(self):
        if not self._all_job_ids:
            return
        self._join_dependencies = list(set(self._all_job_ids))

    def srun(
        self,
        command: str,
        conf: typing.Optional[typing.Dict] = None,
        simple_slurm_kwargs: typing.Optional[typing.Dict] = None,
    ) -> SlurmJobReference:
        dispatch_guard()
        conf = _get_conf(conf)
        slurm = simple_slurm.Slurm(**conf)
        logging.getLogger("slurminade").debug("SRUN %s", command)
        if simple_slurm_kwargs:
            ret = slurm.srun(command, **simple_slurm_kwargs)
        else:
            ret = slurm.srun(command)
        return SlurmJobReference(None, ret, "srun")


class SubprocessJobReference(JobReference):
    def __init__(self):
        pass

    def get_job_id(self) -> Optional[int]:
        return None

    def get_exit_code(self) -> Optional[int]:
        return None

    def get_info(self) -> Dict[str, Any]:
        return {"on_slurm": False}


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
        self,
        funcs: typing.Iterable[FunctionCall],
        options: SlurmOptions,  # noqa: ARG002
        entry_point: Path,
        block: bool = False,  # noqa: ARG002
    ) -> int:
        dispatch_guard()
        command = create_slurminade_command(entry_point, funcs, self.max_arg_length)
        os.system(command)
        return -1

    def srun(
        self,
        command: str,
        conf: typing.Optional[typing.Dict] = None,  # noqa: ARG002
        simple_slurm_kwargs: typing.Optional[typing.Dict] = None,  # noqa: ARG002
    ):
        dispatch_guard()
        logging.getLogger("slurminade").debug("SRUN %s", command)
        subprocess.run(command, check=True)

    def sbatch(
        self,
        command: str,
        conf: typing.Optional[typing.Dict] = None,  # noqa: ARG002
        simple_slurm_kwargs: typing.Optional[typing.Dict] = None,  # noqa: ARG002
    ):
        self.srun(command)

    def is_sequential(self):
        return True


class LocalJobReference(JobReference):
    def get_job_id(self) -> None:
        return None

    def get_exit_code(self) -> None:
        return None

    def get_info(self) -> Dict[str, Any]:
        return {"on_slurm": False}


class DirectCallDispatcher(Dispatcher):
    """
    A dispatcher that calls functions as if we would not use slurminade.
    This allows compatibility of scripts also on computers not integrated into
    the slurm network.
    """

    def _dispatch(
        self,
        funcs: typing.Iterable[FunctionCall],
        options: SlurmOptions,  # noqa: ARG002
        entry_point: Path,  # noqa: ARG002
        block: bool = False,  # noqa: ARG002
    ) -> LocalJobReference:
        dispatch_guard()
        for func in funcs:
            FunctionMap.call(func.func_id, func.args, func.kwargs)
        return LocalJobReference()

    def srun(
        self,
        command: str,
        conf: typing.Optional[typing.Dict] = None,  # noqa: ARG002
        simple_slurm_kwargs: typing.Optional[typing.Dict] = None,  # noqa: ARG002
    ):
        dispatch_guard()
        subprocess.run(command, check=True)
        return LocalJobReference()

    def sbatch(
        self,
        command: str,
        conf: typing.Optional[typing.Dict] = None,  # noqa: ARG002
        simple_slurm_kwargs: typing.Optional[typing.Dict] = None,  # noqa: ARG002
    ):
        return self.srun(command)

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
    global __dispatcher  # noqa: PLW0603
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
    global __dispatcher  # noqa: PLW0603
    __dispatcher = dispatcher
    assert dispatcher == get_dispatcher()


def dispatch(
    funcs: typing.Union[FunctionCall, typing.Iterable[FunctionCall]],
    options: SlurmOptions,
    entry_point: Path,
    block: bool = False,
) -> JobReference:
    """
    Distribute function calls with the current dispatcher.
    :param funcs: The functions calls to be distributed.
    :param options: The slurm options to be used.
    :return: The job id.
    """
    funcs = list(funcs) if not isinstance(funcs, FunctionCall) else [funcs]
    for func in funcs:
        if not FunctionMap.check_id(func.func_id, entry_point):
            msg = f"Function '{func.func_id}' cannot be called from the given entry point."
            raise KeyError(msg)
    return get_dispatcher()(funcs, options, entry_point, block)


def srun(
    command: typing.Union[str, typing.List[str]],
    conf: typing.Union[SlurmOptions, typing.Dict, None] = None,
    simple_slurm_kwargs: typing.Optional[typing.Dict] = None,
) -> JobReference:
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
    command = (
        command
        if isinstance(command, str)
        else " ".join(shlex.quote(c) for c in command)
    )
    return get_dispatcher().srun(command, conf, simple_slurm_kwargs)


def sbatch(
    command: typing.Union[str, typing.List[str]],
    conf: typing.Union[SlurmOptions, typing.Dict, None] = None,
    simple_slurm_kwargs: typing.Optional[typing.Dict] = None,
) -> JobReference:
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
    command = (
        command
        if isinstance(command, str)
        else " ".join(shlex.quote(c) for c in command)
    )
    return get_dispatcher().sbatch(command, conf, simple_slurm_kwargs)


def join():
    """
    Join all jobs that have been dispatched so far.
    :return: None
    """
    get_dispatcher().join()
