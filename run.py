#!/usr/bin/env python3
"""solstate — auto-updating Solana ecosystem report.

    python run.py                 # collect once, write all three outputs
    python run.py --watch         # keep refreshing on an interval
    python run.py --interval 600  # set the refresh interval (seconds)
    python run.py --serve         # local web server on 127.0.0.1
    python run.py --json-only     # machine-readable output only

No API keys, no accounts, no configuration required.
"""
import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from solstate.collect import collect                     # noqa: E402
from solstate.store import Store, TRACKED                 # noqa: E402
from solstate import anomaly                              # noqa: E402
from solstate.render import html as render_html           # noqa: E402
from solstate.render import markdown as render_md         # noqa: E402

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
DEFAULT_CONFIG = ROOT / "config.json"


def load_config(path):
    cfg = {
        "interval_seconds": 600,
        "rpc_endpoints": None,
        "top_validators": 20,
        "top_protocols": 15,
        "output_dir": "out",
        "history_db": "out/history.db",
        "html_auto_refresh": True,
        "rules": {},
    }
    p = Path(path)
    if p.exists():
        try:
            cfg.update(json.loads(p.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"[warn] could not read {p}: {e}", file=sys.stderr)
    return cfg


def build(cfg, quiet=False):
    """One full cycle: collect, store, detect, render."""
    out_dir = ROOT / cfg["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    store = Store(ROOT / cfg["history_db"])

    t0 = time.time()
    snap = collect(cfg.get("rpc_endpoints"),
                   cfg.get("top_validators", 20),
                   cfg.get("top_protocols", 15))
    store.save(snap)
    alerts = anomaly.detect(snap, store, cfg.get("rules"))
    store.record_anomalies(snap["meta"]["ts"], alerts)

    history = {name: [v for _, v in store.series(name, 120)] for name in TRACKED}

    snap["anomalies"] = alerts
    snap["meta"]["snapshots_stored"] = store.snapshot_count()

    (out_dir / "data.json").write_text(
        json.dumps(snap, indent=2, default=str), encoding="utf-8")
    (out_dir / "report.md").write_text(
        render_md.render(snap, alerts), encoding="utf-8")
    (out_dir / "dashboard.html").write_text(
        render_html.render(snap, history, alerts,
                           refresh_seconds=cfg["interval_seconds"]
                           if cfg.get("html_auto_refresh") else 0),
        encoding="utf-8")

    if not quiet:
        net = snap.get("network") or {}
        val = snap.get("validators") or {}
        pr = snap.get("price") or {}
        print(f"[{time.strftime('%H:%M:%S')}] epoch {net.get('epoch')} "
              f"· {net.get('tps_avg_30m', 0):,.0f} TPS "
              f"· {val.get('active')} validators ({val.get('delinquent')} delinquent) "
              f"· SOL ${pr.get('price_usd') or 0:,.2f} "
              f"· {len(alerts)} anomalies "
              f"· {time.time()-t0:.1f}s")
        for a in alerts:
            print(f"           {a['severity'].upper():<8} {a['message']}")
        if snap["meta"].get("errors"):
            for k, v in snap["meta"]["errors"].items():
                print(f"           [source warning] {k}: {v}")
    return snap, alerts


def serve(cfg):
    """Serve the output directory on loopback only."""
    import http.server
    import socketserver
    import threading

    out_dir = ROOT / cfg["output_dir"]
    port = int(cfg.get("port", 8800))

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(out_dir), **kw)

        def do_GET(self):
            if self.path in ("/", ""):
                self.path = "/dashboard.html"
            return super().do_GET()

        def log_message(self, *a):
            pass

    def loop():
        while True:
            try:
                build(cfg)
            except Exception:
                traceback.print_exc()
            time.sleep(cfg["interval_seconds"])

    threading.Thread(target=loop, daemon=True).start()
    # Bind to loopback explicitly: this exposes local machine data and must
    # never be reachable from the network.
    with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
        print(f"solstate serving http://127.0.0.1:{port}  "
              f"(refreshing every {cfg['interval_seconds']}s, Ctrl+C to stop)")
        httpd.serve_forever()


def main():
    ap = argparse.ArgumentParser(description="Auto-updating Solana ecosystem report")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--interval", type=int, help="refresh interval in seconds")
    ap.add_argument("--watch", action="store_true", help="run continuously")
    ap.add_argument("--serve", action="store_true", help="serve on 127.0.0.1")
    ap.add_argument("--port", type=int, default=8800)
    ap.add_argument("--json-only", action="store_true")
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.interval:
        cfg["interval_seconds"] = args.interval
    cfg["port"] = args.port

    if args.serve:
        return serve(cfg)

    if args.watch:
        print(f"solstate watching, every {cfg['interval_seconds']}s (Ctrl+C to stop)")
        while True:
            try:
                build(cfg)
            except KeyboardInterrupt:
                return
            except Exception:
                traceback.print_exc()
            time.sleep(cfg["interval_seconds"])

    snap, alerts = build(cfg, quiet=args.json_only)
    if args.json_only:
        print(json.dumps(snap, indent=2, default=str))
    else:
        out = ROOT / cfg["output_dir"]
        print(f"\nwrote {out / 'dashboard.html'}")
        print(f"      {out / 'report.md'}")
        print(f"      {out / 'data.json'}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstopped")
