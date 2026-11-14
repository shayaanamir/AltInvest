# Fair-value refit log (D83), hand-committed copy

The served fair-value refits, the pointer `CURRENT` and `refit_log.jsonl` live on the ml-data volume
(`/data/nft/fv_refits/`), written only by the containers (10.9b SHOULD FIX 1). Nothing in the repository decides or
redirects a refit. This folder is a copy for the record: `refit_log.jsonl` and each refit's `metadata.json`
(`model.txt` is not copied; its sha256 is in the metadata). Do not edit the copies.

To update the copy after a refit (PowerShell, repo root; `<label>` is the new folder name in the log):

    docker cp altinvest-ml-nft-refresh:/data/nft/fv_refits/refit_log.jsonl ml/docs/phase10/refits/refit_log.jsonl
    docker cp altinvest-ml-nft-refresh:/data/nft/fv_refits/refits/<label>/metadata.json ml/docs/phase10/refits/<label>/

Then commit the copies with a `docs(ml):` commit.
