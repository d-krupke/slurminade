import os
import shlex
import unittest
from pathlib import Path

import slurminade
from slurminade.dispatcher import create_slurminade_command, FunctionCall


@slurminade.slurmify()
def f(s):
    pass


def delete_file(file):
    if os.path.exists(file):
        os.remove(file)


class TestCreateCommand(unittest.TestCase):
    def test_create_long_command(self):
        dummy_call = FunctionCall(f.func_id, ["." * 100], {})
        command = create_slurminade_command([dummy_call], 100)
        args = shlex.split(command)
        path = Path(args[-1])
        self.assertEqual(args[-2], "temp")
        # check creation of temporary file
        self.assertTrue(Path(path).is_file())
        delete_file(path)

    def test_create_short_command(self):
        dummy_call = FunctionCall(f.func_id, [""], {})
        command = create_slurminade_command([dummy_call], 100000)
        args = shlex.split(command)
        self.assertEqual(args[-2], "arg")





