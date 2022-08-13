import inspect
import typing

from .dispatcher import FunctionCall, dispatch, get_dispatcher
from .function_map import FunctionMap
from .guard import guard_recursive_distribution
from .options import SlurmOptions


class SlurmFunction:
    """
    A wrapper around a function that allows it to be distributed to slurm.
    ```
    @slurmify(...function specific slurm options...)
    def f(foobar):
        print(foobar)

    if __name__=="__main__":
        assert isinstance(f, SlurmFunction), "f has become a SlurmFunction"
        jid = f.distribute("hello")
        f.wait_for(jid).distribute("bye")
    ```
    """

    def __init__(
        self, special_slurm_opts: typing.Dict, func: typing.Callable, func_id: str
    ):
        self.special_slurm_opts = SlurmOptions(**special_slurm_opts)
        self.func = func
        self.func_id = func_id

    def update_options(self, conf: typing.Dict[str, typing.Any]):
        self.special_slurm_opts.update(conf)

    def _add_dependencies(self, job_ids, method: str = "afterany"):
        opt = f"{method}:" + ":".join(str(jid) for jid in job_ids)
        if "dependency" in self.special_slurm_opts:
            # There are already dependencies. Trying to extend them.
            if isinstance(self.special_slurm_opts["dependency"], dict):
                dependecy_dict = self.special_slurm_opts["dependency"]
                if method in dependecy_dict:
                    dependecy_dict[method] += ":" + ":".join(
                        str(jid) for jid in job_ids
                    )
                else:
                    dependecy_dict[method] = ":".join(str(jid) for jid in job_ids)
            elif isinstance(self.special_slurm_opts["dependency"], str):
                self.special_slurm_opts["dependency"] += "," + opt
            else:
                # Could not extend dependencies because I have no idea what is going on.
                raise RuntimeError("Key 'dependency' has unexpected type.")
        else:
            self.special_slurm_opts["dependency"] = opt

    def wait_for(
        self, job_ids: typing.Union[int, typing.Iterable[int]], method: str = "afterany"
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
        if isinstance(job_ids, int):
            job_ids = [job_ids]
        if any(jid < 0 for jid in job_ids) and not get_dispatcher().is_sequential():
            raise RuntimeError(
                "Invalid job id. Not every dispatcher can directly return"
                " job ids, because it may not directly distribute them or"
                " doesn't distribute them at all."
            )
        sfunc._add_dependencies(list(job_ids), method)
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
        return self.func(*args, **kwargs)

    def distribute(self, *args, **kwargs) -> int:
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
            [FunctionCall(self.func_id, args, kwargs)], self.special_slurm_opts
        )

    @staticmethod
    def call(func_id, *args, **kwargs):
        return FunctionMap.call(func_id, args, kwargs)


def slurmify(f=None, **args) -> typing.Callable[[typing.Callable], SlurmFunction]:
    """
    Decorator: Make a function distributable to slurm.
    Usage:
    ```
    @slurmify()
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
