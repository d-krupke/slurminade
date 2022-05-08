import slurminade


@slurminade.slurmify()
def f(text):
    print("Hello from imported function:", text)
