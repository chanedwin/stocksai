# Reference data sources

| File | Source | Pinned commit | Fetched | License/attribution |
|---|---|---|---|---|
| `sp500_constituents.csv` | [fja05680/sp500](https://github.com/fja05680/sp500), file `S&P 500 Historical Components & Changes (Updated).csv` | `b792557e915703398ef9a67e4b583a37c6ec80d5` | 2026-07-09 | Community-reconstructed from public sources; known pre-2004 undercount (487-494 members). Verify with `python -m pipeline.collect.cli verify-constituents` after any update. |

Update procedure: fetch the file at a new upstream commit, update the pin here, run the verification pass, commit both together.
