"""The NFT refresh sidecar (ml.nft.refresh): each daily cycle runs in a child process (10.9b: no job holds memory
between runs)."""

import sys

import pytest

from ml.nft import refresh


class _Stop(Exception):
    pass


def test_loop_runs_each_cycle_in_a_child_process():
    calls = []

    def run(cmd):
        calls.append(cmd)
        raise _Stop

    with pytest.raises(_Stop):
        refresh.loop(run=run)
    assert calls == [[sys.executable, "-m", "ml.nft.refresh", "--cycle"]]
