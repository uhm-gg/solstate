"""Interactive dark-theme HTML dashboard.

Self-contained by design: no CDN, no build step, no external fonts. The file
opens from disk with a double-click and works offline, which matters because
the brief asks for something low-maintenance with no API keys or dependencies.
Charts are hand-rolled inline SVG for the same reason.
"""
import html
import json


def _e(s):
    return html.escape(str(s if s is not None else "—"))


def _n(v, dp=0, pre="", suf=""):
    if v is None or not isinstance(v, (int, float)):
        return "—"
    return f"{pre}{v:,.{dp}f}{suf}"


def _usd(v, dp=0):
    if v is None or not isinstance(v, (int, float)):
        return "—"
    a = abs(v)
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= div:
            return f"${v/div:,.2f}{suf}"
    return f"${v:,.{dp}f}"


def _delta(v, dp=2):
    if v is None or not isinstance(v, (int, float)):
        return '<span class="d flat">—</span>'
    cls = "up" if v > 0 else ("down" if v < 0 else "flat")
    arrow = "▲" if v > 0 else ("▼" if v < 0 else "·")
    return f'<span class="d {cls}">{arrow} {abs(v):.{dp}f}%</span>'


def _sparkline(points, w=260, h=44, stroke="#14f195"):
    """Inline SVG sparkline. Returns empty string when there is nothing to draw
    rather than a misleading flat line."""
    vals = [p for p in points if isinstance(p, (int, float))]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    step = w / (len(vals) - 1)
    pts = [(i * step, h - 3 - ((v - lo) / rng) * (h - 6)) for i, v in enumerate(vals)]
    d = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
    area = d + f" L{w:.1f},{h} L0,{h} Z"
    uid = abs(hash(tuple(vals[:12]))) % 100000
    return (f'<svg class="spark" viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
            f'<defs><linearGradient id="g{uid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0%" stop-color="{stroke}" stop-opacity=".28"/>'
            f'<stop offset="100%" stop-color="{stroke}" stop-opacity="0"/>'
            f'</linearGradient></defs>'
            f'<path d="{area}" fill="url(#g{uid})"/>'
            f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="1.6" '
            f'stroke-linejoin="round"/></svg>')


def _bar_rows(items, label_key, value_key, fmt=_usd, limit=10):
    items = items[:limit]
    if not items:
        return '<div class="empty">no data</div>'
    top = max((i.get(value_key) or 0) for i in items) or 1
    out = []
    for i in items:
        v = i.get(value_key) or 0
        pct = v / top * 100
        out.append(
            f'<div class="bar"><div class="bl">{_e(i.get(label_key))}</div>'
            f'<div class="bt"><div class="bf" style="width:{pct:.1f}%"></div></div>'
            f'<div class="bv">{fmt(v)}</div></div>')
    return "".join(out)


def render(snap, history=None, anomalies=None, refresh_seconds=0):
    history = history or {}
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

    sev_counts = {}
    for a in anomalies:
        sev_counts[a["severity"]] = sev_counts.get(a["severity"], 0) + 1
    banner_cls = ("critical" if sev_counts.get("critical") else
                  "warning" if sev_counts.get("warning") else "ok")
    banner_txt = ("All monitored metrics within normal range"
                  if not anomalies else
                  " · ".join(f"{n} {s}" for s, n in sorted(sev_counts.items())))

    # -------------------------------------------------------------- KPI tiles
    epoch_pct = net.get("epoch_progress_pct") or 0
    tiles = [
        ("SOL price", _usd(price.get("price_usd"), 2), _delta(price.get("change_24h_pct")),
         history.get("sol_price"), "#14f195"),
        ("Network TPS", _n(net.get("tps_avg_30m"), 0),
         f'<span class="sub">{_n(net.get("tps_nonvote_avg_30m"),0)} non-vote</span>',
         history.get("tps"), "#9945ff"),
        ("Total value locked", _usd(tvl.get("tvl_usd")), _delta(tvl.get("change_1d_pct")),
         history.get("tvl_usd"), "#14f195"),
        ("DEX volume 24h", _usd(dexv.get("total_24h")), _delta(dexv.get("change_1d_pct")),
         history.get("dex_volume_24h"), "#00d1ff"),
        ("Stablecoin float", _usd(stab.get("total_usd")), _delta(stab.get("change_1d_pct")),
         history.get("stablecoins_usd"), "#00d1ff"),
        ("REV 24h", _usd(fees.get("total_24h")),
         f'<span class="sub">{_usd(der.get("rev_annualised_usd"))} annualised</span>',
         history.get("fees_24h"), "#ffb01f"),
        ("Active validators", _n(val.get("active")),
         (f'<span class="d down">{val.get("delinquent")} delinquent</span>'
          if (val.get("delinquent") or 0) else '<span class="d up">0 delinquent</span>'),
         history.get("validators_active"), "#9945ff"),
        ("Nakamoto coefficient", _n(val.get("nakamoto_coefficient")),
         f'<span class="sub">superminority {_n(val.get("superminority"))}</span>',
         history.get("nakamoto"), "#ffb01f"),
    ]
    tile_html = "".join(
        f'<div class="tile"><div class="tl">{_e(lab)}</div>'
        f'<div class="tv">{v}</div><div class="tm">{sub}</div>'
        f'{_sparkline(hist or [], stroke=col)}</div>'
        for lab, v, sub, hist, col in tiles)

    # ------------------------------------------------------------- anomalies
    if anomalies:
        an_html = "".join(
            f'<div class="an {_e(a["severity"])}"><span class="pill">{_e(a["severity"])}</span>'
            f'<span>{_e(a["message"])}</span></div>' for a in anomalies)
    else:
        an_html = ('<div class="an ok"><span class="pill">clear</span>'
                   '<span>No anomalies detected against current baselines.</span></div>')

    # ------------------------------------------------------------ validators
    tv_rows = "".join(
        f'<tr><td class="mono">{_e(v["vote_pubkey"][:20])}…</td>'
        f'<td class="r">{_n(v["stake_sol"],0)}</td>'
        f'<td class="r">{_n(v["share_pct"],2,suf="%")}</td>'
        f'<td class="r">{_n(v["commission"],0,suf="%")}</td></tr>'
        for v in (val.get("top_validators") or [])[:12])

    delq = val.get("delinquent_validators") or []
    delq_html = ("".join(
        f'<tr><td class="mono">{_e(v["vote_pubkey"][:20])}…</td>'
        f'<td class="r">{_n(v["stake_sol"],0)} SOL</td></tr>' for v in delq[:8])
        or '<tr><td colspan="2" class="empty">none</td></tr>')

    # -------------------------------------------------------------- upgrades
    up_html = "".join(
        f'<div class="up-item"><div class="up-h"><b>{_e(u["name"])}</b>'
        f'<span class="tag">{_e(u["status"])}</span></div>'
        f'<div class="sub">{_e(u["summary"])}</div>'
        f'<div class="ref">{_e(u["impact"])} · {_e(u["reference"])}</div></div>'
        for u in snap.get("upgrades", []))

    errs = meta.get("errors") or {}
    err_html = ""
    if errs:
        err_html = ('<div class="card"><h2>Source warnings</h2>' + "".join(
            f'<div class="an warning"><span class="pill">{_e(k)}</span>'
            f'<span>{_e(v)}</span></div>' for k, v in errs.items()) + "</div>")

    refresh_meta = (f'<meta http-equiv="refresh" content="{refresh_seconds}">'
                    if refresh_seconds else "")

    return TEMPLATE.format(
        refresh=refresh_meta,
        generated=_e(meta.get("generated_at")),
        version=_e(meta.get("version")),
        collect_s=_n(meta.get("collect_seconds"), 2),
        rpc=_e(meta.get("rpc_endpoint")),
        banner_cls=banner_cls, banner_txt=_e(banner_txt),
        tiles=tile_html, anomalies=an_html,
        epoch=_e(net.get("epoch")), epoch_pct=f"{epoch_pct:.1f}",
        epoch_eta=_e(der.get("epoch_eta_human")),
        slot=_n(net.get("slot")), block_height=_n(net.get("block_height")),
        slot_time=_n(net.get("slot_time_avg_30m"), 3, suf="s"),
        vote_share=_n(net.get("vote_share_pct"), 1, suf="%"),
        client=_e(net.get("version")),
        daily_tx=_n(der.get("est_daily_transactions"), 0),
        daily_nv=_n(der.get("est_daily_nonvote_transactions"), 0),
        base_fee=_usd(der.get("base_fee_per_signature_usd"), 6),
        avg_rev_tx=_usd(der.get("avg_rev_per_nonvote_tx_usd"), 4),
        staked_pct=_n(der.get("staked_pct_of_circulating"), 2, suf="%"),
        staked_usd=_usd(der.get("staked_usd")),
        stake_yield=_n(der.get("nominal_staking_yield_pct"), 2, suf="%"),
        rev_yield=_n(der.get("rev_yield_on_stake_pct"), 2, suf="%"),
        inflation=_n(sup.get("inflation_total_pct"), 2, suf="%"),
        circ=_n(sup.get("circulating_sol"), 0),
        total_sol=_n(sup.get("total_sol"), 0),
        mcap=_usd(price.get("market_cap_usd")),
        fdv=_usd(price.get("fdv_usd")),
        rank=_n(price.get("market_cap_rank")),
        ath_off=_n(price.get("ath_change_pct"), 1, suf="%"),
        vol24=_usd(price.get("volume_24h_usd")),
        chg7=_delta(price.get("change_7d_pct")),
        chg30=_delta(price.get("change_30d_pct")),
        tvl_7d=_delta(tvl.get("change_7d_pct")),
        tvl_30d=_delta(tvl.get("change_30d_pct")),
        tvl_ath=_usd(tvl.get("ath_usd")),
        dex_tvl=_n(der.get("dex_volume_to_tvl"), 2, suf="x"),
        stab_tvl=_n(der.get("stablecoin_to_tvl_ratio"), 2, suf="x"),
        top_validators=tv_rows, delinquent=delq_html,
        protocol_bars=_bar_rows(prot.get("top") or [], "name", "tvl_usd"),
        category_bars=_bar_rows(prot.get("by_category") or [], "category", "tvl_usd", limit=8),
        dex_bars=_bar_rows(dexv.get("top") or [], "name", "total_24h", limit=8),
        fee_bars=_bar_rows(fees.get("top") or [], "name", "total_24h", limit=8),
        protocol_count=_n(prot.get("count")),
        cex_excluded=_usd(prot.get("excluded_cex_usd")),
        upgrades=up_html, errors=err_html,
        tvl_chart=_sparkline([h["tvl"] for h in (tvl.get("history") or [])],
                             w=680, h=90, stroke="#14f195"),
        stab_chart=_sparkline([h["total"] for h in (stab.get("history") or [])],
                              w=680, h=90, stroke="#00d1ff"),
        tps_chart=_sparkline([s["tps"] for s in reversed(net.get("samples") or [])],
                             w=680, h=90, stroke="#9945ff"),
        payload=json.dumps({"meta": meta, "derived": der}, default=str),
    )


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Solana Ecosystem Report</title>{refresh}
<style>
:root{{--bg:#07090c;--panel:#0e1218;--panel2:#141a22;--line:#1e2732;--fg:#e8edf4;
--dim:#7d8b9c;--grn:#14f195;--pur:#9945ff;--cy:#00d1ff;--amb:#ffb01f;--red:#ff4d6a;}}
*{{box-sizing:border-box}}
body{{margin:0;background:radial-gradient(1200px 600px at 15% -10%,#101a2b 0%,var(--bg) 55%);
color:var(--fg);font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif;
-webkit-font-smoothing:antialiased}}
a{{color:var(--cy)}}
.wrap{{max-width:1360px;margin:0 auto;padding:26px 22px 70px}}
header{{display:flex;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:6px}}
h1{{margin:0;font-size:23px;letter-spacing:-.4px;font-weight:700}}
h1 .g{{background:linear-gradient(90deg,var(--grn),var(--cy),var(--pur));
-webkit-background-clip:text;background-clip:text;color:transparent}}
.meta{{color:var(--dim);font-size:12px;margin-left:auto;text-align:right;line-height:1.7}}
.mono{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px}}
.banner{{margin:16px 0 20px;padding:11px 15px;border-radius:10px;font-weight:600;
border:1px solid;display:flex;gap:10px;align-items:center}}
.banner.ok{{background:rgba(20,241,149,.07);border-color:rgba(20,241,149,.3);color:var(--grn)}}
.banner.warning{{background:rgba(255,176,31,.08);border-color:rgba(255,176,31,.35);color:var(--amb)}}
.banner.critical{{background:rgba(255,77,106,.09);border-color:rgba(255,77,106,.4);color:var(--red)}}
.grid{{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(232px,1fr));margin-bottom:18px}}
.tile{{background:linear-gradient(160deg,var(--panel2),var(--panel));border:1px solid var(--line);
border-radius:13px;padding:14px 15px 8px;position:relative;overflow:hidden}}
.tl{{color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:.9px;font-weight:600}}
.tv{{font-size:26px;font-weight:700;margin:5px 0 2px;letter-spacing:-.5px}}
.tm{{font-size:12px;min-height:18px}}
.spark{{display:block;width:100%;height:44px;margin-top:4px}}
.d{{font-weight:600;font-size:12px}}
.d.up{{color:var(--grn)}} .d.down{{color:var(--red)}} .d.flat{{color:var(--dim)}}
.sub{{color:var(--dim);font-size:12px}}
.cols{{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(340px,1fr))}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:13px;padding:16px 18px}}
.card.wide{{grid-column:1/-1}}
.card h2{{margin:0 0 13px;font-size:11.5px;text-transform:uppercase;letter-spacing:1.1px;
color:var(--dim);font-weight:700}}
.kv{{display:flex;justify-content:space-between;gap:14px;padding:6px 0;
border-bottom:1px solid rgba(255,255,255,.045);font-size:13px}}
.kv:last-child{{border-bottom:0}}
.kv span:first-child{{color:var(--dim)}}
.kv b{{font-weight:600}}
table{{width:100%;border-collapse:collapse;font-size:12.5px}}
th{{text-align:left;color:var(--dim);font-size:10.5px;text-transform:uppercase;
letter-spacing:.7px;padding:0 8px 7px 0;border-bottom:1px solid var(--line)}}
td{{padding:6px 8px 6px 0;border-bottom:1px solid rgba(255,255,255,.04)}}
td.r,th.r{{text-align:right}}
.bar{{display:grid;grid-template-columns:132px 1fr 92px;gap:10px;align-items:center;
padding:4px 0;font-size:12.5px}}
.bl{{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#c6d2e0}}
.bt{{background:#0a0e13;border-radius:5px;height:9px;overflow:hidden}}
.bf{{height:100%;background:linear-gradient(90deg,var(--pur),var(--cy));border-radius:5px}}
.bv{{text-align:right;color:var(--dim);font-variant-numeric:tabular-nums}}
.an{{display:flex;gap:11px;align-items:flex-start;padding:9px 0;
border-bottom:1px solid rgba(255,255,255,.045);font-size:13px}}
.an:last-child{{border-bottom:0}}
.pill{{font-size:10px;text-transform:uppercase;letter-spacing:.7px;padding:2px 8px;
border-radius:99px;font-weight:700;flex-shrink:0;border:1px solid}}
.an.critical .pill{{color:var(--red);border-color:var(--red);background:rgba(255,77,106,.1)}}
.an.warning .pill{{color:var(--amb);border-color:var(--amb);background:rgba(255,176,31,.1)}}
.an.info .pill{{color:var(--cy);border-color:var(--cy);background:rgba(0,209,255,.1)}}
.an.ok .pill{{color:var(--grn);border-color:var(--grn);background:rgba(20,241,149,.1)}}
.prog{{height:8px;background:#0a0e13;border-radius:99px;overflow:hidden;margin:9px 0 5px}}
.prog i{{display:block;height:100%;background:linear-gradient(90deg,var(--grn),var(--cy))}}
.up-item{{padding:10px 0;border-bottom:1px solid rgba(255,255,255,.045)}}
.up-item:last-child{{border-bottom:0}}
.up-h{{display:flex;gap:9px;align-items:center;margin-bottom:3px}}
.tag{{font-size:10px;color:var(--pur);border:1px solid rgba(153,69,255,.45);
background:rgba(153,69,255,.1);padding:1px 7px;border-radius:99px}}
.ref{{color:#5e6b7c;font-size:11px;margin-top:3px;font-family:ui-monospace,monospace}}
.empty{{color:var(--dim);font-size:12.5px;padding:8px 0}}
footer{{margin-top:26px;color:var(--dim);font-size:11.5px;text-align:center;line-height:1.9}}
@media(max-width:640px){{.tv{{font-size:22px}}.bar{{grid-template-columns:96px 1fr 74px}}}}
</style></head><body><div class="wrap">
<header>
  <h1>Solana <span class="g">Ecosystem Report</span></h1>
  <div class="meta">generated {generated} · v{version}<br>
    collected in {collect_s}s via <span class="mono">{rpc}</span></div>
</header>

<div class="banner {banner_cls}"><b>Status</b> — {banner_txt}</div>

<div class="grid">{tiles}</div>

<div class="cols">
  <div class="card wide"><h2>Anomaly detection</h2>{anomalies}</div>

  <div class="card"><h2>Network</h2>
    <div class="kv"><span>Epoch</span><b>{epoch} · {epoch_pct}%</b></div>
    <div class="prog"><i style="width:{epoch_pct}%"></i></div>
    <div class="kv"><span>Epoch ends in</span><b>{epoch_eta}</b></div>
    <div class="kv"><span>Slot</span><b>{slot}</b></div>
    <div class="kv"><span>Block height</span><b>{block_height}</b></div>
    <div class="kv"><span>Avg slot time (30m)</span><b>{slot_time}</b></div>
    <div class="kv"><span>Vote share of txns</span><b>{vote_share}</b></div>
    <div class="kv"><span>Validator client</span><b>{client}</b></div>
    <div class="kv"><span>Est. daily txns</span><b>{daily_tx}</b></div>
    <div class="kv"><span>Est. daily non-vote</span><b>{daily_nv}</b></div>
  </div>

  <div class="card"><h2>Economics</h2>
    <div class="kv"><span>Market cap</span><b>{mcap}</b></div>
    <div class="kv"><span>Fully diluted</span><b>{fdv}</b></div>
    <div class="kv"><span>Market cap rank</span><b>#{rank}</b></div>
    <div class="kv"><span>24h spot volume</span><b>{vol24}</b></div>
    <div class="kv"><span>7d / 30d price</span><b>{chg7} &nbsp; {chg30}</b></div>
    <div class="kv"><span>Off all-time high</span><b>{ath_off}</b></div>
    <div class="kv"><span>Base fee / signature</span><b>{base_fee}</b></div>
    <div class="kv"><span>Avg REV / non-vote txn</span><b>{avg_rev_tx}</b></div>
  </div>

  <div class="card"><h2>Staking &amp; supply</h2>
    <div class="kv"><span>Staked of circulating</span><b>{staked_pct}</b></div>
    <div class="kv"><span>Stake value</span><b>{staked_usd}</b></div>
    <div class="kv"><span>Nominal staking yield</span><b>{stake_yield}</b></div>
    <div class="kv"><span>REV yield on stake</span><b>{rev_yield}</b></div>
    <div class="kv"><span>Inflation rate</span><b>{inflation}</b></div>
    <div class="kv"><span>Circulating SOL</span><b>{circ}</b></div>
    <div class="kv"><span>Total SOL</span><b>{total_sol}</b></div>
  </div>

  <div class="card"><h2>DeFi ratios</h2>
    <div class="kv"><span>TVL 7d / 30d</span><b>{tvl_7d} &nbsp; {tvl_30d}</b></div>
    <div class="kv"><span>TVL all-time high</span><b>{tvl_ath}</b></div>
    <div class="kv"><span>DEX volume / TVL</span><b>{dex_tvl}</b></div>
    <div class="kv"><span>Stablecoins / TVL</span><b>{stab_tvl}</b></div>
    <div class="kv"><span>Protocols tracked</span><b>{protocol_count}</b></div>
    <div class="kv"><span>CEX reserves excluded</span><b>{cex_excluded}</b></div>
  </div>

  <div class="card wide"><h2>Total value locked — 90 days</h2>{tvl_chart}</div>
  <div class="card wide"><h2>Stablecoin float — 90 days</h2>{stab_chart}</div>
  <div class="card wide"><h2>Throughput — last 30 performance samples</h2>{tps_chart}</div>

  <div class="card"><h2>Top protocols by TVL</h2>{protocol_bars}</div>
  <div class="card"><h2>TVL by category</h2>{category_bars}</div>
  <div class="card"><h2>DEX volume 24h</h2>{dex_bars}</div>
  <div class="card"><h2>Fees / REV 24h</h2>{fee_bars}</div>

  <div class="card wide"><h2>Largest validators by stake</h2>
    <table><tr><th>vote account</th><th class="r">stake (SOL)</th>
    <th class="r">share</th><th class="r">commission</th></tr>{top_validators}</table>
  </div>

  <div class="card"><h2>Delinquent validators</h2>
    <table><tr><th>vote account</th><th class="r">stake</th></tr>{delinquent}</table>
  </div>

  <div class="card"><h2>Upcoming upgrades</h2>{upgrades}</div>
  {errors}
</div>

<footer>
  Data: Solana JSON-RPC · DefiLlama · CoinGecko — all public, no API keys.<br>
  Anomaly baselines are computed from locally stored history, so they sharpen
  as the tool keeps running.
</footer>
</div>
<script id="solstate-meta" type="application/json">{payload}</script>
</body></html>"""
