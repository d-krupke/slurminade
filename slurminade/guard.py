import typing

__exec_flag = False


def guard_recursive_distribution():
    if __exec_flag:
        raise RuntimeError(
            "Cannot distribute a task within a distributed task! "
            "(maybe you forgot to guard you script with "
            "'if __name__==\"__main__\":'?)"
        )


def prevent_distribution():
    __exec_flag = True


class TooManyDispatchesError(RuntimeError):
    def __init__(self, n_calls):
        self.n_calls = n_calls

    def __str__(self):
        return (
            f"Exceeded the dispatch limit of {self.n_calls} calls. "
            f"This limit has been introduced to prevent you from spamming your "
            f"slurm environment in case of a bug. You can increase it "
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


dispatch_guard = _DispatchGuard(1000)


def set_dispatch_limit(n: typing.Optional[int]):
    """
    Set a limit to the number of dispatches. This feature has been introduced to
    prevent you from accidentally DDoSing you Slurm environment due to a bug.
    :param n: The maximal number of dispatches.
    :return: None
    """
    dispatch_guard.set_limit(n)
