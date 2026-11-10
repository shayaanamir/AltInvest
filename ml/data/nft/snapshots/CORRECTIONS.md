# Corrections to the frozen NFT snapshots

The snapshot directories and their `manifest.json` files are never rewritten (D62). Corrections to what a manifest says are recorded here instead. This file is not part of any snapshot's hashes.

## 2026-11-10: `git_dirty: true` is a false positive (recorded 2026-11-11, step 10.5b)

`2026-11-10/manifest.json` records `git_commit 262dfe977ef5e85e4aa4908b62c58effe6da81c4` and `git_dirty: true`.

The tree was clean apart from the snapshot's own new files. `ml.nft.snapshot.freeze` read the git state *after* writing the parquet files, so git counted those as untracked changes:
- The code that built the snapshot is exactly commit 262dfe9.
- The order was fixed in b9a56e6: the git state is now read before any file is written.
- Both later snapshots record `git_dirty: false`.

| Snapshot | Manifest records code at | Files committed in | Manifest `git_dirty` |
|---|---|---|---|
| 2026-11-10 | 262dfe977ef5e85e4aa4908b62c58effe6da81c4 | b9a56e67bed6ffd0be0ce97fcb48bbd0e495d15b | true (false positive, see above) |
| 2026-11-10-items | 9df9029d08859471f1955f5ec21285aa6fc327ff | 24dfefa94a82ae501b8d406d6276070690422611 | false |
| 2026-11-10-items-v2 | 5c4359cb39c29c77ee3634db2638b05779aa5608 | 5110e8d469ed356b789d0976c72ad21137243373 | false |

## 2026-11-10: `floor_eth_model` / `floor_spike` columns

These columns hold the D66 spike guard, which D73 withdrew. They stay in `floor.parquet` as recorded, but nothing served or newly evaluated uses them. `sales_filtered.parquet` was built with the guarded floor in rule R3. Fair value uses the v2 item snapshot (D70), which does not use the guard.
