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


def _sale(token, tx, seller="s", buyer="b", price=1.0, t=0):
    ts = 1_763_000_000 + t
    return {"slug": "azuki", "token_id": token, "timestamp": ts, "date": "2026-11-13", "price_eth": price,
            "payment_symbol": "ETH", "buyer": buyer, "seller": seller, "tx": tx, "protocol_address": "",
            "marketplace": "unknown"}


def _live(tmp_path):
    import pandas as pd

    from ml.nft import store, tx_payments as txp
    sales = pd.DataFrame([_sale("1", "0xold"), _sale("2", "0xold"),                  # multi-token, stored
                          _sale("3", "0xnew"), _sale("4", "0xnew"), _sale("4", "0xnew"),   # multi-token, new
                          _sale("5", "0xsingle")])                                      # one token: never read
    store.write_csv(sales, tmp_path / "sales_raw.csv")
    store.write_csv(pd.DataFrame([{"tx": "0xold", "ok": True, "value_eth": 2.0, "weth": 0.0, "beth": 0.0}]),
                    tmp_path / txp.OUT)
    return txp


def test_daily_stage_reads_only_new_multi_token_transactions(tmp_path):
    """10.9b SHOULD FIX 2: the D74 record of each new multi-token transaction is read once and appended."""
    txp = _live(tmp_path)
    asked = []

    def fetch(txs):
        asked.append(list(txs))
        return [{"tx": t, "ok": True, "value_eth": 2.0, "weth": 0.0, "beth": 0.0} for t in txs]

    out = txp.update(tmp_path, fetch_fn=fetch)
    assert asked == [["0xnew"]] and out == {"new_transactions": 1, "read": 1, "stored": 2, "not_returned": 0}
    assert txp.update(tmp_path, fetch_fn=fetch)["new_transactions"] == 0 and len(asked) == 1     # read once
    stored = txp.store.read_csv(tmp_path / txp.OUT)
    assert list(stored["tx"]) == ["0xold", "0xnew"]


def test_daily_stage_never_shows_the_rpc_url(tmp_path):
    txp = _live(tmp_path)
    url = "https://eth-mainnet.g.alchemy.com/v2/SECRETKEY"

    def fetch(txs):
        raise ValueError(f"connection to {url} failed")

    with pytest.raises(RuntimeError) as e:
        txp.update(tmp_path, fetch_fn=fetch)
    assert "SECRETKEY" not in str(e.value) and "alchemy" not in str(e.value)


def test_refresh_runs_the_tx_payments_stage_after_the_sales(tmp_path, monkeypatch):
    txp = _live(tmp_path)
    monkeypatch.setattr(refresh.config, "ML_NFT_DIR", tmp_path)
    monkeypatch.setattr(refresh, "Client", lambda: (_ for _ in ()).throw(RuntimeError("no key")))
    monkeypatch.setattr(refresh.collect, "collect_eth", lambda: {"bars_written": 0})
    monkeypatch.setattr(txp, "update", lambda: {"new_transactions": 0})
    status = refresh.run_once()
    assert status["stages"]["tx_payments"] == {"status": "ok", "result": {"new_transactions": 0}}
