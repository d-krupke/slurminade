from pathlib import Path

import slurminade

test_file_path = Path("./f_test_file.txt")
print("NOISE123")


@slurminade.slurmify()
def f(s):
    with test_file_path.open("w") as file:
        file.write(s)


def test_create_command_with_noise():
    slurminade.set_entry_point(__file__)
    if test_file_path.exists():
        test_file_path.unlink()
    dispatcher = slurminade.SubprocessDispatcher()
    dispatcher.max_arg_length = 1
    slurminade.set_dispatcher(dispatcher)
    s = "test"
    f.distribute(s)
    assert test_file_path.is_file()
    with test_file_path.open() as file:
        assert file.readline() == s
    test_file_path.unlink(missing_ok=True)
