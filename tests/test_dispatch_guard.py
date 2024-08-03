import pytest

import slurminade
from slurminade.guard import TooManyDispatchesError, _DispatchGuard, set_dispatch_limit


@slurminade.slurmify()
def f():
    pass


def test_dispatch_guard_simple():
    slurminade.set_entry_point(__file__)
    dg = _DispatchGuard(3)
    dg()
    dg()
    dg()
    with pytest.raises(TooManyDispatchesError):
        dg()


def test_dispatch_guard_dispatch_limit():
    slurminade.set_entry_point(__file__)
    set_dispatch_limit(3)
    f.distribute()
    f.distribute()
    f.distribute()
    with pytest.raises(TooManyDispatchesError):
        f.distribute()


def test_dispatch_guard_dispatch_limit_batch():
    slurminade.set_entry_point(__file__)
    set_dispatch_limit(2)
    with slurminade.JobBundling(max_size=2):
        for _ in range(4):
            f.distribute()
    with pytest.raises(TooManyDispatchesError):
        f.distribute()
