"""
This module provides the starting point for the slurm node. You do not have to call
anything of this file yourself.
"""
import json
import pathlib
import sys

from .function import SlurmFunction
from .function_map import set_entry_point
from .guard import prevent_distribution


def parse_args():
    batch_file_path = pathlib.Path(
        sys.argv[1]
    )  # the file with the code (function definition)
    if not batch_file_path.exists():
        msg = "Batch file does not exist.\n"
        msg += f" File: {batch_file_path}\n"
        msg += "This should not happen. Please report this bug."
        raise RuntimeError(msg)
    # determine whether function calls are provided as an argument or in a temp file.
    mode = sys.argv[2]
    if mode == "arg":
        function_calls = json.loads(sys.argv[3])
    elif mode == "temp":
        tmp_file_path = pathlib.Path(sys.argv[3])
        if not tmp_file_path.exists():
            msg = "Using temporary file for passing function arguments, but file does not exist.\n"
            msg += f" File: {tmp_file_path}\n"
            msg += "This should not happen. Please report this bug."
            raise RuntimeError(msg)
        with open(tmp_file_path) as f:
            function_calls = json.load(f)
        tmp_file_path.unlink()  # delete the temp file
    else:
        msg = "Unknown function call mode. Expected 'arg' or 'temp'.\n"
        msg += f" Got: {mode}\n"
        msg += "This should not happen. Please report this bug."
        raise RuntimeError(msg)
    assert isinstance(function_calls, list), "Expected a list of dicts"
    return batch_file_path, function_calls


def main():
    prevent_distribution()  # make sure, the code on the node does not distribute itself.
    batch_file, function_calls = parse_args()

    set_entry_point(batch_file)
    with open(batch_file) as f:
        code = "".join(f.readlines())

    glob = dict(globals())
    glob["__file__"] = batch_file
    glob["__name__"] = None
    exec(code, glob)

    # Execute the functions
    for fc in function_calls:
        SlurmFunction.call(fc["func_id"], *fc.get("args", []), **fc.get("kwargs", {}))


if __name__ == "__main__":
    main()
