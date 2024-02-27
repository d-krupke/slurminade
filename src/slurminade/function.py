import inspect
import logging
import subprocess
import typing
from enum import Enum
from pathlib import Path

from .dispatcher import FunctionCall, dispatch, get_dispatcher
from .function_map import FunctionMap, get_entry_point
from .guard import guard_recursive_distribution
from .job_reference import JobReference
from .options import SlurmOptions


class CallPolicy(Enum):
    """
    Policy for the call of a function.
    """

    LOCALLY = 0
    DISTRIBUTED = 1
    DISTRIBUTED_BLOCKING = 2


class SlurmFunction:
    """
    A wrapper around a function that allows it to be distributed to slurm.

    .. code-block:: python

        @slurmify(function specific slurm options)
        def f(foobar):
            print(foobar)

        if __name__=="__main__":
            assert isinstance(f, SlurmFunction), "f has become a SlurmFunction"
            jid = f.distribute("hello")
            f.wait_for(jid).distribute("bye")

    """

    def __init__(
        self,
        special_slurm_opts: typing.Dict,
        func: typing.Callable,
        func_id: str,
        call_policy: CallPolicy = CallPolicy.LOCALLY,
    ):
        self.special_slurm_opts = SlurmOptions(**special_slurm_opts)
        self.func = func
        self.func_id = func_id
        self.call_policy = call_policy
        self.defining_file = Path(inspect.getfile(func))

    def update_options(self, conf: typing.Dict[str, typing.Any]):
        self.special_slurm_opts.update(conf)

    def wait_for(
        self,
        job_ids: typing.Union[JobReference, typing.Iterable[JobReference]],
        method: str = "afterany",
    ) -> "SlurmFunction":
        """
        Add a dependency to a distribution.
        `f_jid = f.wait_for(job_ids).distribute("hello")`
        f will only be executed once all jobs within job_ids have finished (or failed).
        Its own job id can then also be used as dependency for other distributions.
        Note that this method does not manipulate the original function but returns
        a new function object, so you have to use chaining.
        Not every dispatcher returns valid job ids on distribute. For example with
        `Batch`, you get the job ids with `job_ids = batch.flush()`.
        :param job_ids: A single job id or an iterable of job ids.
        :param method: 'after'|'afterany'|'afternotok'|'afterok'|'singleton'
        :return: Chainable slurm function object.
        """
        sfunc = SlurmFunction(self.special_slurm_opts, self.func, self.func_id)
        job_ids = (
            [job_ids] if isinstance(job_ids, JobReference) else list(job_ids)
        )  # make sure it is a list
        if not job_ids and not get_dispatcher().is_sequential():
            msg = "Creating a dependency on an empty list of job ids."
            msg += " This is probably an error in your code."
            msg += " Maybe you are using `Batch` but flush outside of the `with` block?"
            raise RuntimeError(msg)
        if (
            any(jid.get_job_id() is None for jid in job_ids)
            and not get_dispatcher().is_sequential()
        ):
            msg = "Invalid job id. Not every dispatcher can directly return job ids, because it may not directly distribute them or doesn't distribute them at all."
            raise RuntimeError(msg)
        sfunc.special_slurm_opts.add_dependencies(
            [jid.get_job_id() for jid in job_ids], method
        )
        return sfunc

    def with_options(self, **kwargs) -> "SlurmFunction":
        """
        Add slurm options to the function.
        :param kwargs: The slurm options.
        :return: The modified function.
        """
        sfunc = SlurmFunction(self.special_slurm_opts, self.func, self.func_id)
        sfunc.update_options(kwargs)
        return sfunc

    def _check(self, args, kwargs):
        """
        Check if the arguments match the function signature.
        """
        inspect.signature(self.func).bind(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        """
        Direct call of the original function.
        :param args: Positional arguments.
        :param kwargs: Keyword arguments.
        :return: The return value of the function.
        """
        if self.call_policy == CallPolicy.LOCALLY:
            return self.run_locally(*args, **kwargs)
        if self.call_policy == CallPolicy.DISTRIBUTED:
            return self.distribute(*args, **kwargs)
        if self.call_policy == CallPolicy.DISTRIBUTED_BLOCKING:
            return self.distribute_and_wait(*args, **kwargs)
        msg = "Unknown call policy."
        raise RuntimeError(msg)

    def get_entry_point(self) -> Path:
        """
        Returns the entry point for the function.
        Either it is defined in the FunctionMap, or the defining file is used.
        """
        try:
            return get_entry_point()
        except FileNotFoundError:
            logging.getLogger("slurminade").debug(
                "Using defining file %s as entry point.", self.defining_file
            )
            return self.defining_file

    def distribute(self, *args, **kwargs) -> JobReference:
        """
        Try to distribute function call. If slurm is not available, a direct function
        call will be performed.
        `f.distribute("hello")`
        Call with function arguments.
        :return: Job id. Not necessarily valid (usually -1 in this case).
        """
        self._check(args, kwargs)
        guard_recursive_distribution()
        return dispatch(
            [FunctionCall(self.func_id, args, kwargs)],
            self.special_slurm_opts,
            entry_point=self.get_entry_point(),
            block=False,
        )

    def distribute_and_wait(self, *args, **kwargs) -> JobReference:
        """
        Distribute the function and wait for it to finish.
        :param args: The positional arguments.
        :param kwargs: The keyword arguments.
        :return: The job id.
        """
        self._check(args, kwargs)
        guard_recursive_distribution()
        return dispatch(
            [FunctionCall(self.func_id, args, kwargs)],
            self.special_slurm_opts,
            entry_point=self.get_entry_point(),
            block=True,
        )

    def run_locally(self, *args, **kwargs):
        """
        Call the function locally.
        `f.local("hello")`
        Call with function arguments.
        :return: The return value of the function.
        """
        return self.func(*args, **kwargs)

    def __str__(self) -> str:
        return self.func.__name__

    @staticmethod
    def call(func_id, *args, **kwargs):
        return FunctionMap.call(func_id, args, kwargs)


def slurmify(
    f=None, **args
) -> typing.Union[typing.Callable[[typing.Callable], SlurmFunction], SlurmFunction]:
    """
    Decorator: Make a function distributable to slurm.
    Usage:

    .. code-block:: python

        @slurmify()
        def func(a, b):
            pass

    :param f: Function
    :param args: Special slurm options for this function.
    :return: A decorated function, callable with slurm.
    """

    if f:  # use default parameters
        func_id = FunctionMap.register(f)
        return SlurmFunction({}, f, func_id)

    def dec(func) -> SlurmFunction:
        func_id = FunctionMap.register(func)
        return SlurmFunction(args, func, func_id)

    return dec


def _slurmify(
    allow_overwrite: bool, **args
) -> typing.Union[typing.Callable[[typing.Callable], SlurmFunction], SlurmFunction]:
    """
    Decorator: Make a function distributable to slurm.
    Usage:

    .. code-block:: python

        @slurmify_()
        def func(a, b):
            pass

    :param f: Function
    :param args: Special slurm options for this function.
    :return: A decorated function, callable with slurm.
    """

    def dec(func) -> SlurmFunction:
        func_id = FunctionMap.register(func, allow_overwrite=allow_overwrite)
        return SlurmFunction(args, func, func_id)

    return dec


@_slurmify(allow_overwrite=True)
def shell(cmd: typing.Union[str, typing.List[str]]):
    """
    Execute a command.
    :param cmd: The command to be executed.
    """
    subprocess.run(cmd, check=True, shell=True)
