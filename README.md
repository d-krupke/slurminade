# slurminade
A decorator-based slurm runner.

## Installation

Simply install via pip `pip install slurminade`.

## Usage

Important: *slurminade* only works when used within a regular Python-file.
This file needs to be available on all slurm nodes to reconstruct the functions.

```python

import slurminade
import datetime

# Settings for slurm
slurminade.update_default_configuration(partition="alg", constraint="alggen02")


@slurminade.slurmify()
def test(hello_world):
    with open("slurminade_example.txt", "w") as f:
        f.write(hello_world)

# This 'if' is critical as this code is also executed on the node to reconstruct the function.
if __name__ == "__main__":
    # Call the function remotely.
    test.distribute(f"Hello World from slurminade! {str(datetime.datetime.now())}")
```

## Debugging

You can use `.local` instead of `.distribute` to run the task on the local computer, 
without slurm. You will see all output.