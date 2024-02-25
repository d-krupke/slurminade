import typing


class FunctionCall:
    """
    A function call to be dispatched.
    """

    def __init__(self, func_id, args: typing.Tuple, kwargs: typing.Dict):
        self.func_id = func_id  # the function id, as in FunctionMap
        self.args = args  # the positional arguments for the call
        self.kwargs = kwargs  # the keyword arguments for the call

    def to_json(self) -> typing.Dict:
        """
        Convert call to a json object that can be passed to slurm.
        :return: json object.
        """
        return {"func_id": self.func_id, "args": self.args, "kwargs": self.kwargs}

    def __str__(self) -> str:
        """
        Return a printable string representation of the call, useful for logging.
        """

        def arg_to_str(arg):
            if isinstance(arg, str):
                return f"'{arg}'"
            return str(arg)

        short_args = ", ".join(arg_to_str(a) for a in self.args)
        if len(short_args) > 200:
            short_args = short_args[:200] + "..."
        short_kwargs = ", ".join(f"{k}={arg_to_str(v)}" for k, v in self.kwargs.items())
        if len(short_kwargs) > 200:
            short_kwargs = short_kwargs[:200] + "..."
        args = ", ".join(a for a in [short_args, short_kwargs] if a)
        return f"{self.func_id.split(':')[-1]}({args})"
