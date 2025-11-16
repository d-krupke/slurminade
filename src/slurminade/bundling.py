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

# Module-level logger for consistent logging
_logger = logging.getLogger("slurminade.bundling")


class BundlingJobReference(JobReference):
    """
    Placeholder job reference for bundled tasks.

    Since bundled tasks are not dispatched immediately, this reference
    returns None for job_id and exit_code until the bundle is flushed.
    """

    def __init__(self) -> None:
        """Initialize a placeholder job reference."""
        super().__init__()

    def get_job_id(self) -> typing.Optional[int]:
        """
        Get the job ID (always None for bundled tasks).

        Returns:
            None, as bundled tasks are not dispatched yet
        """
        return None

    def get_exit_code(self) -> typing.Optional[int]:
        """
        Get the exit code (always None for bundled tasks).

        Returns:
            None, as bundled tasks are not dispatched yet
        """
        return None

    def get_info(self) -> typing.Dict[str, typing.Any]:
        """
        Get job information (always empty for bundled tasks).

        Returns:
            Empty dict, as bundled tasks are not dispatched yet
        """
        return {}


class TaskBuffer:
    """
    A simple container to buffer all the tasks by their options.
    We can only bundle tasks with the same slurm options.
    """

    def __init__(self) -> None:
        """Initialize an empty task buffer."""
        self._tasks: typing.Dict[
            typing.Tuple[Path, SlurmOptions], typing.List[FunctionCall]
        ] = defaultdict(list)
        _logger.debug("Created TaskBuffer")

    def add(self, task: FunctionCall, options: SlurmOptions, entry_point: Path) -> int:
        """
        Add a task to the buffer.

        Args:
            task: The function call to buffer
            options: Slurm options for this task
            entry_point: Entry point path

        Returns:
            Number of tasks buffered with these options
        """
        self._tasks[(entry_point, options)].append(task)
        count = len(self._tasks[(entry_point, options)])
        _logger.debug(
            "Added task to buffer. %d tasks with options %s", count, options
        )
        return count

    def items(
        self,
    ) -> typing.Iterator[typing.Tuple[Path, SlurmOptions, typing.List[FunctionCall]]]:
        """
        Iterate over buffered tasks grouped by options.

        Yields:
            Tuples of (entry_point, options, tasks)
        """
        for (entry_point, opt), tasks in self._tasks.items():
            if tasks:
                yield entry_point, opt, tasks

    def clear(self) -> None:
        """Clear all buffered tasks."""
        total_tasks = sum(len(tasks) for tasks in self._tasks.values())
        total_groups = len(self._tasks)
        _logger.debug(
            "Clearing buffer: %d tasks in %d groups", total_tasks, total_groups
        )
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

    def __init__(self, max_size: int) -> None:
        """
        Initialize job bundling with a maximum bundle size.

        Args:
            max_size: Bundle up to this many calls per job
        """
        super().__init__()
        self.max_size = max_size
        self.subdispatcher = get_dispatcher()
        self._tasks = TaskBuffer()
        self._all_job_refs: typing.List[JobReference] = []
        _logger.info(
            "Created JobBundling with max_size=%d, dispatcher=%s",
            max_size,
            self.subdispatcher.__class__.__name__,
        )

    def flush(self) -> typing.List[JobReference]:
        """
        Distribute all buffered tasks. Return the jobs used.

        This method is called automatically when the context is exited.
        However, you may want to call it manually to get the job references,
        for example to use them for dependency management with ``wait_for``.

        Returns:
            A list of job references for the dispatched jobs
        """
        _logger.info("Flushing JobBundling buffer")
        job_refs: typing.List[JobReference] = []
        total_tasks = 0

        for entry_point, opt, tasks_ in self._tasks.items():
            tasks = tasks_
            total_tasks += len(tasks)
            bundle_count = 0

            while tasks:
                batch = tasks[: self.max_size]
                job_ref = self.subdispatcher(batch, opt, entry_point)
                job_refs.append(job_ref)
                bundle_count += 1
                _logger.debug(
                    "Flushed bundle %d with %d tasks (options: %s)",
                    bundle_count,
                    len(batch),
                    opt,
                )
                tasks = tasks[self.max_size :]

        self._tasks.clear()
        self._all_job_refs.extend(job_refs)

        _logger.info(
            "Flushed %d total tasks in %d jobs (bundles)", total_tasks, len(job_refs)
        )
        return job_refs

    def get_all_job_ids(self) -> typing.List[int]:
        """
        Return all job ids that have been used.

        Returns:
            List of job IDs (excluding None values)
        """
        job_ids = [job_ref.get_job_id() for job_ref in self._all_job_refs]
        filtered_ids = [jid for jid in job_ids if jid is not None]
        _logger.debug("Retrieved %d job IDs from %d job refs", len(filtered_ids), len(self._all_job_refs))
        return filtered_ids

    def get_all_jobs(self) -> typing.List[JobReference]:
        """
        Return all job references that have been created.

        Returns:
            List of all JobReference objects
        """
        _logger.debug("Retrieved %d job references", len(self._all_job_refs))
        return list(self._all_job_refs)

    def add(self, func: SlurmFunction, *args: typing.Any, **kwargs: typing.Any) -> None:
        """
        You can also add a task using `add` instead of `distribute`.

        Args:
            func: The SlurmFunction to call
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        """
        _logger.debug("Adding task %s to bundle with %d args", func.func_id, len(args))
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
        """
        Dispatch function calls, buffering unless blocking is requested.

        Args:
            funcs: Function calls to dispatch
            options: Slurm options for the jobs
            entry_point: Entry point path
            block: If True, dispatch immediately without buffering

        Returns:
            JobReference (BundlingJobReference if buffered, actual ref if blocking)
        """
        if block:
            # if blocking, we don't buffer, but dispatch immediately
            _logger.debug("Blocking dispatch requested, bypassing buffer")
            return self.subdispatcher._dispatch(funcs, options, entry_point, block=True)

        func_list = list(funcs)
        _logger.debug("Buffering %d function calls", len(func_list))
        for func in func_list:
            self._tasks.add(func, options, entry_point)
        return BundlingJobReference()

    def srun(
        self,
        command: str,
        conf: typing.Optional[typing.Dict[str, typing.Any]] = None,
        simple_slurm_kwargs: typing.Optional[typing.Dict[str, typing.Any]] = None,
    ) -> JobReference:
        """
        Execute command with srun (bypasses bundling).

        Args:
            command: Shell command to execute
            conf: Slurm configuration options
            simple_slurm_kwargs: Additional simple_slurm keyword arguments

        Returns:
            JobReference for the srun job
        """
        _logger.debug("Executing srun command (bypassing bundling): %s", command[:50])
        options = SlurmOptions(**(conf if conf else {}))
        return self.subdispatcher.srun(command, options, simple_slurm_kwargs)

    def sbatch(
        self,
        command: str,
        conf: typing.Optional[typing.Dict[str, typing.Any]] = None,
        simple_slurm_kwargs: typing.Optional[typing.Dict[str, typing.Any]] = None,
    ) -> JobReference:
        """
        Execute command with sbatch (bypasses bundling).

        Args:
            command: Shell command to execute
            conf: Slurm configuration options
            simple_slurm_kwargs: Additional simple_slurm keyword arguments

        Returns:
            JobReference for the sbatch job
        """
        _logger.debug("Executing sbatch command (bypassing bundling): %s", command[:50])
        options = SlurmOptions(**(conf if conf else {}))
        return self.subdispatcher.sbatch(command, options, simple_slurm_kwargs)

    def __enter__(self) -> "JobBundling":
        """
        Enter context manager - activate bundling dispatcher.

        Returns:
            Self for use in with statement
        """
        self.subdispatcher = get_dispatcher()
        _logger.info("Entering JobBundling context, activating bundling dispatcher")
        set_dispatcher(self)
        return self

    def __exit__(
        self,
        exc_type: typing.Optional[typing.Type[BaseException]],
        exc_val: typing.Optional[BaseException],
        exc_tb: typing.Optional[typing.Any],
    ) -> None:
        """
        Exit context manager - flush buffered tasks and restore previous dispatcher.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        if exc_type:
            _logger.error("Exiting JobBundling context due to exception: %s", exc_type.__name__)
            logging.getLogger("slurminade").error("Aborted due to exception.")
            return
        _logger.info("Exiting JobBundling context, flushing buffered tasks")
        self.flush()
        set_dispatcher(self.subdispatcher)

    def _log_dispatch(self, funcs: typing.List[FunctionCall], options: SlurmOptions) -> None:
        """
        Log information about tasks being added to the batch.

        Args:
            funcs: List of function calls being added
            options: Slurm options for the tasks
        """
        if len(funcs) == 1:
            logging.getLogger("slurminade").info(
                "Adding task to batch with options %s: %s", options, funcs[0]
            )
        else:
            logging.getLogger("slurminade").info(
                "Adding %d tasks to batch with options %s: %s",
                len(funcs),
                options,
                ", ".join([str(f) for f in funcs]),
            )

    def __del__(self) -> None:
        """
        Destructor - flush any remaining buffered tasks on cleanup.
        """
        _logger.debug("JobBundling destructor called, flushing any remaining tasks")
        self.flush()

    def join(self) -> None:
        """
        Flush all buffered tasks and wait for subdispatcher to complete.
        """
        _logger.info("Joining JobBundling - flushing and waiting for completion")
        self.flush()
        return self.subdispatcher.join()

    def is_sequential(self) -> bool:
        """
        Check if the underlying subdispatcher executes sequentially.

        Returns:
            True if sequential, False otherwise
        """
        return self.subdispatcher.is_sequential()


class Batch(JobBundling):
    """
    Compatibility alias for JobBundling. This is the old name. Deprecated.

    .. deprecated::
        Use :class:`JobBundling` instead. This alias will be removed in a future version.
    """

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        """
        Initialize Batch (deprecated alias for JobBundling).

        Args:
            *args: Positional arguments passed to JobBundling
            **kwargs: Keyword arguments passed to JobBundling
        """
        super().__init__(*args, **kwargs)
        _logger.warning("Batch class is deprecated, use JobBundling instead")
        logging.getLogger("slurminade").warning(
            "The `Batch` class has been renamed to `JobBundling`. Please update your code."
        )
