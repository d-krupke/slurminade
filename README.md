# slurminade

*slurminade* makes using the workload manager [slurm](https://slurm.schedmd.com/documentation.html) with Python beautiful.
It is based on [simple_slurm](https://github.com/amq92/simple_slurm), but instead of just allowing to comfortably execute shell commands in slurm, it allows to directly distribute Python-functions.
A function decorated with `@slurminade.slurmify(partition="alg")` will automatically be executed by a node of the partition `alg` by just calling `.distribute(yes_also_args_are_allowed)`.
The general idea is that the corresponding Python-code exists on both machines, thus, the slurm-node can also call the functions of the original code if you tell if which one and what arguments to use.
This is similar to [celery](https://github.com/celery/celery) but you do not need to install anything, just make sure the same Python-environment is available the nodes (usually the case in a proper slurm setup).

Please check the documentation of [simple_slurm](https://github.com/amq92/simple_slurm) to get to know more about the
possible parameters. You can also call simple_slurm directly by `srun` and `sbatch` (automatically with the 
configuration specified with slurminade).

A simple script that executes a function three times on slurm-nodes could look like this:
```python

import slurminade
import datetime

# Settings for slurm
slurminade.update_default_configuration(partition="alg", constraint="alggen02")


@slurminade.slurmify()
def test(file_name, text):
    with open(file_name, "w") as f:
        f.write(text)

# Without the `if`, the node would also execute this part (*slurminade* will abort automatically)
if __name__ == "__main__":
    # Call the function remotely.
    test.distribute("slurminade_test_1.txt", f"Hello World from slurminade! {str(datetime.datetime.now())}")
    test.distribute("slurminade_test_2.txt", f"Hello World from slurminade! {str(datetime.datetime.now())}")
    test.distribute("slurminade_test_3.txt", f"Hello World from slurminade! {str(datetime.datetime.now())}")
```

> :warning: You should not use this to spam your slurm environment with tasks. Only distribute a function call if it takes at least a few seconds, otherwise it will be faster to run it locally.

We recommend to use *slurminade* with [conda](https://docs.conda.io/en/latest/).
We have not tested it with other virtual environments.

The code is super simple and open source, don't be afraid to create a fork that fits your own needs.

If slurm is not available, `distribute` results in a local function call.
To enforce a distribution to a slurm node, use `force_distribute`.
Currently, `srun` and `sbatch` will still fail without a *slurm* environment.

## Installation

You can install *slurminade* with `pip install slurminade`.

> :warning: *slurminade* is still under development. I tested it only for some simple use cases. Please expect some bugs.

## Usage

You can set task specific slurm arguments within the decorator, e.g., `@slurminade.slurmify(constraint="alggen03")`.
These arguments are directly passed to *simple_slurm*, such that all its arguments are supported.

In order for *slurminade* to work, the code needs to be in a Python file/project shared by all slurm-nodes.
Otherwise, *slurminade* will not find the corresponding function.
The slurmified functions also must be importable, i.e., on the top level.
Currently, all function names must be unique as *slurminade* will only transmit the function's name.

## Don't do:

### Bad: System calls
```python
import slurminade
import os
@slurminade.slurmify()
def run_shell_command():
    os.system("complex call")
    # BAD! The system call will run outside of slurm! The slurm task directly terminates.
```
instead use
```python
import slurminade

if __name__=="__main__":
    slurminade.sbatch("complex call")  # forwards your call to simple_slurm that is better used for such things.
```

### Bad: Global variables

```python
import slurminade

FLAG = True

@slurminade.slurmify()
def bad_global(args):
    if FLAG:  # BAD! Will be True because the __main__ Part is not executed on the node.
        pass
    else:
        pass

# Without the `if`, the node would also execute this part (*slurminade* will abort automatically)
if __name__ == "__main__":
    FLAG = False
    bad_global.distribute("args")
```
instead do
```python
import slurminade
@slurminade.slurmify()
def bad_global(args, FLAG):  # Now the flag is passed correctly as an argument. Note that only json-compatible arguments are possible.
    if FLAG: 
        pass
    else:
        pass

# Without the `if`, the node would also execute this part (*slurminade* will abort automatically)
if __name__ == "__main__":
    FLAG = False
    bad_global.distribute("args", FLAG)
```
> :warning The same is true for any global state such as file or database connections.

### Error: Complex objects as arguments

```python
import slurminade

@slurminade.slurmify()
def sec_order_func(func):  
    func()  
    
def f():
    print("hello")
    
def g():
    print("world!")
    
if __name__=="__main__":
    sec_order_func.distribute(f)  # will throw an exception 
    sec_order_func.distribute(g)
```
Instead, create individual slurmified functions for each call or pass a simple identifier that lets the function
deduce, what to do, e.g., a switch-case.
If you really need to pass complex objects, you could also pickle the object and only pass the file name.

## Default configuration

You can set up a default configuration in `~/slurminade_default.json`.
This should simply be a dictionary of arguments for *simple_slurm*.
For example
```json
{
  "partition": "alg"
}
```

## Debugging

You can use `.local` instead of `.distribute` to run the task on the local computer, 
without slurm. If there is a bug, you will directly see it in the output (at least for most bugs).
