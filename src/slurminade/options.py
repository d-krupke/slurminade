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

    def as_dict(self) -> typing.Dict:
        return dict(self._items())

    def add_dependencies(self, job_ids, method: str = "afterany"):
        opt = f"{method}:" + ":".join(str(jid) for jid in job_ids)
        if "dependency" in self:
            # There are already dependencies. Trying to extend them.
            if isinstance(self["dependency"], dict):
                dependecy_dict = self["dependency"]
                if method in dependecy_dict:
                    dependecy_dict[method] += ":" + ":".join(
                        str(jid) for jid in job_ids
                    )
                else:
                    dependecy_dict[method] = ":".join(str(jid) for jid in job_ids)
            elif isinstance(self["dependency"], str):
                self["dependency"] += "," + opt
            else:
                # Could not extend dependencies because I have no idea what is going on.
                msg = "Key 'dependency' has unexpected type."
                raise RuntimeError(msg)
        else:
            self["dependency"] = opt
