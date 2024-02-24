
import slurminade
from pytest import raises

def test_dispatch_limit_batch():
    @slurminade.slurmify()
    def f():
        pass

    slurminade.set_entry_point(__file__)

    with raises(KeyError):
        f.distribute()
