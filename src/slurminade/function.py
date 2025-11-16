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

# Module-level logger for consistent logging
_logger = logging.getLogger("slurminade.function")


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
        special_slurm_opts: typing.Dict[str, typing.Any],
        func: typing.Callable[..., typing.Any],
        func_id: str,
        call_policy: CallPolicy = CallPolicy.LOCALLY,
    ) -> None:
        """
        Initialize a SlurmFunction wrapper.

        Args:
            special_slurm_opts: Slurm options specific to this function
            func: The callable to wrap
            func_id: Unique identifier for this function
            call_policy: How to call this function (locally, distributed, etc.)
        """
        self.special_slurm_opts = SlurmOptions(**special_slurm_opts)
        self.func = func
        self.func_id = func_id
        self.call_policy = call_policy
        self.defining_file = Path(inspect.getfile(func))
        _logger.debug("Created SlurmFunction for %s with policy %s", func_id, call_policy)

    def update_options(self, conf: typing.Dict[str, typing.Any]) -> None:
        """
        Update Slurm options for this function.

        Args:
            conf: Dictionary of options to update
        """
        _logger.debug("Updating options for %s: %s", self.func_id, conf)
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

    def _check(self, args: tuple[typing.Any, ...], kwargs: typing.Dict[str, typing.Any]) -> None:
        """
        Check if the arguments match the function signature.

        Args:
            args: Positional arguments
            kwargs: Keyword arguments

        Raises:
            TypeError: If arguments don't match function signature
        """
        inspect.signature(self.func).bind(*args, **kwargs)

    def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        """
        Direct call of the original function.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            The return value of the function (depends on call policy)
        """
        _logger.debug("Calling %s with policy %s", self.func_id, self.call_policy)
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
            _logger.debug(
                "Using defining file %s as entry point for %s",
                self.defining_file,
                self.func_id
            )
            return self.defining_file

    def distribute(self, *args: typing.Any, **kwargs: typing.Any) -> JobReference:
        """
        Try to distribute function call. If slurm is not available, a direct function
        call will be performed.

        Args:
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Job reference (may be invalid if not using Slurm)
        """
        self._check(args, kwargs)
        _logger.info("Distributing %s with %d args", self.func_id, len(args))
        guard_recursive_distribution()
        return dispatch(
            [FunctionCall(self.func_id, args, kwargs)],
            self.special_slurm_opts,
            entry_point=self.get_entry_point(),
            block=False,
        )

    def distribute_and_wait(self, *args: typing.Any, **kwargs: typing.Any) -> JobReference:
        """
        Distribute the function and wait for it to finish.

        Args:
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Job reference
        """
        self._check(args, kwargs)
        _logger.info("Distributing %s (blocking) with %d args", self.func_id, len(args))
        guard_recursive_distribution()
        return dispatch(
            [FunctionCall(self.func_id, args, kwargs)],
            self.special_slurm_opts,
            entry_point=self.get_entry_point(),
            block=True,
        )

    def run_locally(self, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        """
        Call the function locally (not distributed).

        Args:
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            The return value of the function
        """
        _logger.debug("Running %s locally with %d args", self.func_id, len(args))
        return self.func(*args, **kwargs)

    def __str__(self) -> str:
        return self.func.__name__

    @staticmethod
    def call(func_id: str, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        """
        Call a slurmified function by its ID.

        Args:
            func_id: The function identifier
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            The return value of the function
        """
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
    :param cmd: The command to be executed. Can be a string (will use shell=True)
               or a list of arguments (will use shell=False for better security).
    """
    if isinstance(cmd, str):
        # String commands require shell=True to handle pipes, redirects, etc.
        subprocess.run(cmd, check=True, shell=True)
    else:
        # List of arguments is safer - no shell needed
        subprocess.run(cmd, check=True, shell=False)
