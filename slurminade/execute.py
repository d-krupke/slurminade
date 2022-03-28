import sys
from .function import SlurmFunction


__exec_flag = False

def guard_recursive_distribution():
    if __exec_flag:
        raise RuntimeError("Cannot distribute a task within a distributed task! "
                           "(maybe you forgot to guard you script with "
                           "'if __name__==\"__main__\":'?)")

def main():
    __exec_flag = True
    batchfile = sys.argv[1]
    funcid = sys.argv[2]
    args = sys.argv[3]
    with open(batchfile, "r") as f:
        code = "".join(f.readlines())
        exec(code)
    SlurmFunction.call(funcid, args)


if __name__ == "__main__":
    main()
