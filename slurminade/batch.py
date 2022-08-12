import shutil
import typing
from collections import defaultdict

from slurminade.dispatcher import Dispatcher
from slurminade.dispatcher import get_dispatcher, FunctionCall, set_dispatcher
from slurminade.function import SlurmFunction
from slurminade.options import SlurmOptions


class TaskContainer:
    def __init__(self):
        self._tasks = defaultdict(list)

    def add(self, task: FunctionCall,
            options: SlurmOptions) -> int:
        self._tasks[options].append(task)
        return len(self._tasks[options])

    def items(self):
        for opt, tasks in self._tasks.items():
            if tasks:
                yield opt, tasks

    def get(self, options: SlurmOptions) -> typing.List[FunctionCall]:
        return self._tasks[options]

    def clear(self):
        self._tasks.clear()


class Batch(Dispatcher):
    def __init__(self, max_size: int):
        super().__init__()
        self.max_size = max_size
        self.subdispatcher = get_dispatcher()
        self._tasks = TaskContainer()

    def flush(self, options: typing.Optional[SlurmOptions] = None)\
            -> typing.Iterable[int]:
        job_ids = []
        if options is None:
            for opt, tasks in self._tasks.items():
                while tasks:
                    job_id = self.subdispatcher(tasks[:self.max_size], opt)
                    job_ids.append(job_id)
                    tasks = tasks[self.max_size:]

        else:
            tasks = self._tasks.get(options)
            while len(tasks) > self.max_size:
                job_id = self.subdispatcher(tasks[:self.max_size], options)
                job_ids.append(job_id)
                tasks = tasks[:self.max_size]
        self._tasks.clear()
        return job_ids

    def add(self, func: SlurmFunction, *args, **kwargs):
        self._dispatch([FunctionCall(func.func_id, args, kwargs)],
                       func.special_slurm_opts)

    def _dispatch(self, funcs: typing.Iterable[FunctionCall],
                  options: SlurmOptions) -> int:
        for func in funcs:
            self._tasks.add(func, options)
        return -1

    def srun(self, command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
        return self.subdispatcher.srun(command, conf, simple_slurm_kwargs)

    def sbatch(self, command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
        return self.subdispatcher.sbatch(command, conf, simple_slurm_kwargs)

    def __enter__(self):
        self.subdispatcher = get_dispatcher()
        set_dispatcher(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            print("Aborted due to exception.")
            return
        self.flush()
        set_dispatcher(self.subdispatcher)

    def is_sequential(self):
        return self.subdispatcher.is_sequential()