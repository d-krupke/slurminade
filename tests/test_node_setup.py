import slurminade
from pathlib import Path

test_file_path = Path("./f_test_file.txt")

@slurminade.node_setup
def f():
    with open(test_file_path, "w") as file:
        file.write('node_setup')

@slurminade.slurmify
def nil():
    pass

def test_node_setup():
    slurminade.set_entry_point(__file__)
    if test_file_path.exists():
        test_file_path.unlink()
    dispatcher = slurminade.SubprocessDispatcher()
    slurminade.set_dispatcher(dispatcher)
    slurminade.set_dispatch_limit(100)
    nil.distribute()
    with open(test_file_path) as file:
        assert file.readline() == 'node_setup'
    if test_file_path.exists():  # delete the file
        test_file_path.unlink()