import inspect
import shutil
import subprocess
import json
import os
import simple_slurm

from .dispatcher import Dispatcher, _FunctionCall
from .guard import guard_recursive_distribution
from .conf import _get_conf


class SlurmFunction:
    dispatcher = Dispatcher()
    function_map = {}
    entry_point = None

    @staticmethod
    def set_entry_point(entry_point: str) -> None:
        """
        This function usually is not necessary for endusers.
        Set a manual entry point. This can allow you to use slurmify from the interactive
        interpreter. It is also necessary, for slurmindae in the slurm node, because
        the entry point will be executed not by file but by exec(file_content).
        :param entry_point: A path to the entry point file.
        :return: None
        """
        SlurmFunction.dispatcher.set_default_entry_point(entry_point)
        SlurmFunction.entry_point = entry_point

    def __init__(self, special_slurm_opts, func):
        if (
            not func.__name__
            or func.__name__ == "<lambda>"
            or not inspect.getfile(func)
        ):
            raise ValueError("Can only slurmify proper functions.")
        self.special_slurm_opts = special_slurm_opts
        self.func = func
        self.func_id = self._get_func_id(func)
        if self.func_id in self.function_map:
            raise RuntimeError("Multiple function definitions!")
        self.function_map[self.func_id] = func

    def _get_func_id(self, func):
        file = inspect.getfile(func)
        if file == "<string>":  # on the slurm node, the functions in the entry point
            # are named `<string>`.
            file = self.entry_point
        path = os.path.normpath(os.path.abspath(file))
        return f"{path}:{func.__name__}"

    def _check(self, args, kwargs):
        """
        Check if the arguments match the function signature.
        """
        inspect.signature(self.func).bind(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def distribute(self, *args, **kwargs):
        """
        Try to distribute function call. If slurm is not available, a direct function
        call will be performed.
        Call with function arguments.
        :return: True if distributed to slurm.
        """
        if shutil.which("sbatch"):
            self.force_distribute(*args, **kwargs)
            return True
        else:
            print(
                "SBATCH is not available. Running code locally. "
                "If you do not want this, use `force_distribute'."
            )
            self(*args, **kwargs)
            return False

    def force_distribute(self, *args, **kwargs):
        """
        Distribute to slurm. Will throw an error if slurm is not available.
        """
        self._check(args, kwargs)
        guard_recursive_distribution()
        self.dispatcher.dispatch_to_slurm(
            _FunctionCall(self.func_id, args=args, kwargs=kwargs),
            self.special_slurm_opts,
        )

    def local(self, *args, **kwargs):
        """
        This function simulates a distribution but runs on the local computer.
        Great for debugging.
        """
        self._check(args, kwargs)
        self.dispatcher.dispatch_locally(
            _FunctionCall(self.func_id, args=args, kwargs=kwargs)
        )

    @staticmethod
    def call(func_id, argj):
        argd = json.loads(argj)
        SlurmFunction.function_map[func_id](*argd["args"], **argd["kwargs"])


def slurmify(f=None, **args):
    """
    Decorator: Make a function distributable to slurm.
    Usage:
    ```
    @slurimfy()
    def func(a, b):
        pass
    ```
    :param f: Function
    :param args: Special slurm options for this function.
    :return: A decorated function, callable with slurm.
    """

    if f:  # use default parameters

        return SlurmFunction({}, f)
    else:

        def dec(func):
            return SlurmFunction(args, func)

        return dec


def force_srun(command, conf: dict = None, simple_slurm_kwargs: dict = None):
    """
    Just calling simple_slurm's srun but with default parameters of slurminade.
    `srun` executes the command on a slurm node but waits for the return.
    :param command: The command to be executed.
    :param conf: Slurm configuration changes just for this command.
    :param simple_slurm_kwargs: Use this to change the arguments passed to simple_slurm.
    :return: The return of `simple_slurm.srun`.
    """
    conf = _get_conf(conf)
    slurm = simple_slurm.Slurm(**conf)
    if simple_slurm_kwargs:
        return slurm.srun(command, **simple_slurm_kwargs)
    else:
        return slurm.srun(command)


def srun(command, conf: dict = None, simple_slurm_kwargs: dict = None):
    """
    Just calling simple_slurm's srun but with default parameters of slurminade.
    `srun` executes the command on a slurm node but waits for the return.
    If slurm is not available, the command will be executed locally.
    :param command: The command to be executed.
    :param conf: Slurm configuration changes just for this command.
    :param simple_slurm_kwargs: Use this to change the arguments passed to simple_slurm.
    :return: The return of `simple_slurm.srun`.
    """
    if shutil.which("srun"):
        force_srun(command, conf, simple_slurm_kwargs)
    else:
        print(
            "SRUN is not available. Running code locally. "
            "If you do not want this, use `force_srun'."
        )
        subprocess.run(command, check=True)


def force_sbatch(command, conf: dict = None, simple_slurm_kwargs: dict = None):
    """
    Just calling simple_slurm's sbatch but with default parameters of slurminade.
    `sbatch` executes the command on a slurm node and returns directly.
    :param command: The command to be executed.
    :param conf: Slurm configuration changes just for this command.
    :param simple_slurm_kwargs: Use this to change the arguments passed to simple_slurm.
    :return: The return of `simple_slurm.sbatch`.
    """
    conf = _get_conf(conf)
    slurm = simple_slurm.Slurm(**conf)
    if simple_slurm_kwargs:
        return slurm.sbatch(command, **simple_slurm_kwargs)
    else:
        return slurm.sbatch(command)


def sbatch(command, conf: dict = None, simple_slurm_kwargs: dict = None):
    """
    Just calling simple_slurm's sbatch but with default parameters of slurminade.
    `sbatch` executes the command on a slurm node and returns directly.
    If slurm is not available, the command will be executed locally.
    :param command: The command to be executed.
    :param conf: Slurm configuration changes just for this command.
    :param simple_slurm_kwargs: Use this to change the arguments passed to simple_slurm.
    :return: The return of `simple_slurm.sbatch`.
    """
    if shutil.which("sbatch"):
        force_srun(command, conf, simple_slurm_kwargs)
    else:
        print(
            "sbatch is not available. Running code locally. "
            "If you do not want this, use `force_sbatch'."
        )
        subprocess.run(command, check=True)
