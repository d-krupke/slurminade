import socket
import tempfile
import time
from pathlib import Path

import click

from slurminade import join, slurmify, srun


@slurmify()
def _write_to_file(path, content):
    time.sleep(1)
    # get hostname and write it to the file
    hostname = socket.gethostname()
    with open(path, "w") as file:
        print("Hello from ", hostname)
        file.write(content + "\n" + hostname)
    # wait a second for the file to be written
    time.sleep(1)


@click.command()
@click.option("--partition", default=None, help="The partition to use.")
@click.option("--constraint", default=None, help="The constraint to use.")
def check_slurm(partition, constraint):
    """
    Check if the code is running on a slurm node.
    """
    # enforce slurm
    from slurminade.conf import update_default_configuration
    from slurminade.dispatcher import SlurmDispatcher, set_dispatcher
    from slurminade.function_map import set_entry_point

    set_dispatcher(SlurmDispatcher())
    print("Setting entry point to ", Path(__file__).resolve())
    set_entry_point(Path(__file__).resolve())

    if partition:
        update_default_configuration(partition=partition)
    if constraint:
        update_default_configuration(constraint=constraint)

    # create a temporary folder for the slurm check
    with tempfile.TemporaryDirectory(dir=".") as tmpdir:
        tmpdir = Path(tmpdir).resolve()
        assert Path(tmpdir).exists()
        # Check 1
        tmp_file_path = tmpdir / "check_1.txt"
        _write_to_file.distribute_and_wait(str(tmp_file_path), "test")
        if not Path(tmp_file_path).exists():
            msg = "Slurminade failed: The file was not written to the temporary directory."
            raise Exception(msg)
        with open(tmp_file_path) as file:
            content = file.readlines()
            print(
                "Slurminade check 1 successful. Test was run on node",
                content[1].strip(),
            )

        # Check 2
        tmp_file_path = tmpdir / "check_2.txt"
        _write_to_file.distribute(str(tmp_file_path), "test")
        # wait up to 1 minutes for the file to be written
        for _ in range(60):
            if Path(tmp_file_path).exists():
                break
            time.sleep(1)
        if not Path(tmp_file_path).exists():
            msg = "Slurminade failed: The file was not written to the temporary directory."
            raise Exception(msg)
        with open(tmp_file_path) as file:
            content = file.readlines()
            print(
                "Slurminade check 2 successful. Test was run on node",
                content[1].strip(),
            )

        join()

        # Check 3
        tmp_file_path = tmpdir / "check_3.txt"
        srun(["touch", str(tmp_file_path)])
        time.sleep(1)
        if not Path(tmp_file_path).exists():
            msg = "Slurminade failed: The file was not written to the temporary directory."
            raise Exception(msg)
        print("Slurminade check 3 successful.")
        tmp_file_path.unlink()

        # Check 4
        tmp_file_path = tmpdir / "check_4.txt"
        _write_to_file.distribute_and_wait(str(tmp_file_path), "test")
        if not Path(tmp_file_path).exists():
            msg = "Slurminade failed: The file was not written to the temporary directory."
            raise Exception(msg)
        with open(tmp_file_path) as file:
            content = file.readlines()
            print(
                "Slurminade check 1 successful. Test was run on node",
                content[1].strip(),
            )


if __name__ == "__main__":
    check_slurm()
