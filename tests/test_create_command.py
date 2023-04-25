import shlex
import unittest
from pathlib import Path

import slurminade
from slurminade.dispatcher import create_slurminade_command, FunctionCall

test_file_path = Path("./f_test_file.txt")


@slurminade.slurmify()
def f(s):
    with open(test_file_path, "w") as file:
        file.write(s)


class TestCreateCommand(unittest.TestCase):
    def test_create_long_command(self):
        test_call = FunctionCall(f.func_id, ["." * 100], {})
        command = create_slurminade_command([test_call], 100)
        args = shlex.split(command)
        path = Path(args[-1])
        self.assertEqual(args[-2], "temp")
        # check creation of temporary file
        self.assertTrue(Path(path).is_file())
        path.unlink(missing_ok=True)    # delete the file

    def test_create_short_command(self):
        test_call = FunctionCall(f.func_id, [""], {})
        command = create_slurminade_command([test_call], 100000)
        args = shlex.split(command)
        self.assertEqual(args[-2], "arg")

    def test_dispatch_with_temp_file(self):
        slurminade.set_entry_point(__file__)
        test_file_path.unlink(missing_ok=True)
        dispatcher = slurminade.SubprocessDispatcher()
        dispatcher.max_arg_length = 1
        slurminade.set_dispatcher(dispatcher)
        s = "test"
        f.distribute(s)
        self.assertTrue(test_file_path.is_file())
        with open(test_file_path, "r") as file:
            self.assertEqual(file.readline(), s)
        test_file_path.unlink(missing_ok=True)   # delete the file
