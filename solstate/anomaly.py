"""Anomaly detection over collected metrics.

Two complementary layers:

  * Absolute rules -- fire from the very first run, encode what operators
    actually care about (chain halts, delinquency spikes, slow slots).
  * Statistical rules -- z-scores against the local baseline, which only
    become meaningful once enough history exists.

A cold start with no history must still produce useful alerts, which is why
the absolute layer exists at all.
"""

SEV_ORDER = {"critical": 0, "warning": 1, "info": 2}

# Thresholds chosen against Solana's normal operating envelope: mainnet runs
# ~0.30-0.45s slots and a few thousand TPS, and delinquency sits near 1-2%.
DEFAULT_RULES = {
    "tps_drop_pct": 40.0,          # vs baseline mean
    "tps_spike_pct": 80.0,
    "slot_time_warn_s": 0.65,      # sustained slots this slow = degraded
    "slot_time_crit_s": 0.90,
    "delinquent_pct_warn": 5.0,
    "delinquent_pct_crit": 10.0,
    "tvl_move_pct": 10.0,          # 1d
    "price_move_pct": 10.0,        # 24h
    "stablecoin_move_pct": 5.0,    # 1d
    "nakamoto_drop": 3,            # absolute drop vs baseline
    "zscore": 3.0,
    # Statistical significance is not the same as mattering. A metric sampled
    # every 10 minutes barely moves between reads, so its standard deviation
    # collapses and a 0.2% wobble scores z=-18. Three guards keep the detector
    # from crying wolf:
    "min_baseline_n": 20,          # too few samples => no trustworthy baseline
    "min_deviation_pct": 8.0,      # must ALSO be a materially large move
    "min_cv": 0.002,               # near-constant series => z is meaningless
}


def _a(metric, severity, message, value=None, baseline=None):
    return {"metric": metric, "severity": severity, "message": message,
            "value": value, "baseline": baseline}


def detect(snap, store, rules=None):
    r = {**DEFAULT_RULES, **(rules or {})}
    out = []
    net = snap.get("network") or {}
    val = snap.get("validators") or {}
    price = snap.get("price") or {}
    tvl = snap.get("tvl") or {}
    stab = snap.get("stablecoins") or {}

    # ------------------------------------------------------- absolute rules
    if net.get("health") and net["health"] != "ok":
        out.append(_a("health", "critical", f"RPC health check failing: {net['health']}"))

    st = net.get("slot_time_avg_30m") or 0
    if st >= r["slot_time_crit_s"]:
        out.append(_a("slot_time", "critical",
                      f"Slot time {st:.3f}s — chain is producing blocks far slower than normal",
                      st, 0.40))
    elif st >= r["slot_time_warn_s"]:
        out.append(_a("slot_time", "warning",
                      f"Slot time elevated at {st:.3f}s (normal ≈0.40s)", st, 0.40))

    dp = val.get("delinquent_pct") or 0
    if dp >= r["delinquent_pct_crit"]:
        out.append(_a("delinquent_pct", "critical",
                      f"{dp:.1f}% of validators delinquent ({val.get('delinquent')} of "
                      f"{val.get('total')})", dp))
    elif dp >= r["delinquent_pct_warn"]:
        out.append(_a("delinquent_pct", "warning",
                      f"Validator delinquency at {dp:.1f}%", dp))

    for key, label, thresh, sect in (
            ("change_1d_pct", "TVL", r["tvl_move_pct"], tvl),
            ("change_24h_pct", "SOL price", r["price_move_pct"], price),
            ("change_1d_pct", "Stablecoin supply", r["stablecoin_move_pct"], stab)):
        v = sect.get(key)
        if isinstance(v, (int, float)) and abs(v) >= thresh:
            out.append(_a(label.lower().replace(" ", "_"),
                          "warning" if abs(v) < thresh * 2 else "critical",
                          f"{label} moved {v:+.1f}% in 24h", v, thresh))

    # ---------------------------------------------------- statistical rules
    checks = [
        ("tps", "TPS", True), ("tps_nonvote", "Non-vote TPS", True),
        ("slot_time", "Slot time", False), ("sol_price", "SOL price", False),
        ("tvl_usd", "TVL", False), ("fees_24h", "Network fees (24h)", False),
        ("dex_volume_24h", "DEX volume (24h)", False),
    ]
    for name, label, directional in checks:
        base = store.baseline(name)
        series = store.series(name, 2)
        if not base or not series or base["stdev"] <= 0:
            continue
        # Not enough history to know what "normal" looks like yet.
        if base["n"] < r["min_baseline_n"]:
            continue
        # Near-constant series: stdev is so small relative to the level that a
        # z-score measures sampling noise, not a real move.
        if base["mean"] and (base["stdev"] / abs(base["mean"])) < r["min_cv"]:
            continue

        cur = series[-1][1]
        z = (cur - base["mean"]) / base["stdev"]
        pct = (cur - base["mean"]) / base["mean"] * 100 if base["mean"] else 0
        # Both tests must pass: statistically unusual AND actually large.
        # Either alone produces noise -- z alone flagged a 0.2% wobble as
        # critical during development.
        if abs(z) < r["zscore"] or abs(pct) < r["min_deviation_pct"]:
            continue

        sev = "critical" if abs(z) > r["zscore"] * 1.8 else "warning"
        direction = "above" if z > 0 else "below"
        out.append(_a(name, sev,
                      f"{label} is {abs(pct):.1f}% {direction} its {base['n']}-sample "
                      f"baseline (z={z:+.1f})", cur, base["mean"]))

    # TPS drop/spike vs baseline, expressed in the operator's own language.
    base = store.baseline("tps")
    if base and base["mean"]:
        cur = net.get("tps_avg_30m") or 0
        pct = (cur - base["mean"]) / base["mean"] * 100
        if pct <= -r["tps_drop_pct"]:
            out.append(_a("tps", "critical",
                          f"Throughput collapsed {abs(pct):.0f}% below baseline "
                          f"({cur:,.0f} vs {base['mean']:,.0f} TPS)", cur, base["mean"]))
        elif pct >= r["tps_spike_pct"]:
            out.append(_a("tps", "info",
                          f"Throughput spiked {pct:.0f}% above baseline "
                          f"({cur:,.0f} vs {base['mean']:,.0f} TPS)", cur, base["mean"]))

    nb = store.baseline("nakamoto")
    if nb and (nb["mean"] - (val.get("nakamoto_coefficient") or 0)) >= r["nakamoto_drop"]:
        out.append(_a("nakamoto", "warning",
                      f"Nakamoto coefficient fell to {val.get('nakamoto_coefficient')} "
                      f"(baseline {nb['mean']:.1f}) — stake is concentrating",
                      val.get("nakamoto_coefficient"), nb["mean"]))

    # De-duplicate by metric, keeping the most severe finding for each.
    best = {}
    for a in out:
        cur = best.get(a["metric"])
        if cur is None or SEV_ORDER[a["severity"]] < SEV_ORDER[cur["severity"]]:
            best[a["metric"]] = a
    return sorted(best.values(), key=lambda a: SEV_ORDER[a["severity"]])
