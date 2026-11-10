"""Item traits and rarity (D60). Pure functions, no I/O.

A trait's share = tokens with that value / tokens in the collection; a token without a value in a category
counts as the value 'none'. rarity_score = sum over the collection's categories of -log(share);
rarity_rank 1 = rarest (highest score; ties share the smaller rank). Traits are static metadata, revealed
before the sales window starts, so they are known before every sale.
"""

import numpy as np
import pandas as pd

NONE = "none"
TRAIT_COLUMNS = ["slug", "token_id", "trait_type", "value"]
TOKEN_COLUMNS = ["slug", "token_id", "name", "image_url", "n_traits"]


def parse_token(nft: dict, slug: str) -> tuple[dict, list[dict]]:
    """(token row, trait rows) from one Alchemy getNFTsForContract item. The metadata's trait list is under
    'attributes' (ERC-721 metadata) or 'traits' (OpenSea-style metadata)."""
    meta = (nft.get("raw") or {}).get("metadata") or {}
    raw = meta.get("attributes") or meta.get("traits") or []
    token_id = str(int(str(nft["tokenId"]), 0))
    seen, rows = set(), []
    for a in raw if isinstance(raw, list) else []:
        kind, value = (a or {}).get("trait_type"), (a or {}).get("value")
        if kind is None or value is None or str(kind) in seen:
            continue
        seen.add(str(kind))
        rows.append({"slug": slug, "token_id": token_id, "trait_type": str(kind).strip(),
                     "value": str(value).strip()})
    image = nft.get("image") or {}
    token = {"slug": slug, "token_id": token_id, "name": nft.get("name") or meta.get("name") or "",
             "image_url": image.get("cachedUrl") or image.get("originalUrl") or meta.get("image_url") or "",
             "n_traits": len(rows)}
    return token, rows


def trait_matrix(tokens: pd.DataFrame, traits: pd.DataFrame) -> pd.DataFrame:
    """One collection: rows = every token, columns = every category, cells = the value or 'none'."""
    wide = traits.pivot(index="token_id", columns="trait_type", values="value")
    return wide.reindex(tokens["token_id"]).fillna(NONE)


def shares(matrix: pd.DataFrame) -> pd.DataFrame:
    """Share of supply of each token's value, per category (same shape as `matrix`)."""
    return matrix.apply(lambda col: col.map(col.value_counts(normalize=True)))


def rarity(tokens: pd.DataFrame, traits: pd.DataFrame) -> pd.DataFrame:
    """One collection: token_id, rarity_score, rarity_rank, rarity_pct (rank / supply x 100)."""
    score = -np.log(shares(trait_matrix(tokens, traits))).sum(axis=1)
    rank = score.rank(ascending=False, method="min").astype(int)
    return pd.DataFrame({"token_id": score.index, "rarity_score": score.to_numpy(),
                         "rarity_rank": rank.to_numpy(), "rarity_pct": 100 * rank.to_numpy() / len(score)})


def rarity_all(tokens: pd.DataFrame, traits: pd.DataFrame) -> pd.DataFrame:
    """rarity() for every collection, with the slug."""
    parts = []
    for slug, tk in tokens.groupby("slug", sort=True):
        parts.append(rarity(tk, traits[traits["slug"] == slug]).assign(slug=slug))
    return pd.concat(parts, ignore_index=True)[["slug", "token_id", "rarity_score", "rarity_rank", "rarity_pct"]]
