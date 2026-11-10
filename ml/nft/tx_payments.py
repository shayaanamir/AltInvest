"""What each multi-token sale transaction actually paid (D74), read once from the Alchemy Ethereum RPC.

    python -m ml.nft.tx_payments        (resumable; writes ML_NFT_DIR/tx_payments.csv)

For every transaction that has a multi-token group (one tx, one seller, one buyer, >= 2 tokens of one collection)
in the base snapshot: the ETH value of the transaction and the sum of WETH and BETH ERC-20 Transfer amounts in
its receipt. The ALCHEMY_API_KEY is part of the RPC URL, so URLs and requests are never printed or logged.
"""

import time

import pandas as pd
import requests

from ml import config
from ml.nft import item_clean as ic, snapshot, store
from ml.nft.opensea import env_value

OUT = "tx_payments.csv"
COLUMNS = ["tx", "ok", "value_eth", "weth", "beth"]
BATCH = 10                                          # transactions per JSON-RPC batch (2 calls each)
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
TOKENS = {"0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "weth", "0x0000000000a39bb272e79075ade125fd351887ac": "beth"}


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
    if not key:
        raise SystemExit("ALCHEMY_API_KEY is not set (environment or .env)")
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


def main() -> None:
    snapshot.require_snapshot("sales_raw")
    path = config.ML_NFT_DIR / OUT
    have = store.read_csv(path) if path.exists() else pd.DataFrame(columns=COLUMNS)
    todo = [t for t in multi_token_txs(snapshot.load("sales_raw")) if t not in set(have["tx"])]
    print(f"[tx-payments] {len(todo)} transactions to read ({len(have)} stored)", flush=True)
    for i in range(0, len(todo), 200):                         # write every 200: resumable
        rows = fetch(todo[i:i + 200])
        if not rows:
            continue
        have = pd.concat([have, pd.DataFrame(rows, columns=COLUMNS)], ignore_index=True) if len(have) else pd.DataFrame(rows, columns=COLUMNS)
        store.write_csv(have, path)
        print(f"[tx-payments] {len(have)} stored, {int((~have['ok'].astype(bool)).sum())} not returned", flush=True)


if __name__ == "__main__":
    main()
