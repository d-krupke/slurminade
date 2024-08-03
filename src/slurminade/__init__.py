"""
slurminade allows to distribute function calls to slurm using decorators.

.. code-block:: python

    import slurminade

    slurminade.update_default_configuration(partition="alg")  # global options for slurm

    # If no slurm environment is found, the functions are called directly to make scripts
    # compatible with any environment.
    # You can enforce slurm with `slurminade.set_dispatcher(slurminade.SlurmDispatcher())`


    # use this decorator to make a function distributable with slurm
    @slurminade.slurmify(
        constraint="alggen02"
    )  # function specific options can be specified
    def prepare():
        print("Prepare")


    @slurminade.slurmify()
    def f(foobar):
        print(f"f({foobar})")


    @slurminade.slurmify()
    def clean_up():
        print("Clean up")


    if __name__ == "__main__":
        jid = prepare.distribute()

        with slurminade.Batch(max_size=20) as batch:  # automatically bundles up to 20 tasks
            # run 100x f after `prepare` has finished
            for i in range(100):
                f.wait_for(jid).distribute(i)

            # clean up after the previous jobs have finished
            jids = batch.flush()
            clean_up.wait_for(jids).distribute()


Project structure:
- batch.py: Contains code for bundling tasks, so we don't spam slurm with too many.
- conf.py: Contains code for managing the configuration of slurm.
- dispatcher.py: Contains code for actually dispatching tasks to slurm.
- execute.py: Contains code to execute the task on the slurm node.
- function.py: Contains the code for making a function slurm-compatible.
- function_map.py: Saves all the slurified functions.
- guard.py: Contains code to prevent you accidentally DDoSing your infrastructure.
- options.py: Contains a simple data structure to save slurm options.
"""

# set default logging
import logging
import sys

# Set up the root logger to print to stdout by default
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# flake8: noqa F401
from .bundling import Batch, JobBundling
from .conf import set_default_configuration, update_default_configuration
from .dispatcher import (
    SlurmDispatcher,
    SubprocessDispatcher,
    TestDispatcher,
    get_dispatcher,
    join,
    sbatch,
    set_dispatcher,
    srun,
)
from .function import shell, slurmify
from .function_map import set_entry_point
from .guard import (
    allow_recursive_distribution,
    disable_warning_on_repeated_flushes,
    set_dispatch_limit,
)
from .node_setup import node_setup

__all__ = [
    "slurmify",
    "update_default_configuration",
    "set_default_configuration",
    "set_dispatch_limit",
    "allow_recursive_distribution",
    "disable_warning_on_repeated_flushes",
    "JobBundling",
    "Batch",
    "srun",
    "join",
    "sbatch",
    "SlurmDispatcher",
    "set_dispatcher",
    "get_dispatcher",
    "TestDispatcher",
    "SubprocessDispatcher",
    "set_entry_point",
    "shell",
    "node_setup",
]
