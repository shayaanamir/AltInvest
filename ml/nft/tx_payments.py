"""What each multi-token sale transaction actually paid (D74), read once from the Alchemy Ethereum RPC.

    python -m ml.nft.tx_payments        (resumable; writes ML_NFT_DIR/tx_payments.csv)
    python -m ml.nft.tx_payments --live (the daily refresh stage: new multi-token transactions in the live sales)

For every transaction that has a multi-token group (one tx, one seller, one buyer, >= 2 tokens of one collection)
in the base snapshot: the ETH value of the transaction and the sum of WETH and BETH ERC-20 Transfer amounts in
its receipt. The ALCHEMY_API_KEY is part of the RPC URL, so URLs and requests are never printed or logged.

Since 10.9b the daily NFT refresh also runs update(): every multi-token transaction in the live sales (deduplicated as
the serving history is) that has no stored record yet is read once, by the same rule (D74), and appended. Without it,
fv_serving drops every new multi-token group (D78(A)) and the monthly refit drifts from the D79 procedure.
"""

import time

import pandas as pd
import requests

from ml import config
from ml.nft import item_clean as ic, sales as sl, snapshot, store
from ml.nft.opensea import env_value

OUT = "tx_payments.csv"
COLUMNS = ["tx", "ok", "value_eth", "weth", "beth"]
BATCH = 10                                          # transactions per JSON-RPC batch (2 calls each)
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
CHUNK = 200                                         # transactions per stored write (resumable)
TOKENS = {"0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "weth", "0x0000000000a39bb272e79075ade125fd351887ac": "beth"}


class MissingKey(RuntimeError):
    pass


def multi_token_txs(sales: pd.DataFrame) -> list[str]:
    s, _ = ic.collapse_passthroughs(sales)
    n = s.groupby(["slug", "tx", "seller", "buyer"])["token_id"].transform("nunique")
    return sorted(s.loc[n >= 2, "tx"].unique())


def parse(tx: dict | None, receipt: dict | None) -> dict:
    if not tx or not receipt:
        return {"ok": False, "value_eth": None, "weth": None, "beth": None}
    sums = {"weth": 0.0, "beth": 0.0}
    for lg in receipt.get("logs", []):
        sym = TOKENS.get((lg.get("address") or "").lower())
        topics = lg.get("topics") or []
        if sym and len(topics) == 3 and topics[0] == TRANSFER:
            sums[sym] += int(lg["data"], 16) / 1e18
    return {"ok": True, "value_eth": int(tx.get("value", "0x0"), 16) / 1e18, **sums}


def _post(url: str, body: list) -> list:
    """One JSON-RPC batch; raises RuntimeError with the HTTP status only (never the URL) on any failure."""
    r = requests.post(url, json=body, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")
    out = r.json()
    if not isinstance(out, list):
        raise RuntimeError("batch answer is not a list")
    return out


def fetch(txs: list[str], post=None, sleep=time.sleep) -> list[dict]:
    """Rows for the transactions whose batch succeeded. A batch that keeps failing is left out (not stored), so
    the next run asks again; nothing is ever recorded as 'not returned' because of a rate limit."""
    key = env_value("ALCHEMY_API_KEY")
    if not key and post is None:
        raise MissingKey("ALCHEMY_API_KEY is not set (environment or .env)")
    url = f"https://eth-mainnet.g.alchemy.com/v2/{key}"
    post = post or (lambda body: _post(url, body))
    rows = []
    for i in range(0, len(txs), BATCH):
        part = txs[i:i + BATCH]
        body = []
        for j, tx in enumerate(part):
            body += [{"jsonrpc": "2.0", "id": 2 * j, "method": "eth_getTransactionByHash", "params": [tx]},
                     {"jsonrpc": "2.0", "id": 2 * j + 1, "method": "eth_getTransactionReceipt", "params": [tx]}]
        res = None
        for attempt in range(5):
            try:
                answer = post(body)
                if any("error" in x for x in answer):
                    raise RuntimeError("rate limited or error inside the batch")
                res = {x.get("id"): x.get("result") for x in answer}
                break
            except (requests.RequestException, ValueError, RuntimeError) as e:
                msg = str(e) if isinstance(e, RuntimeError) else type(e).__name__
                print(f"[tx-payments] batch {i // BATCH}: {msg}; retry {attempt + 1}", flush=True)
                sleep(5 * 2 ** attempt)
        if res is not None:
            rows += [{"tx": tx, **parse(res.get(2 * j), res.get(2 * j + 1))} for j, tx in enumerate(part)]
        sleep(0.5)
    return rows


def _store(sales: pd.DataFrame, path, fetch_fn) -> dict:
    """Read and append the records of the multi-token transactions in `sales` that have none yet."""
    have = store.read_csv(path) if path.exists() else pd.DataFrame(columns=COLUMNS)
    todo = [t for t in multi_token_txs(sales) if t not in set(have["tx"])]
    print(f"[tx-payments] {len(todo)} transactions to read ({len(have)} stored)", flush=True)
    read = 0
    for i in range(0, len(todo), CHUNK):
        rows = fetch_fn(todo[i:i + CHUNK])
        if not rows:
            continue
        read += len(rows)
        new = pd.DataFrame(rows, columns=COLUMNS)
        have = pd.concat([have, new], ignore_index=True) if len(have) else new
        store.write_csv(have, path)
    ok = have["ok"].astype(str).str.lower().isin(("true", "1"))
    print(f"[tx-payments] {len(have)} stored, {int((~ok).sum())} not returned", flush=True)
    return {"new_transactions": len(todo), "read": read, "stored": len(have), "not_returned": int((~ok).sum())}


def update(directory=None, fetch_fn=None) -> dict:
    """The daily refresh stage (10.9b): new multi-token transactions in the live sales, read once (D74). Any failure
    is re-raised with its type only, so no message can carry the RPC URL."""
    d = config.ML_NFT_DIR if directory is None else directory
    raw = sl.dedupe(store.read_table(d, "sales_raw"))[sl.SALE_COLUMNS]
    try:
        return _store(raw, d / OUT, fetch_fn or fetch)
    except MissingKey:
        raise
    except Exception as e:
        raise RuntimeError(f"tx payment read failed ({type(e).__name__})") from None


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Transaction payments of multi-token sales (D74)")
    parser.add_argument("--live", action="store_true", help="new multi-token transactions in the live sales")
    if parser.parse_args().live:
        print(update())
        return
    snapshot.require_snapshot("sales_raw")
    _store(snapshot.load("sales_raw"), config.ML_NFT_DIR / OUT, fetch)


if __name__ == "__main__":
    main()
