"""Phase 10 step 10.5c: D74 multi-token rule from transaction payments, D75 currency and NOT_FEATURES.
Hand-made frames, no network."""

import pandas as pd

from ml.nft import item_clean as ic
from ml.nft import tx_payments as txp

T0 = int(pd.Timestamp("2025-03-01", tz="UTC").timestamp())
DAY = 86400


def _s(token, tx, seller, buyer, price, symbol="ETH", slug="c", t=1):
    ts = T0 + t * DAY
    return {"slug": slug, "token_id": token, "timestamp": ts,
            "date": pd.Timestamp(ts, unit="s", tz="UTC").strftime("%Y-%m-%d"), "price_eth": price,
            "payment_symbol": symbol, "buyer": buyer, "seller": seller, "tx": tx, "protocol_address": "",
            "marketplace": "unknown"}


def _pay(rows):
    return pd.DataFrame(rows, columns=["tx", "ok", "value_eth", "weth", "beth"])


SALES = pd.DataFrame([
    _s("1", "ta", "a", "b", 2.0), _s("2", "ta", "a", "b", 2.0),                       # sweep: tx paid 4.0 ETH
    _s("3", "tb", "a", "b", 5.0), _s("4", "tb", "a", "b", 5.0),                       # bundle: 5.0 repeated, tx paid 5
    _s("5", "tc", "x", "y", 1.0, "BETH"), _s("6", "tc", "x", "y", 1.0, "BETH"),       # Blur bid fills: BETH logs 2x
    _s("7", "td", "a", "b", 1.0), _s("8", "td", "a", "b", 1.0),                       # RPC did not return
    _s("9", "te", "a", "b", 3.0),                                                      # single token: never checked
    _s("10", "tf", "a", "b", 1.0, "WETH"), _s("11", "tf", "a", "b", 1.0, "WETH"),     # WETH with fees: 2.02 paid
])
PAY = _pay([("ta", True, 4.0, 0, 0), ("tb", True, 5.0, 0, 0), ("tc", True, 0, 0, 4.0), ("td", False, None, None, None),
            ("tf", True, 0, 2.02, 0)])


def test_multi_token_groups_are_kept_when_rows_add_up_to_what_the_transaction_paid():
    kept, counts = ic.classify_multi_token(SALES, SALES, PAY)
    assert sorted(kept["token_id"], key=int) == ["1", "2", "5", "6", "9", "10", "11"]
    assert counts == {"C2_attributable_groups": 3, "C2_attributable_rows": 6,
                      "C2_not_attributable_groups": 1, "C2_not_attributable_rows": 2,
                      "C2_rpc_missing_groups": 1, "C2_rpc_missing_rows": 2}


def test_rows_of_other_collections_in_the_same_transaction_count_toward_the_sum():
    other = pd.DataFrame([_s("90", "ta", "z", "b", 1.0, slug="other")])
    all_rows = pd.concat([SALES, other], ignore_index=True)
    kept, counts = ic.classify_multi_token(SALES, all_rows, PAY)       # 2 + 2 + 1 = 5 > 1.01 x 4.0
    assert "1" not in set(kept["token_id"]) and counts["C2_not_attributable_groups"] == 2
    pay = PAY.copy()
    pay.loc[pay["tx"] == "ta", "value_eth"] = 5.0                       # the tx paid for all three: attributable
    assert "1" in set(ic.classify_multi_token(SALES, all_rows, pay)[0]["token_id"])


def test_tolerance_is_one_percent():
    assert ic.ATTRIBUTION_TOLERANCE == 1.01
    pay = PAY.copy()
    pay.loc[pay["tx"] == "ta", "value_eth"] = 4.0 / 1.0101            # rows exceed the payment by just over 1%
    assert "1" not in set(ic.classify_multi_token(SALES, SALES, pay)[0]["token_id"])


def test_clean_with_payments_adds_payment_currency_and_reports_the_new_counts():
    points = pd.DataFrame({"slug": "c", "time": [T0 - DAY], "token_unit": [1.0]})
    rows, counts = ic.clean(SALES, points, PAY)
    assert set(rows["payment_currency"]) == {"ETH"} and "C2_bundle_rows_dropped" not in counts["c"]
    assert counts["c"]["C2_attributable_rows"] == 6
    old_rows, old_counts = ic.clean(SALES, points)                     # v2 path unchanged: the D70 C2
    assert "payment_currency" not in old_rows and old_counts["c"]["C2_bundle_rows_dropped"] == 10


def test_payment_currency_is_one_to_one_and_not_a_feature():
    assert ic.payment_currency(pd.Series(["ETH", "WETH", "BETH"])).tolist() == ["ETH", "ETH", "ETH"]
    for col in ("payment_currency", "marketplace", "sale_type", "payment_symbol"):
        assert col in ic.NOT_FEATURES


def test_rpc_parsing_sums_weth_and_beth_transfers_and_never_needs_the_url():
    log = lambda addr, wei: {"address": addr, "topics": [txp.TRANSFER, "0x1", "0x2"], "data": hex(wei)}
    receipt = {"logs": [log("0xC02aaa39b223FE8D0A0e5C4F27eAD9083C756Cc2", 10 ** 18),
                        log("0x0000000000a39bb272e79075ade125fd351887ac", 2 * 10 ** 18),
                        log("0x0000000000a39bb272e79075ade125fd351887ac", 2 * 10 ** 18),
                        {"address": "0xdead", "topics": [txp.TRANSFER, "0x1", "0x2"], "data": hex(10 ** 18)}]}
    assert txp.parse({"value": hex(3 * 10 ** 18)}, receipt) == {"ok": True, "value_eth": 3.0, "weth": 1.0, "beth": 4.0}
    assert txp.parse(None, receipt)["ok"] is False
    calls = []

    def post(body):
        calls.append(len(body))
        raise ValueError("not json")
    assert txp.fetch(["0xaa", "0xbb"], post=post, sleep=lambda s: None) == []    # failed batches are not stored
    assert calls == [4] * 5
