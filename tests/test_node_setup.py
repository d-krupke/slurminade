from pathlib import Path

import slurminade

test_file_path = Path("./f_test_file.txt")


@slurminade.node_setup
def f():
    with test_file_path.open("w") as file:
        file.write("node_setup")


@slurminade.slurmify
def nil():
    pass


def test_node_setup():
    slurminade.set_entry_point(__file__)
    test_file_path.unlink(missing_ok=True)
    dispatcher = slurminade.SubprocessDispatcher()
    slurminade.set_dispatcher(dispatcher)
    slurminade.set_dispatch_limit(100)
    nil.distribute()
    with test_file_path.open() as file:
        assert file.readline() == "node_setup"
    if test_file_path.exists():  # delete the file
        test_file_path.unlink()
