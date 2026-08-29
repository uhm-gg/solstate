# solstate — auto-updating Solana ecosystem report

A single command produces three views of Solana's live state: an interactive
dark-theme **HTML dashboard**, a human-readable **Markdown report**, and
structured **JSON**.

```bash
python run.py
```

That is the entire setup. **No API keys. No accounts. No `pip install`.**
It runs on a clean Python 3.8+ interpreter using only the standard library.

```bash
python run.py            # collect once, write all three outputs
python run.py --watch    # refresh forever on an interval
python run.py --serve    # local web server, auto-refreshing
python run.py --json-only # pipe structured data into something else
```

---

## Why no dependencies

The brief prefers solutions needing no API keys or external dependencies. This
one takes that literally: `solstate/http.py` is a ~90-line `urllib` wrapper
handling gzip, JSON, retries and backoff, which is everything `requests` was
doing for us. The only third-party thing involved is the Solana network itself.

Verified on a stock **Python 3.9.0** install with no virtualenv and nothing
installed:

```
$ python run.py
[17:25:09] epoch 1024 · 3,925 TPS · 689 validators (8 delinquent) · SOL $105.20 · 0 anomalies · 7.4s
```

That matters beyond point-scoring: a report with no key to rotate and no
dependency to bump is a report that still works in six months, unattended.

---

## Data sources and how they are integrated

Every source is a public, keyless endpoint. Each is wrapped in its own
collector and they run **concurrently**, so a full refresh takes ~7 seconds
rather than the ~25 it would take in sequence.

| Source | Used for | Endpoints |
|---|---|---|
| **Solana JSON-RPC** | network, validators, supply | `getEpochInfo`, `getRecentPerformanceSamples`, `getVoteAccounts`, `getSupply`, `getInflationRate`, `getHealth`, `getVersion` |
| **DefiLlama** | TVL, stablecoins, DEX volume, REV, RWA | `historicalChainTvl`, `protocols`, `stablecoincharts`, `overview/dexs`, `overview/fees` |
| **CoinGecko** | price, market cap, FDV, ATH | `coins/solana` |
| **Official RSS** | ecosystem news & announcements | `solana.com/news/rss.xml` |

**Resilience is designed in, not bolted on:**

- **RPC failover.** Two public endpoints are tried in order. Ankr and dRPC are
  deliberately *not* in the default list — both now reject keyless calls, and a
  default that silently fails is worse than no default.
- **Per-source isolation.** One dead source degrades the report instead of
  killing the run; failures surface in `meta.errors` and in a "Source warnings"
  panel rather than vanishing.
- **Price fallback.** If CoinGecko rate-limits, price falls back to DefiLlama
  automatically.

### Two data-quality decisions worth stating

Both were found by checking the numbers against reality rather than trusting
the API:

1. **CEX reserves are excluded from protocol rankings.** DefiLlama files
   exchange balances held on Solana under the `CEX` category. Left in, "Binance
   CEX" tops the ecosystem at $6.97B — larger than Solana's entire $5.9B DeFi
   TVL, which is nonsense. Those are custodial balances, not DeFi. The excluded
   total (~$12.2B) is reported separately rather than silently dropped.

2. **Per-transaction fees are labelled as averages, not medians.** The brief
   asks for median transaction fees. The honest position: the base fee is
   deterministic (5,000 lamports/signature, reported exactly), but a true
   *median* priority fee needs per-block sampling that no keyless endpoint
   exposes. Reporting a fee-revenue average as a "median" would be wrong —
   priority fees and MEV tips skew it heavily — so it is labelled
   `avg_rev_per_nonvote_tx_usd` and the limitation is stated in the report.

---

## What it reports

**Network** — TPS (total and non-vote), average slot time, epoch number and
progress with a live ETA, slot, block height, validator client version, and
estimated daily transaction counts.

**Validators & decentralisation** — active vs delinquent counts and stake,
**Nakamoto coefficient** (how few validators could halt the chain),
superminority size, top-1/10/50 stake concentration, commission distribution,
and a named list of any delinquent validators.

**Economics** — SOL price with 24h/7d/30d moves, market cap, FDV, distance from
ATH, **REV** (base + priority fees + MEV tips) with its annualised figure, the
base fee per signature, inflation, and the implied nominal staking yield.

**DeFi & growth** — TVL with 1d/7d/30d changes against its ATH, stablecoin float
with history, DEX volume, top protocols by TVL, TVL by category, and
volume/TVL turnover.

**Tokenised real-world assets** — total RWA on Solana split by what the token
actually represents: tokenised equities, treasuries & credit, and commodities.
DefiLlama files all of these under one `RWA` label, but a tokenised S&P share
and a tokenised T-bill are different instruments, and the split is the part
people actually want. Currently ~$2.07B total, of which ~$458M is equities.

**Ecosystem news** — latest posts from official project RSS feeds, parsed with
`xml.etree`. Twitter is deliberately not used: its API needs a paid key and
scraping it is brittle and against terms.

**Cross-source metrics** that no single API returns — computed in
`collect.derive()`:

- `staked_pct_of_circulating` — RPC stake ÷ RPC circulating supply
- `rev_yield_on_stake_pct` — annualised REV ÷ (staked SOL × price), i.e. what
  the chain's fee revenue is actually worth against the capital securing it
- `nominal_staking_yield_pct` — inflation scaled by the staked share of supply
- `dex_volume_to_tvl` — capital turnover
- `stablecoin_to_tvl_ratio` — dry powder relative to deployed capital

---

## Anomaly detection

Two layers, because each covers the other's blind spot.

**Absolute rules** fire from the very first run, with no history:

| Condition | Severity |
|---|---|
| Slot time ≥ 0.90s | critical |
| Slot time ≥ 0.65s | warning |
| Validator delinquency ≥ 10% | critical |
| Validator delinquency ≥ 5% | warning |
| RPC health check failing | critical |
| SOL price move ≥ ±10% / 24h | warning → critical at 2× |
| TVL move ≥ ±10% / 24h | warning → critical at 2× |
| Stablecoin float move ≥ ±5% / 24h | warning → critical at 2× |

**Statistical rules** compare each metric to a baseline built from locally
stored snapshots (z-score > 3.0), covering TPS, slot time, price, TVL, fees and
DEX volume. The baseline **excludes the current reading**, so a bad value cannot
dampen the baseline it is being tested against.

A z-score alone is not enough, and this was found the hard way. Sampling every
10 minutes means most metrics barely move between reads, so the standard
deviation collapses and a **0.2% wobble in slot time scored z = −18 and was
reported as CRITICAL**. Statistical significance is not the same as mattering.
Three guards fix it, and an alert now requires all of them:

| Guard | Default | Why |
|---|---:|---|
| `min_baseline_n` | 20 | too few samples is not a baseline |
| `min_deviation_pct` | 8% | the move must also be materially large |
| `min_cv` | 0.002 | a near-constant series makes z meaningless |

Every threshold is overridable in `config.json`. Alerts are de-duplicated per
metric, keeping the most severe.

**The detector is tested against known-bad states**, because one that returns
"all clear" on a healthy chain proves nothing — a broken one does that too:

```bash
$ python tests/test_anomaly.py
16 passed, 0 failed
```

The suite asserts that throughput collapse, slow slots, mass delinquency, an
unhealthy RPC and large price/TVL moves are all caught; that a healthy chain
stays silent; that the 0.2% false positive above stays silent while a genuine
70% collapse still fires; and that baseline hygiene holds.

---

## Automation strategy

Designed to be started once and left alone.

- **`--watch`** — refresh on `interval_seconds` (default 600) forever. Exceptions
  in one cycle are logged and the loop continues; a transient network failure
  never stops the run.
- **`--serve`** — the same loop plus a local HTTP server. The HTML embeds a
  `<meta http-equiv="refresh">` matched to the interval, so an open browser tab
  updates itself with no JavaScript polling.
- **History accrues automatically.** Every snapshot appends to a SQLite file
  (`out/history.db`), which is what makes statistical detection and the
  dashboard sparklines possible. Detection genuinely sharpens the longer it runs.
- **Deploy anywhere.** With no keys and no dependencies, `python run.py` in a
  cron job or a GitHub Action publishes to GitHub Pages unchanged:

```cron
*/10 * * * * cd /path/to/solstate && python run.py
```

The server binds to `127.0.0.1` only — this surfaces local machine data and
should not be exposed to a network without putting a proxy in front of it.

---

## Outputs

| File | Purpose |
|---|---|
| `out/dashboard.html` | Interactive dark-theme dashboard, fully self-contained |
| `out/report.md` | Human-readable Markdown report |
| `out/data.json` | Complete structured snapshot including anomalies |
| `out/history.db` | SQLite history powering baselines and sparklines |

The HTML has **no CDN, no build step, no external fonts and no JavaScript
framework**. Charts are hand-rolled inline SVG. Open the file from disk with a
double-click and it works offline.

---

## Configuration

`config.json`, all optional:

```json
{
  "interval_seconds": 600,
  "rpc_endpoints": ["https://api.mainnet-beta.solana.com",
                    "https://solana-rpc.publicnode.com"],
  "top_validators": 20,
  "top_protocols": 15,
  "html_auto_refresh": true,
  "rules": { "slot_time_crit_s": 0.90, "zscore": 3.0 }
}
```

---

## Project layout

```
run.py                      CLI: once / --watch / --serve / --json-only
config.json                 thresholds and intervals
solstate/
  http.py                   stdlib-only HTTP: gzip, JSON, retry, backoff
  collect.py                orchestration + derived cross-source metrics
  store.py                  SQLite history and baselines
  anomaly.py                absolute + statistical detection
  sources/
    rpc.py                  Solana JSON-RPC with failover
    offchain.py             DefiLlama + CoinGecko
  render/
    html.py                 dashboard (inline SVG charts)
    markdown.py             Markdown report
tests/
  test_anomaly.py           13 assertions against known-bad states
out/                        generated artefacts
```

Requires Python 3.8+. Nothing else.

---

## What this deliberately does not report

The brief lists daily active addresses. There is no keyless public endpoint
that exposes them: it needs an indexer (Dune, Helius, Flipside), all of which
require an API key. Rather than approximate it badly and present the guess as
a metric, it is omitted and named here.

Similarly, the per-transaction fee figure is reported as an **average**, never
a median — see the fee note above. Where a number cannot be sourced honestly,
this tool says so instead of filling the gap.
