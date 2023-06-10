import unittest

import slurminade
from slurminade.guard import TooManyDispatchesError, _DispatchGuard, set_dispatch_limit


@slurminade.slurmify()
def f():
    pass


class TestDispatchGuard(unittest.TestCase):
    def test_simple(self):
        slurminade.set_entry_point(__file__)
        dg = _DispatchGuard(3)
        dg()
        dg()
        dg()
        self.assertRaises(TooManyDispatchesError, dg)

    def test_dispatch_limit(self):
        slurminade.set_entry_point(__file__)
        set_dispatch_limit(3)
        f.distribute()
        f.distribute()
        f.distribute()
        self.assertRaises(TooManyDispatchesError, f.distribute)

    def test_dispatch_limit_batch(self):
        slurminade.set_entry_point(__file__)
        set_dispatch_limit(2)
        with slurminade.Batch(max_size=2):
            for _ in range(4):
                f.distribute()
        self.assertRaises(TooManyDispatchesError, f.distribute)
