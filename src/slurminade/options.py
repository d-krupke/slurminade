"""Options for Slurm jobs."""

import typing
from collections.abc import Iterator


class SlurmOptions:
    """
    A hashable wrapper for Slurm options.

    Necessary for batching function calls, because only function calls with the
    same options can be bundled. Uses composition instead of inheritance for
    better type safety.
    """

    def __init__(self, **kwargs: typing.Any) -> None:
        """Initialize SlurmOptions with keyword arguments."""
        self._data: dict[str, typing.Any] = dict(kwargs)

    def _items(self) -> Iterator[tuple[str, typing.Any]]:
        """Iterate over items, converting nested dicts to SlurmOptions."""
        for k, v in self._data.items():
            if isinstance(v, dict):
                yield k, SlurmOptions(**v)
            else:
                yield k, v

    def __hash__(self) -> int:
        """
        Compute hash for this options object.

        Note: This will raise TypeError if any values are unhashable
        (e.g., lists). This is intentional to catch bugs early.
        """
        try:
            return hash(tuple(sorted(hash((k, v)) for k, v in self._items())))
        except TypeError as e:
            msg = (
                f"Cannot hash SlurmOptions with unhashable values. "
                f"All values must be hashable (strings, numbers, tuples, etc.), "
                f"not lists or dicts. Error: {e}"
            )
            raise TypeError(msg) from e

    def __eq__(self, other: object) -> bool:
        """Check equality based on data contents."""
        if not isinstance(other, SlurmOptions):
            return False
        return self._data == other._data

    def __repr__(self) -> str:
        """Return a string representation."""
        return f"SlurmOptions({self._data!r})"

    def as_dict(self) -> dict[str, typing.Any]:
        """Convert to a regular dictionary."""
        return dict(self._items())

    def add_dependencies(
        self, job_ids: typing.Iterable[typing.Union[str, int]], method: str = "afterany"
    ) -> None:
        """
        Add job dependencies to these options.

        Args:
            job_ids: Job IDs to depend on
            method: Dependency method (afterany, afterok, etc.)
        """
        opt = f"{method}:" + ":".join(str(jid) for jid in job_ids)

        if "dependency" in self._data:
            # There are already dependencies. Trying to extend them.
            if isinstance(self._data["dependency"], dict):
                dependency_dict = self._data["dependency"]
                if method in dependency_dict:
                    dependency_dict[method] += ":" + ":".join(
                        str(jid) for jid in job_ids
                    )
                else:
                    dependency_dict[method] = ":".join(str(jid) for jid in job_ids)
            elif isinstance(self._data["dependency"], str):
                self._data["dependency"] += "," + opt
            else:
                # Could not extend dependencies because I have no idea what is going on.
                msg = "Key 'dependency' has unexpected type."
                raise RuntimeError(msg)
        else:
            self._data["dependency"] = opt

    # Dict-like interface for backwards compatibility
    def __getitem__(self, key: str) -> typing.Any:
        """Get an item like a dict."""
        return self._data[key]

    def __setitem__(self, key: str, value: typing.Any) -> None:
        """Set an item like a dict."""
        self._data[key] = value

    def __contains__(self, key: object) -> bool:
        """Check if key exists like a dict."""
        return key in self._data

    def get(self, key: str, default: typing.Any = None) -> typing.Any:
        """Get an item with a default value like a dict."""
        return self._data.get(key, default)

    def items(self) -> typing.ItemsView[str, typing.Any]:
        """Get items view like a dict."""
        return self._data.items()

    def keys(self) -> typing.KeysView[str]:
        """Get keys view like a dict."""
        return self._data.keys()

    def values(self) -> typing.ValuesView[typing.Any]:
        """Get values view like a dict."""
        return self._data.values()

    def update(self, other: dict[str, typing.Any]) -> None:
        """Update from another dict."""
        self._data.update(other)

    def copy(self) -> "SlurmOptions":
        """Create a shallow copy."""
        return SlurmOptions(**self._data.copy())
