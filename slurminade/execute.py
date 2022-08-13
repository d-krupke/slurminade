"""
This module provides the starting point for the slurm node. You do not have to call
anything of this file yourself.
"""

import sys

from .guard import prevent_distribution
from .function import SlurmFunction
from .function_map import set_entry_point
import json


def main():

    prevent_distribution()  # make sure, the code on the node does not distribute itself.
    batch_file = sys.argv[1]  # the file with the code (function definition)
    instructions = sys.argv[2]
    # Load the code
    set_entry_point(batch_file)
    with open(batch_file, "r") as f:
        code = "".join(f.readlines())

        # Workaround as otherwise __name__ is not defined
        global __name__
        __name__ = None

        glob = dict(globals())
        glob["__file__"] = batch_file
        exec(code, glob)
    # Execute the functions
    argd = json.loads(instructions)
    assert isinstance(argd, list), "Should be a list of dicts"
    for fc in argd:
        SlurmFunction.call(fc["func_id"], *fc.get("args", []), **fc.get("kwargs", {}))


if __name__ == "__main__":
    main()
