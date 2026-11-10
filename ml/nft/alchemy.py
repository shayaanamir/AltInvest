"""Alchemy NFT API v3 client for item traits (D54): getNFTsForContract with metadata, 100 tokens per page.

The key comes from ALCHEMY_API_KEY (environment or the repo's .env). It is part of the URL path, so URLs are
never printed or logged.
"""

import time
from collections.abc import Iterator

import requests

from ml.nft.opensea import env_value

MAX_ATTEMPTS = 6


class AlchemyError(RuntimeError):
    pass


def contract_nfts(contract: str, key: str | None = None, session: requests.Session | None = None,
                  sleep=time.sleep, start_key: str | None = None) -> Iterator[tuple[list[dict], str | None]]:
    """Yields (tokens of one page, the next pageKey or None)."""
    key = key or env_value("ALCHEMY_API_KEY")
    if not key:
        raise AlchemyError("ALCHEMY_API_KEY is not set (environment or .env)")
    session = session or requests.Session()
    url = f"https://eth-mainnet.g.alchemy.com/nft/v3/{key}/getNFTsForContract"
    page_key = start_key
    while True:
        params = {"contractAddress": contract, "withMetadata": "true", "limit": 100}
        if page_key:
            params["pageKey"] = page_key
        status = "network error"
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                r = session.get(url, params=params, timeout=60, headers={"accept": "application/json"})
                status = f"HTTP {r.status_code}"
            except requests.RequestException:
                r = None
            if r is not None and r.status_code == 200:
                break
            if attempt == MAX_ATTEMPTS:
                raise AlchemyError(f"getNFTsForContract failed for {contract}: {status}")
            sleep(2 ** attempt)
        body = r.json()
        page_key = body.get("pageKey")
        yield body.get("nfts") or [], page_key
        if not page_key:
            return
