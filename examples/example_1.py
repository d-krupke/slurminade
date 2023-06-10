import datetime

import slurminade
from slurminade import Batch

slurminade.update_default_configuration(partition="alg", constraint="alggen02")


@slurminade.slurmify()
def f(hello_world):
    with open("slurminade_example.txt", "a") as f:
        print("hello")
        f.write(hello_world + "\n")


if __name__ == "__main__":
    jid = f.distribute(f"Hello World from slurminade! {datetime.datetime.now()!s}")
    with Batch(20) as batch:
        f.distribute("hello 1!")
        f.distribute("hello 2!")
