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
import logging
import typing

_exec_flag = False


def guard_recursive_distribution():
    global _exec_flag
    if _exec_flag:
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


def prevent_distribution():
    global _exec_flag
    _exec_flag = True


def allow_recursive_distribution() -> None:
    """
    Allow recursive distribution. Dangerous!
    :return: None
    """
    global _exec_flag
    _exec_flag = False


class TooManyDispatchesError(RuntimeError):
    def __init__(self, n_calls):
        self.n_calls = n_calls

    def __str__(self):
        return (
            f"Exceeded the dispatch limit of {self.n_calls} calls. "
            f"This limit has been introduced to prevent you from overloading your "
            f"slurm environment in case of a bug. You can increase it"
            f" using `set_dispatch_limit`."
        )


class _DispatchGuard:
    def __init__(self, max_calls):
        self.max_calls = max_calls
        self.remaining_calls = max_calls

    def __call__(self):
        if not self.max_calls:
            return None
        if self.remaining_calls <= 0:
            raise TooManyDispatchesError(self.max_calls)
        self.remaining_calls -= 1
        return self.remaining_calls

    def set_limit(self, n):
        self.max_calls = n
        self.remaining_calls = n


dispatch_guard = _DispatchGuard(100)


def set_dispatch_limit(n: typing.Optional[int]):
    """
    Set a limit to the number of dispatches. This feature has been introduced to
    prevent you from accidentally DDoSing you Slurm environment due to a bug.
    :param n: The maximal number of dispatches.
    :return: None
    """
    dispatch_guard.set_limit(n)


class BatchGuard:
    """
    Warns you if you flush more than once, as putting the flush call in a loop is
    a common mistake, compared to the intended use of flushing once at the end of
    your context, to get the job ids for dependency management.
    """

    already_warned = False

    def __init__(self) -> None:
        self._num_of_flushes = 0

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
        if num_tasks == 0:  # ignore empty flushes
            return
        self._num_of_flushes += 1
        if self._num_of_flushes == 2 and not self.already_warned:
            logging.getLogger("slurminade").warning(self._get_error_msg())
            self.already_warned = True


def disable_warning_on_repeated_flushes():
    """
    Disable the warning on multiple flushes. This is useful if you want to flush
    multiple times in a loop, without getting a warning.
    """
    BatchGuard.already_warned = True
