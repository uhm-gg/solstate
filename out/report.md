# Solana Ecosystem Report

*Generated 2026-08-29 21:25:09 UTC · solstate v1.0.0 · collected in 7.38s*

> All monitored metrics are within normal range.

## At a glance

| Metric | Value | Change |
|---|---:|---:|
| SOL price | $105.20 | +1.54% |
| Market cap | $61.45B | rank #7 |
| TPS (30m avg) | 3,925 | 1,757 non-vote |
| Avg slot time | 0.317s |  |
| Total value locked | $5.90B | -1.84% |
| Stablecoin float | $15.89B | -2.61% |
| DEX volume 24h | $2.59B | -29.99% |
| REV 24h | $15.73M | $5.74B annualised |
| Active validators | 689 | 8 delinquent |
| Nakamoto coefficient | 18 | superminority 41 |
| Staked of circulating | 74.66% | $45.88B |

## Anomaly detection

No anomalies detected against current baselines.

Baselines are built from locally stored snapshots, so detection sharpens the longer the tool runs. Absolute safety rules (slot time, delinquency, large price/TVL moves) fire from the first run.

## Network performance

- **Epoch 1024** — 78.7% complete, ends in 8h 4m
- Slot `442,708,136` · block height `420,755,970`
- Average slot time (30m): **0.317s**
- Throughput: **3,925 TPS** total, 1,757 TPS non-vote (55.2% of traffic is consensus votes)
- Estimated daily transactions: 339,093,696 (151,776,768 non-vote)
- Validator client: `4.2.1` · RPC health: `ok`

## Validators & decentralisation

- **689 active**, 8 delinquent (1.15%)
- Total stake: **436,134,289 SOL** ($45.88B)
- **Nakamoto coefficient: 18** — validators needed to control >33% of stake and halt the chain
- Superminority (>50% of stake): 41 validators
- Top 10 control 24.15%; top 50 control 55.25%
- 248 validators run 0% commission (median commission 5%)

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

- SOL **$105.20** (+1.54% 24h, +11.45% 7d, +41.36% 30d)
- Market cap $61.45B · FDV $66.60B · -64.1% from ATH
- **REV (24h): $15.73M**, $5.74B annualised — a 12.51% yield on staked value
- Base fee per signature: $0.000526 · average REV per non-vote txn: $0.1036
- Inflation 3.67% → nominal staking yield ≈ 4.92%
- Stablecoin float on Solana: **$15.89B** (-2.61% 24h, -2.88% 7d)

> REV uses DefiLlama's Solana fee series — base fees plus priority fees plus MEV tips. The per-transaction figure is an **average**, not a median: priority fees are heavily skewed, and a true median needs per-block sampling that no keyless public endpoint provides.

## DeFi & ecosystem

- TVL **$5.90B** (-1.84% 24h, +6.31% 7d, +23.03% 30d) · ATH $13.24B
- DEX volume 24h $2.59B → volume/TVL turnover of 0.44x
- 147 protocols tracked with >$1M on Solana
- $12.24B of centralised-exchange reserves excluded from these rankings — those are custodial balances, not DeFi

| Protocol | Category | TVL | 24h | 7d |
|---|---|---:|---:|---:|
| Sanctum Validator LSTs | Liquid Staking | $1.60B | +1.1% | +13.3% |
| Kamino Lend | Lending | $1.25B | +2.4% | +5.8% |
| Raydium AMM | Dexs | $1.13B | -0.9% | +9.9% |
| Jupiter Lend | Lending | $1.10B | +1.2% | +4.5% |
| Binance Staked SOL | Liquid Staking | $1.09B | +1.6% | +14.0% |
| Jito Liquid Staking | Liquid Staking | $1.06B | +1.5% | +12.0% |
| BlackRock BUIDL | RWA | $886.54M | +0.0% | +6.1% |
| Jupiter Perpetual Exchange | Derivatives | $772.82M | +1.2% | +4.2% |
| Jupiter Staked SOL | Liquid Staking | $547.40M | +2.0% | +12.1% |
| xStocks | RWA | $433.46M | +0.5% | +3.7% |

**TVL by category:** Liquid Staking $6.27B · Lending $2.63B · Dexs $2.37B · RWA $2.07B · Derivatives $858.74M · Staking Pool $658.38M

## Upcoming upgrades & developments

- **Alpenglow** (In development) — Replaces TowerBFT/Proof-of-History consensus with Votor+Rotor, targeting ~150ms finality instead of ~12.8s. *[Finality · SIMD-0326]*
- **SIMD-0525 / fee market** (Proposed) — Continued refinement of the local fee market and priority-fee handling to reduce contention-driven spikes. *[Fees · SIMD-0525]*
- **Firedancer** (Rolling out) — Jump Crypto's independent validator client, adding client diversity and higher throughput headroom. *[Throughput / resilience · jump-firedancer]*
- **Token Extensions (Token-2022)** (Live, adoption growing) — Confidential transfers, transfer hooks and metadata on the token program, targeted at institutional issuance. *[Tokenisation · spl-token-2022]*

---

Sources: Solana JSON-RPC, DefiLlama, CoinGecko. All public endpoints, no API keys. RPC used: `https://api.mainnet-beta.solana.com`.