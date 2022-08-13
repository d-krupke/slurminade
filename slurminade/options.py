import typing


class SlurmOptions(dict):
    """
    Primarily just a wrapper to allow using the options in a dict as key.
    Necessary for batching function calls, because only function calls with the
    same options can be bundled.
    """

    def _items(self):
        for k, v in self.items():
            if isinstance(v, dict):
                v = SlurmOptions(**v)
            yield k, v

    def __hash__(self):
        return hash(tuple(sorted(hash((k, v)) for k, v in self._items())))

    def __eq__(self, other):
        if not isinstance(other, SlurmOptions):
            return False
        return hash(self) == hash(other)
