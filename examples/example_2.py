import datetime

# example with importing a function to be executed by node
from example_2b import f

import slurminade

slurminade.set_dispatch_limit(2)
slurminade.update_default_configuration(partition="alg", constraint="alggen02")


@slurminade.slurmify()
def g(hello_world):
    print("This function 'test' is in", __file__)
    with open("slurminade_example.txt", "w") as f_:
        f(hello_world)
        f_.write(hello_world)


if __name__ == "__main__":
    g.distribute("test f")
    f.distribute(f"Hello World from slurminade! {datetime.datetime.now()!s}")
