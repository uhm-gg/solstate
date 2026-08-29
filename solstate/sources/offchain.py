"""Off-chain economic data: TVL, stablecoins, DEX volume, fees/REV, price.

All keyless. DefiLlama and CoinGecko's public tiers cover everything the brief
asks for, so the tool needs no configuration to run.
"""
import time
import concurrent.futures as cf

from solstate.http import get_json

TIMEOUT = 30
CHAIN = "Solana"


def _get(url, **kw):
    return get_json(url, timeout=TIMEOUT, **kw)


def _pct(new, old):
    return ((new - old) / old * 100) if old else 0.0


# ---------------------------------------------------------------------- TVL
def tvl():
    hist = _get(f"https://api.llama.fi/v2/historicalChainTvl/{CHAIN}")
    if not hist:
        return {}
    cur = hist[-1]["tvl"]

    def back(days):
        i = max(0, len(hist) - 1 - days)
        return hist[i]["tvl"]

    return {
        "tvl_usd": cur,
        "change_1d_pct": _pct(cur, back(1)),
        "change_7d_pct": _pct(cur, back(7)),
        "change_30d_pct": _pct(cur, back(30)),
        "ath_usd": max(h["tvl"] for h in hist),
        "history": [{"date": h["date"], "tvl": h["tvl"]} for h in hist[-90:]],
    }


# DefiLlama reports exchange reserves held on Solana under the CEX category.
# Those are custodial balances, not Solana DeFi -- including them puts
# "Binance CEX" at the top of the ecosystem with a TVL larger than the entire
# chain's DeFi TVL, which is nonsense. Excluded from protocol rankings.
EXCLUDED_CATEGORIES = {"CEX", "Chain"}


def protocols(top_n=15):
    """Top Solana DeFi protocols by TVL. The full list is ~9MB, so filter hard."""
    data = _get("https://api.llama.fi/protocols")
    sol, excluded_usd = [], 0.0
    for p in data:
        chain_tvls = p.get("chainTvls") or {}
        v = chain_tvls.get(CHAIN)
        if not v or v < 1_000_000:
            continue
        if p.get("category") in EXCLUDED_CATEGORIES:
            excluded_usd += v
            continue
        sol.append({
            "name": p.get("name"), "category": p.get("category"),
            "tvl_usd": v,
            "change_1d_pct": p.get("change_1d") or 0,
            "change_7d_pct": p.get("change_7d") or 0,
            "url": p.get("url"),
        })
    sol.sort(key=lambda p: -p["tvl_usd"])
    cats = {}
    for p in sol:
        cats[p["category"]] = cats.get(p["category"], 0) + p["tvl_usd"]
    return {
        "count": len(sol),
        "top": sol[:top_n],
        "by_category": sorted(({"category": k, "tvl_usd": v} for k, v in cats.items()),
                              key=lambda c: -c["tvl_usd"])[:10],
        "excluded_cex_usd": excluded_usd,
    }


# -------------------------------------------------------------- stablecoins
def stablecoins():
    """Stablecoin float on Solana.

    /stablecoinchains carries only a current snapshot -- no prevDay/prevWeek
    fields exist on it, so deltas must come from the chart endpoint or they
    silently read as 0%.
    """
    cur = 0.0
    try:
        for row in _get("https://stablecoins.llama.fi/stablecoinchains"):
            if row.get("name") == CHAIN:
                cur = (row.get("totalCirculatingUSD") or {}).get("peggedUSD", 0)
                break
    except Exception:
        pass

    out = {"total_usd": cur, "change_1d_pct": 0.0, "change_7d_pct": 0.0,
           "change_30d_pct": 0.0, "history": []}
    try:
        chart = _get(f"https://stablecoins.llama.fi/stablecoincharts/{CHAIN}")
        pts = [{"date": int(p["date"]),
                "total": (p.get("totalCirculatingUSD") or {}).get("peggedUSD", 0)}
               for p in chart if p.get("totalCirculatingUSD")]
        if pts:
            if not cur:
                out["total_usd"] = cur = pts[-1]["total"]

            def back(days):
                return pts[max(0, len(pts) - 1 - days)]["total"]

            out["change_1d_pct"] = _pct(cur, back(1))
            out["change_7d_pct"] = _pct(cur, back(7))
            out["change_30d_pct"] = _pct(cur, back(30))
            out["history"] = pts[-90:]
    except Exception:
        pass
    return out


# ------------------------------------------------------------ volume & fees
def _overview(kind):
    """DefiLlama dexs/fees overview for Solana."""
    d = _get(f"https://api.llama.fi/overview/{kind}/solana"
             "?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true")
    return {
        "total_24h": d.get("total24h"),
        "total_7d": d.get("total7d"),
        "total_30d": d.get("total30d"),
        "change_1d_pct": d.get("change_1d"),
        "change_7d_pct": d.get("change_7d"),
        "top": sorted(
            ({"name": p.get("name"), "total_24h": p.get("total24h") or 0}
             for p in d.get("protocols", []) if p.get("total24h")),
            key=lambda p: -p["total_24h"])[:10],
    }


def dex_volume():
    return _overview("dexs")


def fees():
    """DefiLlama 'fees' for Solana is the standard proxy for REV
    (Real Economic Value): base fees + priority fees + MEV tips."""
    return _overview("fees")


# --------------------------------------------------------------------- price
def price():
    d = _get("https://api.coingecko.com/api/v3/coins/solana"
             "?localization=false&tickers=false&community_data=false"
             "&developer_data=false&sparkline=false")
    m = d.get("market_data", {})

    def usd(k):
        v = m.get(k)
        return (v or {}).get("usd") if isinstance(v, dict) else v

    return {
        "price_usd": usd("current_price"),
        "market_cap_usd": usd("market_cap"),
        "fdv_usd": usd("fully_diluted_valuation"),
        "volume_24h_usd": usd("total_volume"),
        "change_24h_pct": m.get("price_change_percentage_24h"),
        "change_7d_pct": m.get("price_change_percentage_7d"),
        "change_30d_pct": m.get("price_change_percentage_30d"),
        "ath_usd": usd("ath"),
        "ath_change_pct": (m.get("ath_change_percentage") or {}).get("usd"),
        "atl_usd": usd("atl"),
        "market_cap_rank": d.get("market_cap_rank"),
        "circulating_supply": m.get("circulating_supply"),
    }


def price_fallback():
    """DefiLlama price feed, used when CoinGecko rate-limits."""
    d = _get("https://coins.llama.fi/prices/current/coingecko:solana")
    c = d.get("coins", {}).get("coingecko:solana", {})
    return {"price_usd": c.get("price"), "source": "defillama"}


# ------------------------------------------------------------------ collect
COLLECTORS = {
    "tvl": tvl, "protocols": protocols, "stablecoins": stablecoins,
    "dex_volume": dex_volume, "fees": fees, "price": price,
}


def collect_all():
    """Run every off-chain collector concurrently; a failure in one must not
    take down the report."""
    out, errors = {}, {}

    def run(item):
        k, fn = item
        t0 = time.time()
        try:
            return k, fn(), None, round((time.time() - t0) * 1000)
        except Exception as e:
            return k, None, f"{type(e).__name__}: {str(e)[:140]}", 0

    with cf.ThreadPoolExecutor(max_workers=len(COLLECTORS)) as ex:
        for k, val, err, ms in ex.map(run, COLLECTORS.items()):
            if err:
                errors[k] = err
            else:
                out[k] = val

    if "price" in errors:
        try:
            out["price"] = price_fallback()
            errors["price"] += " (used DefiLlama fallback)"
        except Exception:
            pass
    return out, errors
