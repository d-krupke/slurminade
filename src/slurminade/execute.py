"""
This module provides the starting point for the slurm node. You do not have to call
anything of this file yourself.
"""

import json
import logging
from pathlib import Path

import click

from .function import FunctionMap, SlurmFunction
from .function_map import set_entry_point
from .guard import prevent_distribution


@click.command()
@click.option(
    "--root",
    type=click.Path(exists=True),
    help="The root file of the task.",
    required=True,
)
@click.option("--calls", type=str, help="The function calls.", required=False)
@click.option(
    "--fromfile",
    type=click.Path(exists=True),
    help="The file to read the function calls from.",
    required=False,
)
@click.option(
    "--listfuncs",
    help="List all available functions.",
    default=False,
    is_flag=True,
    required=False,
)
def main(root, calls, fromfile, listfuncs):
    prevent_distribution()  # make sure, the code on the node does not distribute itself.

    set_entry_point(root)
    with open(root) as f:
        code = "".join(f.readlines())

    glob = dict(globals())
    glob["__file__"] = root
    glob["__name__"] = None
    exec(code, glob)

    if listfuncs:
        print(json.dumps(FunctionMap.get_all_ids()))  # noqa T201
        return
    if calls:
        function_calls = json.loads(calls)
    elif fromfile:
        with open(fromfile) as f:
            logging.getLogger("slurminade").info(
                f"Reading function calls from {fromfile}."
            )
            function_calls = json.load(f)
        Path(fromfile).unlink()
    else:
        msg = "No function calls provided."
        raise ValueError(msg)
    if not isinstance(function_calls, list):
        msg = "Expected a list of function calls."
        raise ValueError(msg)
    # Execute the functions
    for fc in function_calls:
        SlurmFunction.call(fc["func_id"], *fc.get("args", []), **fc.get("kwargs", {}))


if __name__ == "__main__":
    main()
