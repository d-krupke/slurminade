import slurminade

slurminade.set_dispatch_limit(10)  # allow maximally 10 dispatches
slurminade.update_default_configuration(partition="alg", constraint="alggen02")
# slurminade.set_dispatcher(slurminade.SlurmDispatcher())  # enforce slurm


@slurminade.slurmify()
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
        # run 10x f after prepare has finished
        for i in range(100):
            f.wait_for(jid).distribute(i)

        # clean up after the previous jobs have finished
        jids = batch.flush()
        clean_up.wait_for(jids).distribute()
