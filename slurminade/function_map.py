import inspect
import typing
import os


class FunctionMap:
    """
    The function map assigns functions an id and stores them to be called later.
    This id is reproducible such that the slurm node can retrieve the function
    it is supposed to call just by the id.
    """

    entry_point: typing.Optional[str] = None  # needed to save the entry point at the slurm node.
    _data = {}

    @staticmethod
    def get_id(func: typing.Callable) -> str:
        file = inspect.getfile(func)
        if file == "<string>":  # on the slurm node, the functions in the entry point
            # are named `<string>`.
            if not FunctionMap.entry_point:
                raise RuntimeError("No entry point known.")
            file = FunctionMap.entry_point
        path = os.path.normpath(os.path.abspath(file))
        return f"{path}:{func.__name__}"

    @staticmethod
    def check_compatibility(func: typing.Callable):
        """
        Throw if the function cannot be assigned an id.
        :param func: The function to be checked.
        :return: None
        """
        if (
                not func.__name__
                or func.__name__ == "<lambda>"
                or not inspect.getfile(func)
        ):
            raise ValueError("Can only slurmify proper functions.")

    @staticmethod
    def register(func: typing.Callable) -> str:
        """
        Register a function, allowing it to be called just by its id.
        :param func: The function to be stored. Needs to be a proper function.
        :return: The function's id.
        """
        FunctionMap.check_compatibility(func)
        func_id = FunctionMap.get_id(func)
        if func_id in FunctionMap._data:
            raise RuntimeError("Multiple function definitions!")
        FunctionMap._data[func_id] = func
        return func_id

    @staticmethod
    def call(func_id: str, args: typing.Iterable,
             kwargs: typing.Dict[str, typing.Any]) -> typing.Any:
        """
        Calls a function by its id.
        :param func_id: The id of the function to be called.
        :param args: The positional arguments.
        :param kwargs: The keyword arguments.
        :return: The return value of the function.
        """
        if func_id not in FunctionMap._data:
            raise KeyError(f"Function '{func_id}' unknown!")
        return FunctionMap._data[func_id](*args, **kwargs)
