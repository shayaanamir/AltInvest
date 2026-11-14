# Phase 10: NFT collections (floor, cone, liquidity, risk, item value)

## 1. Goal
Add 7 liquid Ethereum NFT collections to the app: a [floor price](../GLOSSARY.md) chart with the same 30-day volatility cone as crypto, a liquidity badge, a collection risk score, and an estimated value for a single item. As in Phase 9, every model had to beat a simple baseline in walk-forward and on a sealed test used once. "No model won" was an allowed result.

## 2. What we did
1. Chose collections and sources (OpenSea floor and sales, Alchemy and OpenSea metadata) and wrote the rules first (D53-D62).
2. Backfilled and froze the data (snapshot 2026-11-10, hashed; D62, D64), with a daily refresh sidecar.
3. Collection risk (10.3): EWMA was approved, then withdrawn after a sales check of the floor spike guard (D72, D73); persistence is served. Liquidity is a rule (D58).
4. Collection page with the cone and the liquidity badge (10.4).
5. Item data: wash-trade rules W1/W2 and price rules C1-C3 (D70, D74), item snapshot v3 (D75).
6. Fair value (10.6): 6 LightGBM configs against baselines B0/B1/B2, top-only selection (D76, D77).
7. Item card and API (10.7, D78), the sealed test once (10.8, D79), then in 10.9: monthly refits (D83), the tested error line (D84), the live accuracy log (D85) and the D49 audit (D81, D82).

## 3. Files
- `ml/nft/`: collectors, snapshots, cleaning, features (`fv_features.py`), request-time serving (`fv_serving.py`), refits (`fv_refit.py`), sidecar jobs (`fv_jobs.py`), live accuracy (`live_accuracy.py`).
- `ml/models/nft_fair_value.py`: the 6 declared candidates and the baselines.
- `ml/evaluation/run_nft_risk.py`, `run_nft_fair_value.py`, `run_nft_sealed_fv.py`, `nft_fv_protocol.py`: evaluations; reports in `ml/reports/nft/`.
- `ml/serving/nft_responses.py`, `nft_items.py`; schemas in `ml/docs/CONTRACT_NFT.md`.
- Backend `controllers/nft_*.py`, `routes/nft.py`; frontend `pages/NftCollectionPage.jsx`, `components/nft/`.

## 4. How it works
The item model predicts the premium y = log(price / floor just before the sale). Example (made-up numbers): floor 2.0 ETH, predicted premium 0.05, so the estimate is 2.0 x e^0.05 = 2.10 ETH. Features use only sales and floor points from before the moment they describe; this was tested on 2,000 sales.

## 5. Results
| Part | Result (source) | Served |
|---|---|---|
| Collection risk | EWMA approved in 10.3, withdrawn by the D72 check; under top-only GARCH ranks first, CI includes 0 (`walkforward_risk.json`) | Persistence vol_30d (D73) |
| Item value, walk-forward | fv_pooled_l1_nl15 MdAPE 0.0284 vs B2 0.0335, gain 0.0051 [0.0015, 0.0079]; 80% range not approved (coverage 0.73) (`walkforward_fair_value.json`) | Yes, no range |
| Item value, sealed test (Feb-Nov 2026) | served 0.0294 vs B0 0.0353, gain 0.0059 [0.0034, 0.0085], PASS (`sealed_fair_value.json`) | Yes: model for 6 collections, B2 for lilpudgys (D80) |

MdAPE 0.0294 means half of the sales were within about 2.9% of the estimate. For the rarest 10% of items it was about 9%.

## 6. Decisions
D53-D62 (rules, user review), D63-D68 (data details, autonomous), D69-D75 (data and test rules, user review), D76-D79 (fair value, test), D80-D85 (10.9: lilpudgys keeps B2, top-only, D49 audit, refits, error line, live log).

## 7. Limits
- The confirmation and sealed sets are short (about 40 seven-day blocks in the sealed test), and the collections move together.
- There is no range, no drivers and no comparable sales. lilpudgys uses B2, although on the sealed data the model would have done better there (D80).
- Live data has gaps. Binance is unreachable from Docker on this machine, and new multi-token sales after the snapshot have no payment record (checkpoint_10.7 open items).

## 8. Verify and next
- Verify: "How to verify Phase 10 yourself" in ml/docs/STATUS.md.
- Next: the owner reviews the autonomous decisions (checkpoint_10.9.md) and merges. NFT risk is re-evaluated on 2027-05-10; the first live accuracy summary is due on 2027-01-01.
