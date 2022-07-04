import slurminade
import datetime

from slurminade import AutoBatch

slurminade.update_default_configuration(partition="alg", constraint="alggen02")


@slurminade.slurmify()
def test(hello_world):
    with open("slurminade_example.txt", "w") as f:
        print("hello")
        f.write(hello_world)


if __name__ == "__main__":
    test.local(f"Hello World from slurminade! {str(datetime.datetime.now())}")
    with AutoBatch() as batch:
        batch.add(test, "hello 1!")
        batch.add(test, "hello 2!")
