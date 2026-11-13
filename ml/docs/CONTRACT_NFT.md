# CONTRACT_NFT: ML NFT endpoints (Phase 10, D61, D67)

The ML service (:8001) validates every NFT response against these schemas before returning it, as it does for CONTRACT.md (AGENTS rule 14, `additionalProperties: false`). The backend pulls them daily at 00:15 UTC (D61).
- Errors: an unknown slug gives 404. Missing NFT data gives 503.
- Covered slugs: `ml/config.py` NFT_SLUGS.

## GET /nft/collections -> NftCollectionsResponse

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "NftCollectionsResponse",
  "type": "object",
  "required": ["collections", "marketplaces_counted", "timestamp"],
  "properties": {
    "collections": {"type": "array", "items": {
      "type": "object",
      "required": ["slug", "name", "last_floor_date", "floor_eth", "floor_usd"],
      "properties": {
        "slug": {"type": "string"},
        "name": {"type": "string"},
        "symbol": {"type": ["string", "null"]},
        "contract": {"type": ["string", "null"]},
        "total_supply": {"type": ["integer", "null"]},
        "image_url": {"type": ["string", "null"]},
        "verified": {"type": "boolean"},
        "description": {"type": ["string", "null"]},
        "last_floor_date": {"type": ["string", "null"], "format": "date"},
        "floor_eth": {"type": ["number", "null"], "description": "D55 floor of the last date, ETH (null on a gap day)"},
        "floor_usd": {"type": ["number", "null"], "description": "floor_eth x ETH-USD at 00:00 UTC of that date"},
        "change_24h": {"type": ["number", "null"], "description": "Percent change of the as-of floor over 1 day"},
        "change_7d": {"type": ["number", "null"], "description": "Percent change of the as-of floor over 7 days"},
        "volume_1d_eth": {"type": ["number", "null"], "description": "Wash-filtered sale volume of the last complete UTC day, ETH"},
        "sales_1d": {"type": ["integer", "null"], "description": "Wash-filtered sales of the last complete UTC day"}
      },
      "additionalProperties": false
    }},
    "marketplaces_counted": {"type": "string"},
    "timestamp": {"type": "string", "format": "date-time"}
  },
  "additionalProperties": false
}
```

## GET /nft/{slug}/floor?days=N -> NftFloorResponse

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "NftFloorResponse",
  "type": "object",
  "required": ["slug", "rows", "timestamp"],
  "properties": {
    "slug": {"type": "string"},
    "rows": {"type": "array", "items": {
      "type": "object",
      "required": ["date", "floor_eth", "floor_usd", "floor_source"],
      "properties": {
        "date": {"type": "string", "format": "date"},
        "floor_eth": {"type": ["number", "null"]},
        "floor_usd": {"type": ["number", "null"]},
        "eth_usd": {"type": ["number", "null"], "description": "ETH-USD at 00:00 UTC of the date (D55)"},
        "floor_source": {"type": "string"},
        "floor_age_hours": {"type": ["number", "null"], "description": "Age at 00:00 UTC of the OpenSea floor point behind this day (D67h)"},
        "floor_intraday_median_eth": {"type": ["number", "null"], "description": "Display only; collected live (D55)"}
      },
      "additionalProperties": false
    }},
    "timestamp": {"type": "string", "format": "date-time"},
    "note": {"type": ["string", "null"], "description": "Set when the data is stale"}
  },
  "additionalProperties": false
}
```

## GET /nft/{slug}/risk -> NftRiskResponse

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "NftRiskResponse",
  "type": "object",
  "required": ["slug", "volatility", "risk_score", "liquidity", "as_of", "model_version", "note", "timestamp"],
  "properties": {
    "slug": {"type": "string"},
    "volatility": {"type": ["number", "null"], "description": "Annualised volatility of the daily floor in ETH (served measure x sqrt(365))"},
    "risk_score": {"type": ["number", "null"], "minimum": 0, "maximum": 100, "description": "Higher = safer; relative to the tracked NFT collections only, not comparable to crypto (D59)"},
    "liquidity": {
      "type": "object",
      "required": ["sales_7d", "sales_30d", "volume_7d_eth", "volume_30d_eth", "liquidity_score", "label", "is_illiquid", "marketplaces_counted"],
      "properties": {
        "sales_7d": {"type": ["number", "null"]},
        "sales_30d": {"type": ["number", "null"]},
        "volume_7d_eth": {"type": ["number", "null"]},
        "volume_30d_eth": {"type": ["number", "null"]},
        "liquidity_score": {"type": ["number", "null"], "minimum": 0, "maximum": 100},
        "label": {"type": ["string", "null"], "enum": ["High", "Medium", "Low", "Illiquid", null]},
        "is_illiquid": {"type": ["boolean", "null"]},
        "wash_removed_share_30d": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        "marketplaces_counted": {"type": "string"}
      },
      "additionalProperties": false
    },
    "as_of": {"type": "string", "format": "date", "description": "The floor date these values describe (00:00 UTC)"},
    "model_version": {"type": "string"},
    "note": {"type": "string"},
    "timestamp": {"type": "string", "format": "date-time"}
  },
  "additionalProperties": false
}
```

## GET /nft/{slug}/sales?days=N -> NftSalesResponse

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "NftSalesResponse",
  "type": "object",
  "required": ["slug", "rows", "marketplaces_counted", "timestamp"],
  "properties": {
    "slug": {"type": "string"},
    "rows": {"type": "array", "items": {
      "type": "object",
      "required": ["token_id", "timestamp", "price_eth", "price_usd", "marketplace"],
      "properties": {
        "token_id": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
        "price_eth": {"type": "number"},
        "price_usd": {"type": ["number", "null"]},
        "marketplace": {"type": "string", "enum": ["opensea", "blur", "unknown"]},
        "buyer": {"type": "string"},
        "seller": {"type": "string"},
        "tx": {"type": "string"}
      },
      "additionalProperties": false
    }},
    "marketplaces_counted": {"type": "string"},
    "timestamp": {"type": "string", "format": "date-time"}
  },
  "additionalProperties": false
}
```

## GET /nft/{slug}/items/{token_id}/value -> NftItemValueResponse (step 10.7, D78)

Estimated value of one item if it sold now, in ETH, point only. Unknown slug or token: 404. Model or data unavailable: 503.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "NftItemValueResponse",
  "type": "object",
  "required": [
    "slug",
    "token_id",
    "estimated_value_eth",
    "method",
    "last_floor_eth",
    "last_floor_time",
    "last_sale",
    "no_prior_sale",
    "rarity_rank",
    "rarity_ranked_tokens",
    "accuracy_note",
    "model_version",
    "note",
    "as_of",
    "timestamp"
  ],
  "properties": {
    "slug": {
      "type": "string"
    },
    "token_id": {
      "type": "string"
    },
    "estimated_value_eth": {
      "type": [
        "number",
        "null"
      ],
      "description": "Point estimate in ETH: last floor point before as_of x exp(predicted premium). No range is served (D77)."
    },
    "method": {
      "type": "string",
      "enum": [
        "model",
        "baseline_b2"
      ],
      "description": "Per-collection serving choice, config.NFT_FV_SERVE (D78)"
    },
    "last_floor_eth": {
      "type": [
        "number",
        "null"
      ],
      "description": "The last OpenSea floor point before as_of, ETH"
    },
    "last_floor_time": {
      "type": [
        "string",
        "null"
      ],
      "format": "date-time"
    },
    "last_sale": {
      "type": [
        "object",
        "null"
      ],
      "required": [
        "price_eth",
        "timestamp"
      ],
      "properties": {
        "price_eth": {
          "type": "number"
        },
        "timestamp": {
          "type": "string",
          "format": "date-time"
        }
      },
      "additionalProperties": false
    },
    "no_prior_sale": {
      "type": "boolean",
      "description": "The item has no earlier sale in the data (prev_* features missing)"
    },
    "rarity_rank": {
      "type": [
        "integer",
        "null"
      ],
      "description": "1 = rarest; traits only, ID-like categories excluded"
    },
    "rarity_ranked_tokens": {
      "type": "integer"
    },
    "accuracy_note": {
      "type": "string",
      "description": "From the served artifact's metadata ('Accuracy check pending' until 10.9)"
    },
    "model_version": {
      "type": "string"
    },
    "note": {
      "type": [
        "string",
        "null"
      ]
    },
    "as_of": {
      "type": "string",
      "format": "date-time",
      "description": "The request time t the estimate describes"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    }
  },
  "additionalProperties": false
}
```

## GET /nft/items/value?items=slug:token_id,... -> NftItemValuesResponse (step 10.7, D78)

The same for up to `config.NFT_FV_MAX_BATCH` items (demo holdings). A malformed list: 422.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "NftItemValuesResponse",
  "type": "object",
  "required": [
    "items",
    "timestamp"
  ],
  "properties": {
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "slug",
          "token_id",
          "estimated_value_eth",
          "method",
          "last_floor_eth",
          "last_floor_time",
          "last_sale",
          "no_prior_sale",
          "rarity_rank",
          "rarity_ranked_tokens",
          "accuracy_note",
          "model_version",
          "note",
          "as_of"
        ],
        "properties": {
          "slug": {
            "type": "string"
          },
          "token_id": {
            "type": "string"
          },
          "estimated_value_eth": {
            "type": [
              "number",
              "null"
            ],
            "description": "Point estimate in ETH: last floor point before as_of x exp(predicted premium). No range is served (D77)."
          },
          "method": {
            "type": "string",
            "enum": [
              "model",
              "baseline_b2"
            ],
            "description": "Per-collection serving choice, config.NFT_FV_SERVE (D78)"
          },
          "last_floor_eth": {
            "type": [
              "number",
              "null"
            ],
            "description": "The last OpenSea floor point before as_of, ETH"
          },
          "last_floor_time": {
            "type": [
              "string",
              "null"
            ],
            "format": "date-time"
          },
          "last_sale": {
            "type": [
              "object",
              "null"
            ],
            "required": [
              "price_eth",
              "timestamp"
            ],
            "properties": {
              "price_eth": {
                "type": "number"
              },
              "timestamp": {
                "type": "string",
                "format": "date-time"
              }
            },
            "additionalProperties": false
          },
          "no_prior_sale": {
            "type": "boolean",
            "description": "The item has no earlier sale in the data (prev_* features missing)"
          },
          "rarity_rank": {
            "type": [
              "integer",
              "null"
            ],
            "description": "1 = rarest; traits only, ID-like categories excluded"
          },
          "rarity_ranked_tokens": {
            "type": "integer"
          },
          "accuracy_note": {
            "type": "string",
            "description": "From the served artifact's metadata ('Accuracy check pending' until 10.9)"
          },
          "model_version": {
            "type": "string"
          },
          "note": {
            "type": [
              "string",
              "null"
            ]
          },
          "as_of": {
            "type": "string",
            "format": "date-time",
            "description": "The request time t the estimate describes"
          }
        },
        "additionalProperties": false
      }
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    }
  },
  "additionalProperties": false
}
```

## Notes

- Rows are wash-filtered (D57) and only cover sales reported by OpenSea, including Blur-pool (BETH) sales (D56).
- The NFT risk score uses its own percentile pool of the tracked NFT collections. It cannot be compared with `/risk/{asset}` (D59).
