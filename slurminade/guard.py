__exec_flag = False

def guard_recursive_distribution():
    if __exec_flag:
        raise RuntimeError("Cannot distribute a task within a distributed task! "
                           "(maybe you forgot to guard you script with "
                           "'if __name__==\"__main__\":'?)")

def prevent_distribution():
    __exec_flag = True