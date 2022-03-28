import sys
from .function import SlurmFunction


def main():
    batchfile = sys.argv[1]
    funcid = sys.argv[2]
    args = sys.argv[3]
    with open(batchfile, "r") as f:
        code = "".join(f.readlines())
        exec(code)
    SlurmFunction.call(funcid, args)


if __name__ == "__main__":
    main()
