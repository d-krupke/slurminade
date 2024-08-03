from pathlib import Path

import slurminade
from slurminade.function import SlurmFunction

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


def test_local_1():
    delete_f()
    SlurmFunction.call(f.func_id)
    assert Path(f_file).exists()
    delete_f()


def test_local_2():
    delete_g()
    SlurmFunction.call(g.func_id, x="a", y=2)

    assert Path(g_file).exists()
    with Path(g_file).open() as file:
        assert file.readline() == "a:2"
    delete_g()
