import slurminade

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

    with slurminade.Batch(20) as batch:
        # run 10x f after prepare has finished
        for i in range(10):
            f.wait_for(jid).distribute(i)

        # clean up after the previous jobs have finished
        jids = batch.flush()
        clean_up.wait_for(jids).distribute()