"""
Some security measures to warn you about common mistakes and prevent you from
accidentally DDoSing your slurm environment.

1. Preventing recursive distributions, i.e., slurm nodes also distributing tasks.
2. Limiting the number of distributed tasks.
3. Warn about multiple flushes of batches, often caused by wrong indentation.

You can disable these security mechanisms by
``allow_recursive_distribution``, ``set_dispatch_limit(None)``, and
``disable_warning_for_multiple_flushes``.
"""

from __future__ import annotations

import logging

# Module-level logger for security and guard operations
_logger = logging.getLogger("slurminade.guard")

_exec_flag = False


def on_slurm_node() -> bool:
    """
    Check if currently executing on a Slurm node.

    Returns:
        True if on a Slurm node, False otherwise
    """
    return _exec_flag


def guard_recursive_distribution() -> None:
    """
    Prevent recursive task distribution (tasks distributing more tasks).

    Raises:
        RuntimeError: If attempting to distribute from a Slurm node
    """
    if on_slurm_node():
        _logger.error("Attempted recursive distribution from Slurm node")
        msg = """
        You tried to distribute a task recursively. This is not allowed by default,
        because it probably indicates a bug in your code. To save you from accidentally
        overloading your slurm environment, this feature has been disabled by default.
        The most common reason for this error is that you forgot to guard your script
        with 'if __name__==\"__main__\":'. If you are sure that you want to distribute
        tasks recursively, you can disable this security mechanism by calling
        `allow_recursive_distribution` before the first call of `distribute`.
        """
        raise RuntimeError(msg)


def prevent_distribution() -> None:
    """
    Mark current execution as being on a Slurm node (prevents distribution).
    """
    global _exec_flag  # noqa: PLW0603
    _logger.debug("Preventing distribution - marking as Slurm node execution")
    _exec_flag = True


def allow_recursive_distribution() -> None:
    """
    Allow recursive distribution. Dangerous!

    Warning:
        This disables an important safety mechanism. Use with caution.
    """
    global _exec_flag  # noqa: PLW0603
    _logger.warning("Recursive distribution enabled - safety mechanism disabled")
    _exec_flag = False


class TooManyDispatchesError(RuntimeError):
    """
    Exception raised when dispatch limit is exceeded.

    Attributes:
        n_calls: The maximum number of calls that was configured
    """

    def __init__(self, n_calls: int) -> None:
        """
        Initialize the error.

        Args:
            n_calls: The maximum number of calls allowed
        """
        self.n_calls = n_calls
        super().__init__(str(self))

    def __str__(self) -> str:
        """
        Generate error message.

        Returns:
            Error message describing the dispatch limit exceeded
        """
        return (
            f"Exceeded the dispatch limit of {self.n_calls} calls. "
            f"This limit has been introduced to prevent you from overloading your "
            f"slurm environment in case of a bug. You can increase it"
            f" using `set_dispatch_limit`."
        )


class _DispatchGuard:
    """
    Guard to track and limit the number of task dispatches.

    Attributes:
        max_calls: Maximum number of dispatch calls allowed (None for unlimited)
        remaining_calls: Number of remaining allowed calls
    """

    def __init__(self, max_calls: int | None) -> None:
        """
        Initialize the dispatch guard.

        Args:
            max_calls: Maximum number of dispatches allowed (None for unlimited)
        """
        self.max_calls = max_calls
        self.remaining_calls = max_calls
        _logger.debug("Created DispatchGuard with max_calls=%s", max_calls)

    def __call__(self) -> int | None:
        """
        Check and decrement the dispatch counter.

        Returns:
            Number of remaining calls, or None if unlimited

        Raises:
            TooManyDispatchesError: If dispatch limit exceeded
        """
        if not self.max_calls:
            return None
        if self.remaining_calls <= 0:
            _logger.error("Dispatch limit of %d exceeded", self.max_calls)
            raise TooManyDispatchesError(self.max_calls)
        self.remaining_calls -= 1
        _logger.debug("Dispatch guard: %d/%d calls remaining", self.remaining_calls, self.max_calls)
        return self.remaining_calls

    def set_limit(self, n: int | None) -> None:
        """
        Set a new dispatch limit.

        Args:
            n: New maximum number of dispatches (None for unlimited)
        """
        _logger.info("Setting dispatch limit to %s", n)
        self.max_calls = n
        self.remaining_calls = n


dispatch_guard = _DispatchGuard(100)


def set_dispatch_limit(n: int | None) -> None:
    """
    Set a limit to the number of dispatches.

    This feature has been introduced to prevent you from accidentally DDoSing
    your Slurm environment due to a bug.

    Args:
        n: The maximal number of dispatches (None for unlimited)
    """
    dispatch_guard.set_limit(n)


class BatchGuard:
    """
    Warns you if you flush more than once, as putting the flush call in a loop is
    a common mistake, compared to the intended use of flushing once at the end of
    your context, to get the job ids for dependency management.
    """

    already_warned: bool = False

    def __init__(self) -> None:
        """Initialize the batch guard."""
        self._num_of_flushes: int = 0

    def _get_error_msg(self) -> str:
        return """
        You repeatedly flushed a batch. There are various scenarios where this
        is done on purpose, but we want to warn you, because it is a common mistake
        to put the flush call in a loop by wrong indentation, instead of calling it
        once at the end of your context. If used for dependency management,
        e.g., with `wait_for`, such a mistake can lead to a faulty execution order.
        This warning allows you to quickly call `scancel -u <username>` to cancel
        your jobs, before they do any harm. If you are sure that you want to flush
        your batch multiple times, you can disable this warning by calling
        `disable_warning_on_repeated_flushes` before the first call of `flush`.
        You can also just ignore this warning, as no action is taken by default.
        """

    def report_flush(self, num_tasks: int) -> None:
        """
        Report a batch flush operation.

        Args:
            num_tasks: Number of tasks being flushed
        """
        if num_tasks == 0:  # ignore empty flushes
            return
        self._num_of_flushes += 1
        _logger.debug("Batch flush #%d with %d tasks", self._num_of_flushes, num_tasks)
        if self._num_of_flushes == 2 and not self.already_warned:
            _logger.warning("Multiple batch flushes detected")
            logging.getLogger("slurminade").warning(self._get_error_msg())
            self.already_warned = True


def disable_warning_on_repeated_flushes() -> None:
    """
    Disable the warning on multiple flushes.

    This is useful if you intentionally want to flush multiple times in a loop,
    without getting a warning.
    """
    _logger.info("Disabling repeated flush warnings")
    BatchGuard.already_warned = True
