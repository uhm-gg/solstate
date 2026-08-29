"""Orchestrate every source into one snapshot, then derive cross-source metrics."""
import time
import datetime
import concurrent.futures as cf

from solstate.sources.rpc import SolanaRpc
from solstate.sources import offchain
from solstate.sources import news as news_src

VERSION = "1.0.0"

# Publicly announced work on the Solana roadmap. Kept as data, not prose, so
# the dashboard can render it and the JSON stays machine-readable.
UPGRADES = [
    {"name": "Alpenglow", "status": "In development",
     "summary": "Replaces TowerBFT/Proof-of-History consensus with Votor+Rotor, "
                "targeting ~150ms finality instead of ~12.8s.",
     "impact": "Finality", "reference": "SIMD-0326"},
    {"name": "SIMD-0525 / fee market", "status": "Proposed",
     "summary": "Continued refinement of the local fee market and priority-fee "
                "handling to reduce contention-driven spikes.",
     "impact": "Fees", "reference": "SIMD-0525"},
    {"name": "Firedancer", "status": "Rolling out",
     "summary": "Jump Crypto's independent validator client, adding client "
                "diversity and higher throughput headroom.",
     "impact": "Throughput / resilience", "reference": "jump-firedancer"},
    {"name": "Token Extensions (Token-2022)", "status": "Live, adoption growing",
     "summary": "Confidential transfers, transfer hooks and metadata on the "
                "token program, targeted at institutional issuance.",
     "impact": "Tokenisation", "reference": "spl-token-2022"},
]


def collect(rpc_endpoints=None, top_validators=20, top_protocols=15):
    """Gather everything. Individual source failures degrade the report rather
    than aborting it, so a flaky RPC never costs you the whole run."""
    t0 = time.time()
    rpc = SolanaRpc(rpc_endpoints)
    errors = {}
    out = {}

    def guard(name, fn):
        try:
            return name, fn(), None
        except Exception as e:
            return name, None, f"{type(e).__name__}: {str(e)[:200]}"

    jobs = {
        "network": lambda: rpc.network(),
        "validators": lambda: rpc.validators(top_validators),
        "supply": lambda: rpc.supply(),
        "news": lambda: news_src.news(8),
    }
    with cf.ThreadPoolExecutor(max_workers=5) as ex:
        futs = [ex.submit(guard, k, f) for k, f in jobs.items()]
        offf = ex.submit(offchain.collect_all)
        for fu in futs:
            k, v, err = fu.result()
            if err:
                errors[k] = err
            else:
                out[k] = v
        off, off_err = offf.result()
    out.update(off)
    errors.update(off_err)

    out["upgrades"] = UPGRADES
    out["meta"] = {
        "ts": time.time(),
        "generated_at": datetime.datetime.now(datetime.timezone.utc)
                                 .strftime("%Y-%m-%d %H:%M:%S UTC"),
        "version": VERSION,
        "rpc_endpoint": rpc.last_used,
        "collect_seconds": round(time.time() - t0, 2),
        "errors": errors,
        "sources": ["Solana JSON-RPC", "DefiLlama", "CoinGecko", "solana.com RSS"],
    }
    out["derived"] = derive(out)
    return out


def derive(s):
    """Cross-source metrics that no single API returns."""
    net = s.get("network") or {}
    val = s.get("validators") or {}
    sup = s.get("supply") or {}
    price = s.get("price") or {}
    fees = s.get("fees") or {}
    d = {}

    px = price.get("price_usd") or 0
    staked = val.get("total_stake_sol") or 0
    circ = sup.get("circulating_sol") or 0

    if circ:
        d["staked_pct_of_circulating"] = staked / circ * 100
    if px:
        d["staked_usd"] = staked * px
        d["total_supply_usd"] = (sup.get("total_sol") or 0) * px

    # REV: DefiLlama's Solana "fees" series is the standard proxy -- base fees
    # plus priority fees plus MEV tips paid to validators.
    rev_24h = fees.get("total_24h")
    if rev_24h:
        d["rev_24h_usd"] = rev_24h
        d["rev_annualised_usd"] = rev_24h * 365
        if px and staked:
            d["rev_yield_on_stake_pct"] = rev_24h * 365 / (staked * px) * 100

    tx24 = (net.get("tps_avg_30m") or 0) * 86400
    nv24 = (net.get("tps_nonvote_avg_30m") or 0) * 86400
    d["est_daily_transactions"] = tx24
    d["est_daily_nonvote_transactions"] = nv24

    # Fee reporting, stated precisely rather than conveniently:
    #   * base fee is deterministic -- 5,000 lamports per signature
    #   * REV per tx is an AVERAGE, heavily skewed by priority fees and MEV
    #     tips, so it is not a median and must not be labelled as one
    # A true median priority fee needs per-block sampling that no keyless
    # public endpoint exposes, so it is deliberately not claimed here.
    LAMPORTS_PER_SOL = 1_000_000_000
    if px:
        d["base_fee_per_signature_usd"] = 5_000 / LAMPORTS_PER_SOL * px
    if nv24 and rev_24h:
        d["avg_rev_per_nonvote_tx_usd"] = rev_24h / nv24
    if tx24 and rev_24h:
        d["avg_rev_per_tx_usd"] = rev_24h / tx24

    dexv = (s.get("dex_volume") or {}).get("total_24h")
    tvl_usd = (s.get("tvl") or {}).get("tvl_usd")
    if dexv and tvl_usd:
        d["dex_volume_to_tvl"] = dexv / tvl_usd

    stab = (s.get("stablecoins") or {}).get("total_usd")
    if stab and tvl_usd:
        d["stablecoin_to_tvl_ratio"] = stab / tvl_usd

    if net.get("epoch_eta_seconds"):
        secs = net["epoch_eta_seconds"]
        d["epoch_eta_human"] = f"{int(secs // 3600)}h {int(secs % 3600 // 60)}m"

    infl = sup.get("inflation_total_pct") or 0
    if infl and circ and staked:
        # Staking yield ≈ inflation scaled by the share of supply actually staked.
        d["nominal_staking_yield_pct"] = infl * circ / staked
    return d
