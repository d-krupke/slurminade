"""
This module provides the starting point for the slurm node. You do not have to call
anything of this file yourself.
"""
import os

from .guard import prevent_distribution
from .function import SlurmFunction
from .function_map import set_entry_point
import json
import sys


def parse_args():
    batch_file_path = sys.argv[1]  # the file with the code (function definition)
    # determine whether function calls are provided as an argument or in a temp file.
    mode = sys.argv[2]
    if mode == "arg":
        function_calls = json.loads(sys.argv[3])
    elif mode == "temp":
        with open(sys.argv[3]) as f:
            function_calls = json.load(f)
        os.remove(sys.argv[3])  # delete the temp file
    else:
        raise ValueError("Unknown function call mode. Expected 'arg' or 'temp'.")
    assert isinstance(function_calls, list), "Expected a list of dicts"
    return batch_file_path, function_calls


def main():
    prevent_distribution()  # make sure, the code on the node does not distribute itself.
    batch_file, function_calls = parse_args()

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
    for fc in function_calls:
        SlurmFunction.call(fc["func_id"], *fc.get("args", []), **fc.get("kwargs", {}))


if __name__ == "__main__":
    main()
