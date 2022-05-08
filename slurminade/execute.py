"""
This module provides the starting point for the slurm node. You do not have to call
anything of this file yourself.
"""

import sys

from slurminade.guard import prevent_distribution
from .function import SlurmFunction


def main():

    prevent_distribution()  # make sure, the code on the node does not distribute itself.
    batch_file = sys.argv[1]  # the file with the code (function definition)
    funcid = sys.argv[2]  # the function to be called
    args = sys.argv[3]  # the arguments to call the function with
    # Load the code
    SlurmFunction.set_entry_point(batch_file)
    with open(batch_file, "r") as f:
        code = "".join(f.readlines())

        # Workaround as otherwise __name__ is not defined
        global __name__
        __name__ = None

        exec(code, globals())
    # Execute the function
    SlurmFunction.call(funcid, args)


if __name__ == "__main__":
    main()
