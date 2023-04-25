import os.path
import unittest

import slurminade

f_file = "./f_test_file.txt"
g_file = "./g_test_file.txt"


@slurminade.slurmify()
def f():
    with open(f_file, "w") as file:
        file.write("test")


def delete_f():
    if os.path.exists(f_file):
        os.remove(f_file)


@slurminade.slurmify()
def g(x, y):
    with open(g_file, "w") as file:
        file.write(f"{x}:{y}")


def delete_g():
    if os.path.exists(g_file):
        os.remove(g_file)


def get_file_name():
    filename = os.getenv('PYTEST_CURRENT_TEST')  # doesn't seem to work always
    filename = filename.split("::")[0] if filename else __file__  #workaround
    if not os.path.exists(filename):  # sometimes the test folder gets duplicated.
        filename = "/".join(filename.split("/")[1:])
    return os.path.abspath(filename)


class TestSubprocess(unittest.TestCase):
    def test_1(self):
        slurminade.set_dispatcher(slurminade.SubprocessDispatcher())
        slurminade.set_dispatch_limit(100)
        slurminade.set_entry_point(get_file_name())

        delete_f()
        f.distribute()
        self.assertTrue(os.path.exists(f_file))
        delete_f()

    def test_2(self):
        slurminade.set_dispatcher(slurminade.SubprocessDispatcher())
        slurminade.set_entry_point(get_file_name())
        slurminade.set_dispatch_limit(100)

        delete_g()
        g.distribute(x="a", y=2)
        self.assertTrue(os.path.exists(g_file))
        with open(g_file, "r") as file:
            self.assertEqual(file.readline(), "a:2")
        delete_g()
