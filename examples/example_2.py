import slurminade
import datetime

# example with importing a function to be executed by node
from example_2b import f

slurminade.set_dispatch_limit(1)
slurminade.update_default_configuration(partition="alg", constraint="alggen02")


@slurminade.slurmify()
def test(hello_world):
    print("This function 'test' is in", __file__)
    with open("slurminade_example.txt", "w") as f_:
        f(hello_world)
        f_.write(hello_world)


if __name__ == "__main__":
    f.distribute("test f")
    test.distribute(f"Hello World from slurminade! {str(datetime.datetime.now())}")
