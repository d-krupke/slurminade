import pytest

import slurminade


def test_dispatch_limit_batch():
    @slurminade.slurmify()
    def f():
        pass

    slurminade.set_entry_point(__file__)

    with pytest.raises(KeyError):
        f.distribute()
