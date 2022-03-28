import sys

from slurminade.guard import prevent_distribution
from .function import SlurmFunction



def main():
    prevent_distribution()
    batchfile = sys.argv[1]
    funcid = sys.argv[2]
    args = sys.argv[3]
    with open(batchfile, "r") as f:
        code = "".join(f.readlines())
        exec(code)
    SlurmFunction.call(funcid, args)


if __name__ == "__main__":
    main()
