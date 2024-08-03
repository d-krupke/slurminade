"""
Contains code for bundling function calls together.
"""

import logging
import typing
from collections import defaultdict
from pathlib import Path

from .dispatcher import (
    Dispatcher,
    FunctionCall,
    get_dispatcher,
    set_dispatcher,
)
from .function import SlurmFunction
from .job_reference import JobReference
from .options import SlurmOptions


class BundlingJobReference(JobReference):
    def __init__(self) -> None:
        super().__init__()

    def get_job_id(self) -> typing.Optional[int]:
        return None

    def get_exit_code(self) -> typing.Optional[int]:
        return None

    def get_info(self) -> typing.Dict[str, typing.Any]:
        return {}


class TaskBuffer:
    """
    A simple container to buffer all the tasks by their options.
    We can only bundle tasks with the same slurm options.
    """

    def __init__(self):
        self._tasks = defaultdict(list)

    def add(self, task: FunctionCall, options: SlurmOptions, entry_point: Path) -> int:
        self._tasks[(entry_point, options)].append(task)
        return len(self._tasks[(entry_point, options)])

    def items(self):
        for (entry_point, opt), tasks in self._tasks.items():
            if tasks:
                yield entry_point, opt, tasks

    def clear(self):
        self._tasks.clear()


class JobBundling(Dispatcher):
    """
    The logic to buffer the function calls. It wraps the original dispatcher.

    You can use::

        with slurminade.Batch(max_size=20) as batch:  # automatically bundles up to 20 tasks
            # run 100x f
            for i in range(100):
                f.distribute(i)

    to automatically bundle up to 20 tasks and distribute them.
    """

    def __init__(self, max_size: int):
        """
        :param max_size: Bundle up to this many calls.
        """
        super().__init__()
        self.max_size = max_size
        self.subdispatcher = get_dispatcher()
        self._tasks = TaskBuffer()
        self._all_job_refs = []

    def flush(self) -> typing.List[JobReference]:
        """
        Distribute all buffered tasks. Return the jobs used.
        This method is called automatically when the context is exited.
        However, you may want to call it manually to get the job references,
        for example to use them for dependency management with ``wait_for``.
        :param options: Only flush tasks with specific options.
        :return: A list of job references.
        """
        job_refs = []
        for entry_point, opt, tasks_ in self._tasks.items():
            tasks = tasks_
            while tasks:
                job_ref = self.subdispatcher(tasks[: self.max_size], opt, entry_point)
                job_refs.append(job_ref)
                tasks = tasks[self.max_size :]
        self._tasks.clear()
        self._all_job_refs.extend(job_refs)
        return job_refs

    def get_all_job_ids(self) -> typing.List[int]:
        """
        Return all job ids that have been used.
        """
        job_ids = [job_ref.get_job_id() for job_ref in self._all_job_refs]
        return [jid for jid in job_ids if jid is not None]

    def get_all_jobs(self) -> typing.List[JobReference]:
        return list(self._all_job_refs)

    def add(self, func: SlurmFunction, *args, **kwargs):
        """
        You can also add a task using `add` instead of `distribute`.
        :param func: The function to call
        :param args: The positional arguments
        :param kwargs: The keywords arguments.
        :return: None
        """
        self._dispatch(
            [FunctionCall(func.func_id, args, kwargs)],
            func.special_slurm_opts,
            func.get_entry_point(),
        )

    def _dispatch(
        self,
        funcs: typing.Iterable[FunctionCall],
        options: SlurmOptions,
        entry_point: Path,
        block: bool = False,
    ) -> JobReference:
        if block:
            # if blocking, we don't buffer, but dispatch immediately
            return self.subdispatcher._dispatch(funcs, options, entry_point, block=True)
        for func in funcs:
            self._tasks.add(func, options, entry_point)
        return BundlingJobReference()

    def srun(
        self,
        command: str,
        conf: typing.Optional[typing.Dict] = None,
        simple_slurm_kwargs: typing.Optional[typing.Dict] = None,
    ) -> JobReference:
        conf = SlurmOptions(conf if conf else {})
        return self.subdispatcher.srun(command, conf, simple_slurm_kwargs)

    def sbatch(
        self,
        command: str,
        conf: typing.Optional[typing.Dict] = None,
        simple_slurm_kwargs: typing.Optional[typing.Dict] = None,
    ) -> JobReference:
        conf = SlurmOptions(conf if conf else {})
        return self.subdispatcher.sbatch(command, conf, simple_slurm_kwargs)

    def __enter__(self):
        self.subdispatcher = get_dispatcher()
        set_dispatcher(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logging.getLogger("slurminade").error("Aborted due to exception.")
            return
        self.flush()
        set_dispatcher(self.subdispatcher)

    def _log_dispatch(self, funcs: typing.List[FunctionCall], options: SlurmOptions):
        if len(funcs) == 1:
            logging.getLogger("slurminade").info(
                f"Adding task to batch with options {options}: {funcs[0]}"
            )
        else:
            logging.getLogger("slurminade").info(
                f"Adding {len(funcs)} tasks to batch with options {options}: {', '.join([str(f) for f in funcs])}"
            )

    def __del__(self):
        self.flush()

    def join(self):
        self.flush()
        return self.subdispatcher.join()

    def is_sequential(self):
        return self.subdispatcher.is_sequential()


class Batch(JobBundling):
    """
    Compatibility alias for JobBundling. This is the old name. Deprecated.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.getLogger("slurminade").warning(
            "The `Batch` class has been renamed to `JobBundling`. Please update your code."
        )
