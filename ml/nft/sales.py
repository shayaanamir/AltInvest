"""Sale events and the wash-trade filter (D56, D57). Pure functions, no I/O.

parse_event turns one OpenSea sale event into a row, or says why it is dropped. wash_filter marks each sale
with the first rule that removes it:
  R1 buyer == seller
  R2 round trip: a sale A->B of token t with a sale B->A of the same token within 30 days before or after
     (both legs are marked). This looks ahead: a cleaning rule on stored data, never a feature (D57).
  R3 price below 0.10x or above 20x the collection floor of the sale's UTC date (floor_eth_model, D66; as of
     00:00 UTC, so nothing from later that day is used).
"""

import numpy as np
import pandas as pd

from ml import config

SALE_COLUMNS = ["slug", "token_id", "timestamp", "date", "price_eth", "payment_symbol", "buyer", "seller", "tx",
                "protocol_address", "marketplace"]
KEY = ["slug", "tx", "token_id", "seller", "buyer"]
RULES = ("R1", "R2", "R3")


def marketplace(protocol_address: str, symbol: str) -> str:
    """D56: the API has no marketplace field. Seaport contract -> opensea; BETH (Blur pool) -> blur."""
    if protocol_address and protocol_address.lower() in config.NFT_SEAPORT_ADDRESSES:
        return "opensea"
    return "blur" if symbol == "BETH" else "unknown"


def parse_event(event: dict, slug: str) -> tuple[dict | None, str | None]:
    """(row, None) for a usable sale, (None, reason) for a dropped one."""
    pay, nft = event.get("payment") or {}, event.get("nft") or {}
    symbol = pay.get("symbol") or ""
    if event.get("event_type") != "sale" or not nft.get("identifier") or not event.get("event_timestamp"):
        return None, "malformed"
    if symbol not in config.NFT_PAYMENT_SYMBOLS:
        return None, "payment_token"
    if int(event.get("quantity") or 0) != 1:
        return None, "quantity_not_1"
    price = int(pay.get("quantity") or 0) / 10 ** int(pay.get("decimals") or 18)
    if not price > 0:
        return None, "zero_price"
    ts = int(event["event_timestamp"])
    protocol = (event.get("protocol_address") or "").lower()
    return {"slug": slug, "token_id": str(nft["identifier"]), "timestamp": ts,
            "date": pd.Timestamp(ts, unit="s", tz="UTC").strftime("%Y-%m-%d"), "price_eth": price,
            "payment_symbol": symbol, "buyer": (event.get("buyer") or "").lower(),
            "seller": (event.get("seller") or "").lower(), "tx": (event.get("transaction") or "").lower(),
            "protocol_address": protocol, "marketplace": marketplace(protocol, symbol)}, None


def dedupe(sales: pd.DataFrame) -> pd.DataFrame:
    """One row per (slug, tx, token, seller, buyer), ordered by collection and time."""
    return (sales.drop_duplicates(KEY).sort_values(["slug", "timestamp", "tx", "token_id"])
            .reset_index(drop=True))


def round_trips(sales: pd.DataFrame) -> np.ndarray:
    """True for a sale A->B of token t that has a sale B->A of the same token within the window (R2)."""
    s = sales.reset_index(drop=True)
    s["_i"] = np.arange(len(s))
    back = s[["slug", "token_id", "buyer", "seller", "timestamp"]].rename(
        columns={"buyer": "seller", "seller": "buyer", "timestamp": "t_back"})
    pairs = s[["_i", "slug", "token_id", "seller", "buyer", "timestamp"]].merge(
        back, on=["slug", "token_id", "seller", "buyer"])
    near = (pairs["timestamp"] - pairs["t_back"]).abs() <= config.NFT_WASH_ROUNDTRIP_DAYS * 86400
    out = np.zeros(len(s), dtype=bool)
    out[pairs.loc[near, "_i"].unique()] = True
    return out


def wash_filter(sales: pd.DataFrame, floor: pd.DataFrame) -> pd.DataFrame:
    """`sales` plus floor_eth_model (the floor of the sale's date) and wash_rule ('' = kept, else R1/R2/R3).

    `floor`: slug, date, floor_eth_model. A sale whose date has no floor row raises: every sale needs a floor.
    """
    s = sales.merge(floor[["slug", "date", "floor_eth_model"]], on=["slug", "date"], how="left")
    if s["floor_eth_model"].isna().any():
        bad = s[s["floor_eth_model"].isna()]
        raise ValueError(f"{len(bad)} sale(s) have no floor for their date, first {bad.iloc[0]['slug']} "
                         f"{bad.iloc[0]['date']}")
    lo, hi = config.NFT_WASH_PRICE_BOUNDS
    ratio = s["price_eth"] / s["floor_eth_model"]
    r1 = (s["buyer"] == s["seller"]).to_numpy()
    r2 = round_trips(s)
    r3 = ((ratio < lo) | (ratio > hi)).to_numpy()
    s["wash_rule"] = np.select([r1, r2, r3], list(RULES), "")
    return s


def removal_counts(marked: pd.DataFrame) -> dict:
    """Per collection: sales before, removed by each rule (first matching rule), and kept."""
    out = {}
    for slug, g in marked.groupby("slug", sort=True):
        rules = g["wash_rule"].value_counts()
        out[slug] = {"before": len(g), **{r: int(rules.get(r, 0)) for r in RULES},
                     "kept": int(rules.get("", 0))}
    return out
