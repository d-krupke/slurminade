# slurminade

*slurminade* makes using the workload manager [slurm](https://slurm.schedmd.com/documentation.html) with Python beautiful.
It is based on [simple_slurm](https://github.com/amq92/simple_slurm), but instead of just allowing to comfortably execute shell commands in slurm, it allows to directly distribute Python-functions.
A function decorated with `@slurminade.slurmify(partition="alg")` will automatically be executed by a node of the partition `alg` by just calling `.distribute(yes_also_args_are_allowed)`.
The general idea is that the corresponding Python-code exists on both machines, thus, the slurm-node can also call the functions of the original code if you tell if which one and what arguments to use.
This is similar to [celery](https://github.com/celery/celery) but you do not need to install anything, just make sure the same Python-environment is available the nodes (usually the case in a proper slurm setup).

Please check the documentation of [simple_slurm](https://github.com/amq92/simple_slurm) to get to know more about the
possible parameters. You can also call simple_slurm directly by `srun` and `sbatch` (automatically with the 
configuration specified with slurminade).

*slurminade* has two design goals:
1. Pythonic slurm: Allowing to use slurm in a Pythonic-way, without any shell commands etc.
2. Compatibility: Scripts can also run without slurm. You can share a script and also people without slurm can execute it without any changes.

A simple script could look like this:
```python
import slurminade

slurminade.update_default_configuration(partition="alg")  # global options for slurm

# If no slurm environment is found, the functions are called directly to make scripts
# compatible with any environment.
# You can enforce slurm with `slurminade.set_dispatcher(slurminade.SlurmDispatcher())`

# use this decorator to make a function distributable with slurm
@slurminade.slurmify(constraint="alggen02")  # function specific options can be specified
def prepare():
    print("Prepare")

@slurminade.slurmify()
def f(foobar):
    print(f"f({foobar})")

@slurminade.slurmify()
def clean_up():
    print("Clean up")


if __name__ == "__main__":
    jid = prepare.distribute()

    with slurminade.Batch(max_size=20) as batch:  # automatically bundles up to 20 tasks
        # run 100x f after `prepare` has finished
        for i in range(100):
            f.wait_for(jid).distribute(i)  # no job id while in batch!

        # clean up after the previous jobs have finished
        jids = batch.flush()  # flush returns a list with all job ids.
        clean_up.wait_for(jids).distribute()
```

> :warning: Always use `Batch` when distributing many tasks. Otherwise, you DDoS your slurm.

We recommend to use *slurminade* with [conda](https://docs.conda.io/en/latest/).
We have not tested it with other virtual environments.

The code is super simple and open source, don't be afraid to create a fork that fits your own needs.

If slurm is not available, `distribute` results in a local function call.
Analogous for `srun` and `sbatch` (giving some extra value on top of just forwarding to
*simple_slurm*).

> :warning: Talk with you system administrator or supervisor to get the proper slurm configuration.

## Installation

You can install *slurminade* with `pip install slurminade`.

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

You can set up a default configuration in `~/.slurminade_default.json`.
This should simply be a dictionary of arguments for *simple_slurm*.
For example
```json
{
  "partition": "alg"
}
```

## Debugging

You can use
```python
import slurminade

slurminade.set_dispatcher(slurminade.TestDispatcher())
```
to see the serialization or
```python
import slurminade
slurminade.set_dispatcher(slurminade.SubprocessDispatcher())
```
to distribute the tasks without slurm using subprocesses.

If there is a bug, you will directly see it in the output (at least for most bugs).


## Project structure

The project is reasonably easy:

- batch.py: Contains code for bundling tasks, so we don't spam slurm with too many.
- conf.py: Contains code for managing the configuration of slurm.
- dispatcher.py: Contains code for actually dispatching tasks to slurm.
- execute.py: Contains code to execute the task on the slurm node.
- function.py: Contains the code for making a function slurm-compatible.
- function_map.py: Saves all the slurmified functions.
- guard.py: Contains code to prevent you accidentally DDoSing your infrastructure.
- options.py: Contains a simple data structure to save slurm options.

## Changes

* 0.5.5: Fixing bug guard bug in subprocess dispatcher.
* 0.5.4: Dispatched function calls that are too long for the command line now use a temporary file instead.
* 0.5.3: Fixed a bug that caused the dispatch limit to have no effect.
* 0.5.2: Added pyproject.toml for PEP compliance
* 0.5.1: `Batch` will now flush on delete, in case you forgot.
* 0.5.0:
  * Functions now have a `wait_for`-option and return job ids. 
  * Braking changes: Batches have a new API.
    * `add` is no longer needed.
    * `AutoBatch` is now called `Batch`.
  * Fundamental code changes under the hood.
* <0.5.0:
  * Lots of experiments on finding the right interface.