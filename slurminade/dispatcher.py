import abc
import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
import typing

import simple_slurm

from slurminade.conf import _get_conf
from slurminade.function_map import FunctionMap
from slurminade.options import SlurmOptions


class FunctionCall:
    def __init__(self, func_id, args, kwargs):
        self.func_id = func_id
        self.args = args
        self.kwargs = kwargs

    def to_json(self):
        return {"func_id": self.func_id, "args": self.args, "kwargs": self.kwargs}


class Dispatcher(abc.ABC):
    def __init__(self):
        import __main__
        self.entry_point = __main__.__file__

    @abc.abstractmethod
    def _dispatch(self, funcs: typing.Iterable[FunctionCall],
                  options: SlurmOptions) -> int:
        pass

    @abc.abstractmethod
    def srun(self, command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
        pass

    @abc.abstractmethod
    def sbatch(self, command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
        pass

    def __call__(self,
                 funcs: typing.Union[FunctionCall, typing.Iterable[FunctionCall]],
                 options: SlurmOptions) -> int:
        if isinstance(funcs, FunctionCall):
            funcs = [funcs]
        return self._dispatch(funcs, options)

    def is_sequential(self):
        return False


class TestDispatcher(Dispatcher):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.sbatches = []
        self.sruns = []

    def _dispatch(self, funcs: typing.Iterable[FunctionCall],
                  options: SlurmOptions) -> int:
        funcs = list(funcs)
        print(f"{sys.executable} -m slurminade.execute"
            f" {shlex.quote(self.entry_point)}"
            f" {shlex.quote(json.dumps([f.to_json() for f in funcs]))}")
        self.calls.append(funcs)
        return -1

    def srun(self, command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
        self.sruns.append(command)
        print("SRUN", command)

    def sbatch(self, command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
        self.sbatches.append(command)
        print("SBATCH", command)

    def is_sequential(self):
        return True


class SlurmDispatcher(Dispatcher):
    def __init__(self):
        super().__init__()
        if not shutil.which("sbatch"):
            raise RuntimeError("Slurm could not be found.")

    def _create_slurm_api(self, special_slurm_opts):
        conf = _get_conf(special_slurm_opts)
        slurm = simple_slurm.Slurm(**conf)
        return slurm

    def _dispatch(self, funcs: typing.Iterable[FunctionCall],
                  options: SlurmOptions) -> int:
        slurm = self._create_slurm_api(options)
        return slurm.sbatch(
            f"{sys.executable} -m slurminade.execute"
            f" {shlex.quote(self.entry_point)}"
            f" {shlex.quote(json.dumps([f.to_json() for f in funcs]))}"
        )

    def sbatch(self, command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
        conf = _get_conf(conf)
        slurm = simple_slurm.Slurm(**conf)
        if simple_slurm_kwargs:
            return slurm.sbatch(command, **simple_slurm_kwargs)
        else:
            return slurm.sbatch(command)

    def srun(self, command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
        conf = _get_conf(conf)
        slurm = simple_slurm.Slurm(**conf)
        if simple_slurm_kwargs:
            return slurm.srun(command, **simple_slurm_kwargs)
        else:
            return slurm.srun(command)


class SubprocessDispatcher(Dispatcher):
    def _dispatch(self, funcs: typing.Iterable[FunctionCall],
                  options: SlurmOptions) -> int:
        os.system(
            f"{sys.executable} -m slurminade.execute"
            f" {shlex.quote(self.entry_point)}"
            f" {shlex.quote(json.dumps([f.to_json() for f in funcs]))}"
        )
        return -1

    def srun(self, command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
        subprocess.run(command, check=True)

    def sbatch(self, command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
        self.srun(command)

    def is_sequential(self):
        return True

class DirectCallDispatcher(Dispatcher):
    def _dispatch(self, funcs: typing.Iterable[FunctionCall],
                  options: SlurmOptions) -> int:
        for func in funcs:
            FunctionMap.call(func.func_id, func.args, func.kwargs)
        return -1

    def srun(self, command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
        subprocess.run(command, check=True)

    def sbatch(self, command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
        self.srun(command)

    def is_sequential(self):
        return True

__dispatcher: typing.Optional[Dispatcher] = None


def get_dispatcher() -> Dispatcher:
    global __dispatcher
    if __dispatcher is None:
        try:
            __dispatcher = SlurmDispatcher()
        except RuntimeError as re:
            logging.getLogger("slurminade").warning(str(re))
            logging.getLogger("slurminade").warning("Using direct calls.")
            __dispatcher = DirectCallDispatcher()
    return __dispatcher


def set_dispatcher(dispatcher: Dispatcher):
    global __dispatcher
    __dispatcher = dispatcher
    assert dispatcher == get_dispatcher()


def dispatch(funcs: typing.Union[FunctionCall, typing.Iterable[FunctionCall]],
             options: SlurmOptions) -> int:
    return get_dispatcher()(funcs, options)


def srun(command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
    return get_dispatcher().srun(command, conf, simple_slurm_kwargs)


def sbatch(command: str, conf: dict = None, simple_slurm_kwargs: dict = None):
    return get_dispatcher().sbatch(command, conf, simple_slurm_kwargs)
