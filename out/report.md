# Solana Ecosystem Report

*Generated 2026-08-29 22:06:22 UTC · solstate v1.0.0 · collected in 8.2s*

> All monitored metrics are within normal range.

## At a glance

| Metric | Value | Change |
|---|---:|---:|
| SOL price | $105.00 | +1.51% |
| Market cap | $61.35B | rank #7 |
| TPS (30m avg) | 3,954 | 1,791 non-vote |
| Avg slot time | 0.316s |  |
| Total value locked | $5.91B | -1.71% |
| Stablecoin float | $15.89B | -2.58% |
| DEX volume 24h | $2.59B | -29.99% |
| REV 24h | $15.73M | $5.74B annualised |
| Active validators | 686 | 11 delinquent |
| Nakamoto coefficient | 18 | superminority 41 |
| Staked of circulating | 74.66% | $45.79B |

## Anomaly detection

No anomalies detected against current baselines.

Baselines are built from locally stored snapshots, so detection sharpens the longer the tool runs. Absolute safety rules (slot time, delinquency, large price/TVL moves) fire from the first run.

## Network performance

- **Epoch 1024** — 80.5% complete, ends in 7h 23m
- Slot `442,715,956` · block height `420,763,782`
- Average slot time (30m): **0.316s**
- Throughput: **3,954 TPS** total, 1,791 TPS non-vote (54.7% of traffic is consensus votes)
- Estimated daily transactions: 341,668,368 (154,736,832 non-vote)
- Validator client: `4.2.1` · RPC health: `ok`

## Validators & decentralisation

- **686 active**, 11 delinquent (1.58%)
- Total stake: **436,134,289 SOL** ($45.79B)
- **Nakamoto coefficient: 18** — validators needed to control >33% of stake and halt the chain
- Superminority (>50% of stake): 41 validators
- Top 10 control 24.15%; top 50 control 55.25%
- 247 validators run 0% commission (median commission 5%)

| Vote account | Stake (SOL) | Share | Commission |
|---|---:|---:|---:|
| `CcaHc2L43ZWjwCHART3oZoJv…` | 16,991,835 | 3.90% | 7% |
| `he1iusunGwqrNtafDtLdhsUQ…` | 16,035,737 | 3.68% | 0% |
| `3N7s9zXMZ4QqvHQR15t5GNHy…` | 12,393,242 | 2.84% | 0% |
| `CatzoSMUkTRidT5DwBxAC2pE…` | 11,460,007 | 2.63% | 5% |
| `26pV97Ce83ZQ6Kz9XT4td8td…` | 9,292,131 | 2.13% | 7% |
| `8GbwASqdpw4dVcwbWUxbHXMr…` | 9,081,213 | 2.08% | 0% |
| `51JBzSTU5rAM8gLAVQKgp4Wo…` | 9,001,204 | 2.06% | 10% |
| `CvSb7wdQAFpHuSpTYTJnX5SY…` | 7,294,487 | 1.67% | 5% |
| `9QU2QSxhb24FUX3Tu2FpczXj…` | 7,192,557 | 1.65% | 7% |
| `DumiCKHVqoCQKD8roLApzR5F…` | 6,585,996 | 1.51% | 0% |

## Economics

- SOL **$105.00** (+1.51% 24h, +13.02% 7d, +41.09% 30d)
- Market cap $61.35B · FDV $66.49B · -64.2% from ATH
- **REV (24h): $15.73M**, $5.74B annualised — a 12.54% yield on staked value
- Base fee per signature: $0.000525 · average REV per non-vote txn: $0.1016
- Inflation 3.67% → nominal staking yield ≈ 4.92%
- Stablecoin float on Solana: **$15.89B** (-2.58% 24h, -2.86% 7d)

> REV uses DefiLlama's Solana fee series — base fees plus priority fees plus MEV tips. The per-transaction figure is an **average**, not a median: priority fees are heavily skewed, and a true median needs per-block sampling that no keyless public endpoint provides.

## DeFi & ecosystem

- TVL **$5.91B** (-1.71% 24h, +6.46% 7d, +23.20% 30d) · ATH $13.24B
- DEX volume 24h $2.59B → volume/TVL turnover of 0.44x
- 147 protocols tracked with >$1M on Solana
- $12.25B of centralised-exchange reserves excluded from these rankings — those are custodial balances, not DeFi

| Protocol | Category | TVL | 24h | 7d |
|---|---|---:|---:|---:|
| Sanctum Validator LSTs | Liquid Staking | $1.61B | +1.9% | +14.0% |
| Kamino Lend | Lending | $1.26B | +2.8% | +5.7% |
| Raydium AMM | Dexs | $1.14B | +0.1% | +10.0% |
| Jupiter Lend | Lending | $1.10B | +1.2% | +4.5% |
| Binance Staked SOL | Liquid Staking | $1.09B | +1.6% | +14.0% |
| Jito Liquid Staking | Liquid Staking | $1.06B | +1.5% | +12.0% |
| BlackRock BUIDL | RWA | $886.54M | +0.0% | +6.1% |
| Jupiter Perpetual Exchange | Derivatives | $772.82M | +1.2% | +4.2% |
| Jupiter Staked SOL | Liquid Staking | $547.40M | +2.0% | +12.1% |
| xStocks | RWA | $433.46M | +0.5% | +3.7% |

**TVL by category:** Liquid Staking $6.27B · Lending $2.64B · Dexs $2.37B · RWA $2.07B · Derivatives $858.74M · Staking Pool $658.38M

## Tokenised real-world assets

- Total RWA on Solana: **$2.07B** across 20 issuers
- Of which **tokenised equities: $458.22M**

  - Treasuries & credit: $1.29B
  - Tokenised equities: $458.22M
  - Other RWA: $318.49M
  - Commodities: $9.61M

| Issuer | Type | TVL | 24h |
|---|---|---:|---:|
| BlackRock BUIDL | Treasuries & credit | $886.54M | +0.00% |
| xStocks | Tokenised equities | $433.46M | +0.52% |
| OnRe | Other RWA | $284.65M | +0.05% |
| Ondo Yield Assets | Treasuries & credit | $179.89M | +0.32% |
| Hastra | Treasuries & credit | $157.92M | -0.25% |
| Theo Network thBill | Treasuries & credit | $26.40M | +0.00% |
| Ondo Global Markets | Tokenised equities | $24.76M | -1.15% |
| Plume Vaults | Other RWA | $22.87M | +0.16% |

## Ecosystem news

- [The Token Supercycle Is Here: Solana Brings Breakpoint 2026 to London](https://solana.com/news/breakpoint-2026-london-speakers) — *Solana, 2d ago*
- [Solana Changelog: August 20, 2026](https://solana.com/news/solana-changelog-august-20-2026) — *Solana, 5d ago*
- [Lowering Slot Time and Validators Economic](https://solana.com/news/lowering-slot-time-and-validators-economic) — *Solana, 10d ago*
- [Transaction v1 and the ALT Trade-off](https://solana.com/news/transaction-v1-and-the-alt-trade-off) — *Solana, 12d ago*
- [Solana Changelog: August 13, 2026](https://solana.com/news/solana-changelog-august-13-2026) — *Solana, 16d ago*
- [How Meow Built Agentic Banking and Agent Payment Rails, with Brandon Arvanaghi](https://solana.com/news/how-meow-built-agentic-banking-and-agent-payment-rails-with-brandon-arvanaghi) — *Solana, 16d ago*
- [Why Asia Is Ahead on Stablecoins, According to Reap's Daren Guo](https://solana.com/news/bits-to-bricks-asia-ahead-stablecoins-daren-guo-reap) — *Solana, 17d ago*
- [MoneyGram Ramps launches on Solana](https://solana.com/news/moneygram-ramps) — *Solana, 18d ago*

## Upcoming upgrades & developments

- **Alpenglow** (In development) — Replaces TowerBFT/Proof-of-History consensus with Votor+Rotor, targeting ~150ms finality instead of ~12.8s. *[Finality · SIMD-0326]*
- **SIMD-0525 / fee market** (Proposed) — Continued refinement of the local fee market and priority-fee handling to reduce contention-driven spikes. *[Fees · SIMD-0525]*
- **Firedancer** (Rolling out) — Jump Crypto's independent validator client, adding client diversity and higher throughput headroom. *[Throughput / resilience · jump-firedancer]*
- **Token Extensions (Token-2022)** (Live, adoption growing) — Confidential transfers, transfer hooks and metadata on the token program, targeted at institutional issuance. *[Tokenisation · spl-token-2022]*

---

Sources: Solana JSON-RPC, DefiLlama, CoinGecko, solana.com RSS. All public endpoints, no API keys. RPC used: `https://api.mainnet-beta.solana.com`.