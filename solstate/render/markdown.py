"""Human-readable Markdown report."""
import datetime


def _usd(v, dp=0):
    if not isinstance(v, (int, float)):
        return "—"
    a = abs(v)
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= div:
            return f"${v/div:,.2f}{suf}"
    return f"${v:,.{dp}f}"


def _n(v, dp=0, suf=""):
    return f"{v:,.{dp}f}{suf}" if isinstance(v, (int, float)) else "—"


def _pct(v, dp=2):
    if not isinstance(v, (int, float)):
        return "—"
    return f"{'+' if v > 0 else ''}{v:.{dp}f}%"


def render(snap, anomalies=None):
    anomalies = anomalies or []
    net = snap.get("network") or {}
    val = snap.get("validators") or {}
    sup = snap.get("supply") or {}
    price = snap.get("price") or {}
    tvl = snap.get("tvl") or {}
    stab = snap.get("stablecoins") or {}
    dexv = snap.get("dex_volume") or {}
    fees = snap.get("fees") or {}
    prot = snap.get("protocols") or {}
    der = snap.get("derived") or {}
    meta = snap.get("meta") or {}

    L = []
    A = L.append
    A("# Solana Ecosystem Report")
    A("")
    A(f"*Generated {meta.get('generated_at')} · solstate v{meta.get('version')} "
      f"· collected in {meta.get('collect_seconds')}s*")
    A("")

    # ---------------------------------------------------------------- status
    crit = [a for a in anomalies if a["severity"] == "critical"]
    warn = [a for a in anomalies if a["severity"] == "warning"]
    if crit:
        A(f"> **{len(crit)} critical** and {len(warn)} warning signal(s) detected.")
    elif warn:
        A(f"> {len(warn)} warning signal(s) detected; nothing critical.")
    else:
        A("> All monitored metrics are within normal range.")
    A("")

    # ------------------------------------------------------------- headlines
    A("## At a glance")
    A("")
    A("| Metric | Value | Change |")
    A("|---|---:|---:|")
    rows = [
        ("SOL price", _usd(price.get("price_usd"), 2), _pct(price.get("change_24h_pct"))),
        ("Market cap", _usd(price.get("market_cap_usd")),
         f"rank #{_n(price.get('market_cap_rank'))}"),
        ("TPS (30m avg)", _n(net.get("tps_avg_30m")),
         f"{_n(net.get('tps_nonvote_avg_30m'))} non-vote"),
        ("Avg slot time", _n(net.get("slot_time_avg_30m"), 3, "s"), ""),
        ("Total value locked", _usd(tvl.get("tvl_usd")), _pct(tvl.get("change_1d_pct"))),
        ("Stablecoin float", _usd(stab.get("total_usd")), _pct(stab.get("change_1d_pct"))),
        ("DEX volume 24h", _usd(dexv.get("total_24h")), _pct(dexv.get("change_1d_pct"))),
        ("REV 24h", _usd(fees.get("total_24h")),
         f"{_usd(der.get('rev_annualised_usd'))} annualised"),
        ("Active validators", _n(val.get("active")),
         f"{_n(val.get('delinquent'))} delinquent"),
        ("Nakamoto coefficient", _n(val.get("nakamoto_coefficient")),
         f"superminority {_n(val.get('superminority'))}"),
        ("Staked of circulating", _n(der.get("staked_pct_of_circulating"), 2, "%"),
         _usd(der.get("staked_usd"))),
    ]
    for a, b, c in rows:
        A(f"| {a} | {b} | {c} |")
    A("")

    # ------------------------------------------------------------- anomalies
    A("## Anomaly detection")
    A("")
    if anomalies:
        for a in anomalies:
            icon = {"critical": "🔴", "warning": "🟠", "info": "🔵"}.get(a["severity"], "•")
            A(f"- {icon} **{a['severity']}** — {a['message']}")
    else:
        A("No anomalies detected against current baselines.")
    A("")
    A("Baselines are built from locally stored snapshots, so detection sharpens "
      "the longer the tool runs. Absolute safety rules (slot time, delinquency, "
      "large price/TVL moves) fire from the first run.")
    A("")

    # --------------------------------------------------------------- network
    A("## Network performance")
    A("")
    A(f"- **Epoch {net.get('epoch')}** — {_n(net.get('epoch_progress_pct'),1,'%')} "
      f"complete, ends in {der.get('epoch_eta_human', '—')}")
    A(f"- Slot `{_n(net.get('slot'))}` · block height `{_n(net.get('block_height'))}`")
    A(f"- Average slot time (30m): **{_n(net.get('slot_time_avg_30m'),3,'s')}**")
    A(f"- Throughput: **{_n(net.get('tps_avg_30m'))} TPS** total, "
      f"{_n(net.get('tps_nonvote_avg_30m'))} TPS non-vote "
      f"({_n(net.get('vote_share_pct'),1,'%')} of traffic is consensus votes)")
    A(f"- Estimated daily transactions: {_n(der.get('est_daily_transactions'))} "
      f"({_n(der.get('est_daily_nonvote_transactions'))} non-vote)")
    A(f"- Validator client: `{net.get('version')}` · RPC health: `{net.get('health')}`")
    A("")

    # ------------------------------------------------------------ validators
    A("## Validators & decentralisation")
    A("")
    A(f"- **{_n(val.get('active'))} active**, {_n(val.get('delinquent'))} delinquent "
      f"({_n(val.get('delinquent_pct'),2,'%')})")
    A(f"- Total stake: **{_n(val.get('total_stake_sol'))} SOL** "
      f"({_usd(der.get('staked_usd'))})")
    A(f"- **Nakamoto coefficient: {_n(val.get('nakamoto_coefficient'))}** "
      f"— validators needed to control >33% of stake and halt the chain")
    A(f"- Superminority (>50% of stake): {_n(val.get('superminority'))} validators")
    A(f"- Top 10 control {_n(val.get('top10_share_pct'),2,'%')}; "
      f"top 50 control {_n(val.get('top50_share_pct'),2,'%')}")
    A(f"- {_n(val.get('zero_commission_validators'))} validators run 0% commission "
      f"(median commission {_n(val.get('median_commission'),0,'%')})")
    A("")
    top = (val.get("top_validators") or [])[:10]
    if top:
        A("| Vote account | Stake (SOL) | Share | Commission |")
        A("|---|---:|---:|---:|")
        for v in top:
            A(f"| `{v['vote_pubkey'][:24]}…` | {_n(v['stake_sol'])} | "
              f"{_n(v['share_pct'],2,'%')} | {_n(v['commission'],0,'%')} |")
        A("")

    # -------------------------------------------------------------- economic
    A("## Economics")
    A("")
    A(f"- SOL **{_usd(price.get('price_usd'),2)}** "
      f"({_pct(price.get('change_24h_pct'))} 24h, {_pct(price.get('change_7d_pct'))} 7d, "
      f"{_pct(price.get('change_30d_pct'))} 30d)")
    A(f"- Market cap {_usd(price.get('market_cap_usd'))} · "
      f"FDV {_usd(price.get('fdv_usd'))} · {_pct(price.get('ath_change_pct'),1)} from ATH")
    A(f"- **REV (24h): {_usd(fees.get('total_24h'))}**, "
      f"{_usd(der.get('rev_annualised_usd'))} annualised — "
      f"a {_n(der.get('rev_yield_on_stake_pct'),2,'%')} yield on staked value")
    A(f"- Base fee per signature: {_usd(der.get('base_fee_per_signature_usd'),6)} "
      f"· average REV per non-vote txn: {_usd(der.get('avg_rev_per_nonvote_tx_usd'),4)}")
    A(f"- Inflation {_n(sup.get('inflation_total_pct'),2,'%')} → "
      f"nominal staking yield ≈ {_n(der.get('nominal_staking_yield_pct'),2,'%')}")
    A(f"- Stablecoin float on Solana: **{_usd(stab.get('total_usd'))}** "
      f"({_pct(stab.get('change_1d_pct'))} 24h, {_pct(stab.get('change_7d_pct'))} 7d)")
    A("")
    A("> REV uses DefiLlama's Solana fee series — base fees plus priority fees "
      "plus MEV tips. The per-transaction figure is an **average**, not a median: "
      "priority fees are heavily skewed, and a true median needs per-block "
      "sampling that no keyless public endpoint provides.")
    A("")

    # ------------------------------------------------------------------ defi
    A("## DeFi & ecosystem")
    A("")
    A(f"- TVL **{_usd(tvl.get('tvl_usd'))}** "
      f"({_pct(tvl.get('change_1d_pct'))} 24h, {_pct(tvl.get('change_7d_pct'))} 7d, "
      f"{_pct(tvl.get('change_30d_pct'))} 30d) · ATH {_usd(tvl.get('ath_usd'))}")
    A(f"- DEX volume 24h {_usd(dexv.get('total_24h'))} "
      f"→ volume/TVL turnover of {_n(der.get('dex_volume_to_tvl'),2,'x')}")
    A(f"- {_n(prot.get('count'))} protocols tracked with >$1M on Solana")
    A(f"- {_usd(prot.get('excluded_cex_usd'))} of centralised-exchange reserves "
      f"excluded from these rankings — those are custodial balances, not DeFi")
    A("")
    tp = (prot.get("top") or [])[:10]
    if tp:
        A("| Protocol | Category | TVL | 24h | 7d |")
        A("|---|---|---:|---:|---:|")
        for p in tp:
            A(f"| {p['name']} | {p.get('category','—')} | {_usd(p['tvl_usd'])} | "
              f"{_pct(p.get('change_1d_pct'),1)} | {_pct(p.get('change_7d_pct'),1)} |")
        A("")
    cats = (prot.get("by_category") or [])[:6]
    if cats:
        A("**TVL by category:** " + " · ".join(
            f"{c['category']} {_usd(c['tvl_usd'])}" for c in cats))
        A("")

    # ------------------------------------------------------------------- rwa
    rwa = snap.get("rwa") or {}
    if rwa.get("total_usd"):
        A("## Tokenised real-world assets")
        A("")
        A(f"- Total RWA on Solana: **{_usd(rwa['total_usd'])}** across "
          f"{_n(rwa.get('count'))} issuers")
        A(f"- Of which **tokenised equities: {_usd(rwa.get('equities_usd'))}**")
        A("")
        for k in rwa.get("by_kind", []):
            A(f"  - {k['kind']}: {_usd(k['tvl_usd'])}")
        A("")
        A("| Issuer | Type | TVL | 24h |")
        A("|---|---|---:|---:|")
        for i in rwa.get("top", [])[:8]:
            A(f"| {i['name']} | {i['kind']} | {_usd(i['tvl_usd'])} | "
              f"{_pct(i.get('change_1d_pct'),2)} |")
        A("")

    # ------------------------------------------------------------------ news
    items = (snap.get("news") or {}).get("items") or []
    if items:
        A("## Ecosystem news")
        A("")
        for i in items:
            A(f"- [{i['title']}]({i['link']}) — *{i['source']}, {i['age']}*")
        A("")

    # -------------------------------------------------------------- upgrades
    A("## Upcoming upgrades & developments")
    A("")
    for u in snap.get("upgrades", []):
        A(f"- **{u['name']}** ({u['status']}) — {u['summary']} "
          f"*[{u['impact']} · {u['reference']}]*")
    A("")

    # ----------------------------------------------------------------- notes
    errs = meta.get("errors") or {}
    if errs:
        A("## Source warnings")
        A("")
        for k, v in errs.items():
            A(f"- `{k}`: {v}")
        A("")

    A("---")
    A("")
    A(f"Sources: {', '.join(meta.get('sources', []))}. All public endpoints, no API keys. "
      f"RPC used: `{meta.get('rpc_endpoint')}`.")
    return "\n".join(L)
