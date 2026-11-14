# Live accuracy of the item value estimates (D85)

Generated monthly by the ml-nft-refresh sidecar (`ml.nft.fv_jobs`, `python -m ml.nft.live_accuracy`). Monitoring
only: nothing here changes serving.

Since the 10.9b fixes the sidecar writes the summaries to the ml-data volume
(`/data/nft/live_accuracy/summaries/YYYY-MM.json` and `.md`), never into the repository. The files in this folder are
hand-committed copies; do not edit them. To copy a new month (PowerShell, repo root):

    docker cp altinvest-ml-nft-refresh:/data/nft/live_accuracy/summaries/2026-11.json ml/docs/phase10/live_accuracy/
    docker cp altinvest-ml-nft-refresh:/data/nft/live_accuracy/summaries/2026-11.md ml/docs/phase10/live_accuracy/

- Every day after the NFT refresh the sidecar logs the served estimate of every token with traits (the same code as
  the API) and the floor point it used (B0), in the ml-data volume (`/data/nft/live_accuracy/estimates/`).
- A month is summarised once its last sale is 30 days old (W2 looks 30 days ahead): normally on the 1st of the month
  after next. Each clean sale is matched to the latest estimate of its token logged before it (at most 48 h earlier).
- Summary: MdAPE of the served estimate vs B0 (the floor), pooled, by collection and by rarity decile. A collection
  behind B0 in two consecutive summarised months is marked ALERT; the owner decides what to do.

The first logged day is the day the 10.9 deployment started the sidecar (2026-11-14), so the first summary
(November 2026, partial month) is due on 2027-01-01.
