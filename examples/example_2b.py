import slurminade


@slurminade.slurmify()
def f(text):
    print("Hello from imported function:", text)
    print("This function 'f' is in", __file__)
