import os
from pathlib import Path

import slurminade

f_file = "./f_test_file.txt"
g_file = "./g_test_file.txt"


@slurminade.slurmify()
def f():
    with Path(f_file).open("w") as file:
        file.write("test")


def delete_f():
    Path(f_file).unlink(missing_ok=True)


@slurminade.slurmify()
def g(x, y):
    with Path(g_file).open("w") as file:
        file.write(f"{x}:{y}")


def delete_g():
    Path(g_file).unlink(missing_ok=True)


def get_file_name():
    filename = os.getenv("PYTEST_CURRENT_TEST")  # doesn't seem to work always
    filename = filename.split("::")[0] if filename else __file__  # workaround
    if not Path(filename).exists():  # sometimes the test folder gets duplicated.
        filename = "/".join(filename.split("/")[1:])
    return Path(filename).resolve()


def test_subprocess_1():
    slurminade.set_dispatcher(slurminade.SubprocessDispatcher())
    slurminade.set_dispatch_limit(100)
    slurminade.set_entry_point(get_file_name())

    delete_f()
    f.distribute()
    assert Path(f_file).exists()
    delete_f()


def test_subprocess_2():
    slurminade.set_dispatcher(slurminade.SubprocessDispatcher())
    slurminade.set_entry_point(get_file_name())
    slurminade.set_dispatch_limit(100)

    delete_g()
    g.distribute(x="a", y=2)
    assert Path(g_file).exists()
    with Path(g_file).open() as file:
        assert file.readline() == "a:2"
    delete_g()
