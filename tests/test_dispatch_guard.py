import unittest

from slurminade.guard import _DispatchGuard, TooManyDispatchesError


class TestDispatchGuard(unittest.TestCase):
    def test_simple(self):
        dg = _DispatchGuard(3)
        dg()
        dg()
        dg()
        self.assertRaises(TooManyDispatchesError, dg)
