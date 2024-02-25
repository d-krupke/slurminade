"""
The commands that can be understood by execute.py
"""

import json
import logging
import os
import shlex
import subprocess
import sys
import typing
from pathlib import Path
from tempfile import mkstemp

from .function_call import FunctionCall


def create_slurminade_command(
    entry_point: Path, funcs: typing.Iterable[FunctionCall], max_arg_length: int
) -> str:
    """
    Creates a terminal command that calls the Python module `slurminade.execute` with the
    provided function calls as an argument. If the total length of the function calls
    exceeds the maximum allowed length of a command line argument, a temporary file is
    created to pass the function calls instead.
    :param funcs: The function calls to be dispatched.
    :param max_arg_length: The maximum allowed length of a command line argument.
    :returns: A string representing the command to be executed in the terminal.
    """
    if not entry_point.exists():
        msg = f"Entry point {entry_point} does not exist."
        raise FileNotFoundError(msg)

    command = (
        f"{sys.executable} -m slurminade.execute --root {shlex.quote(str(entry_point))}"
    )

    # Serialize function calls as JSON
    json_calls = json.dumps([f.to_json() for f in funcs])
    serialized_calls = shlex.quote(json_calls)

    if len(serialized_calls) > max_arg_length:
        # The argument is too long, create temporary file for the JSON
        fd, filename = mkstemp(prefix="slurminade_", suffix=".json", text=True, dir=".")
        logging.getLogger("slurminade").info(
            f"Long function calls. Serializing function calls to temporary file {filename}"
        )
        with os.fdopen(fd, "w") as f:
            f.write(json_calls)
        command += f" --fromfile {filename}"
    else:
        command += f" --calls {serialized_calls}"
    return command


def call_slurminade_to_get_function_ids(entry_point: Path) -> typing.Set[str]:
    cmd = [
        sys.executable,
        "-m",
        "slurminade.execute",
        "--root",
        str(entry_point),
        "--listfuncs",
    ]
    out = subprocess.check_output(cmd).decode()
    ids = json.loads(out)
    return set(ids)
