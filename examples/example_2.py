import slurminade
import datetime

# example with importing a function to be executed by node
from example_2b import f

slurminade.update_default_configuration(partition="alg", constraint="alggen02")


@slurminade.slurmify()
def test(hello_world):
    with open("slurminade_example.txt", "w") as f_:
        f(hello_world)
        f_.write(hello_world)


if __name__ == "__main__":
    f.local("test f")
    test.local(f"Hello World from slurminade! {str(datetime.datetime.now())}")
