"""Verify the anomaly detector actually fires.

A detector that returns "all clear" on a healthy chain proves nothing -- it
would also return "all clear" if it were broken. These tests feed it known-bad
states and assert it catches them.

Run:  python tests/test_anomaly.py
"""
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from solstate import anomaly          # noqa: E402
from solstate.store import Store      # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   {detail}" if detail else ""))


def base_snap(**over):
    snap = {
        "meta": {"ts": time.time()},
        "network": {"health": "ok", "tps_avg_30m": 4000.0,
                    "tps_nonvote_avg_30m": 1800.0, "slot_time_avg_30m": 0.40,
                    "epoch": 1024},
        "validators": {"active": 689, "delinquent": 8, "delinquent_pct": 1.1,
                       "nakamoto_coefficient": 18, "total_stake_sol": 436_000_000},
        "price": {"price_usd": 105.0, "change_24h_pct": 1.5},
        "tvl": {"tvl_usd": 5.9e9, "change_1d_pct": -1.8},
        "stablecoins": {"total_usd": 15.9e9, "change_1d_pct": -2.6},
        "fees": {"total_24h": 15_700_000},
        "dex_volume": {"total_24h": 2.59e9},
        "derived": {},
    }
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(snap.get(k), dict):
            snap[k].update(v)
        else:
            snap[k] = v
    return snap


def fresh_store():
    d = tempfile.mkdtemp()
    return Store(Path(d) / "t.db")


def metrics(alerts):
    return {a["metric"] for a in alerts}


print("\n=== absolute rules (must fire with no history at all) ===")

st = fresh_store()
a = anomaly.detect(base_snap(), st)
check("healthy chain produces no alerts", len(a) == 0, f"got {metrics(a)}")

a = anomaly.detect(base_snap(network={"slot_time_avg_30m": 0.95}), fresh_store())
check("critical slot time is caught", any(
    x["metric"] == "slot_time" and x["severity"] == "critical" for x in a))

a = anomaly.detect(base_snap(network={"slot_time_avg_30m": 0.70}), fresh_store())
check("elevated slot time is a warning", any(
    x["metric"] == "slot_time" and x["severity"] == "warning" for x in a))

a = anomaly.detect(base_snap(
    validators={"delinquent": 90, "delinquent_pct": 13.0}), fresh_store())
check("mass validator delinquency is critical", any(
    x["metric"] == "delinquent_pct" and x["severity"] == "critical" for x in a))

a = anomaly.detect(base_snap(network={"health": "node is behind by 400 slots"}),
                   fresh_store())
check("unhealthy RPC is caught", "health" in metrics(a))

a = anomaly.detect(base_snap(price={"change_24h_pct": -22.0}), fresh_store())
check("large price move is caught", "sol_price" in metrics(a), f"got {metrics(a)}")

a = anomaly.detect(base_snap(tvl={"change_1d_pct": -18.0}), fresh_store())
check("large TVL move is caught", "tvl" in metrics(a), f"got {metrics(a)}")


print("\n=== statistical rules (need history) ===")

st = fresh_store()
now = time.time()
# 40 stable snapshots establish a tight baseline.
for i in range(40):
    s = base_snap()
    s["meta"]["ts"] = now - (40 - i) * 600
    s["network"]["tps_avg_30m"] = 4000 + (i % 5) * 20
    st.save(s)

collapsed = base_snap(network={"tps_avg_30m": 900.0})
collapsed["meta"]["ts"] = now
st.save(collapsed)
a = anomaly.detect(collapsed, st)
check("throughput collapse detected against baseline", "tps" in metrics(a),
      f"got {metrics(a)}")
tps_alert = next((x for x in a if x["metric"] == "tps"), None)
check("collapse is rated critical",
      tps_alert is not None and tps_alert["severity"] == "critical",
      tps_alert["message"] if tps_alert else "")

st2 = fresh_store()
for i in range(40):
    s = base_snap()
    s["meta"]["ts"] = now - (40 - i) * 600
    st2.save(s)
normal = base_snap()
normal["meta"]["ts"] = now
st2.save(normal)
a = anomaly.detect(normal, st2)
check("stable history still yields no alerts", len(a) == 0, f"got {metrics(a)}")

print("\n=== baseline hygiene ===")
st3 = fresh_store()
for i in range(10):
    s = base_snap()
    s["meta"]["ts"] = now - (10 - i) * 600
    st3.save(s)
b = st3.baseline("tps")
check("baseline excludes the current reading", b is not None and b["n"] == 9,
      f"n={b['n'] if b else None}")
check("baseline of constant series has zero stdev", b is not None and b["stdev"] == 0)
check("too little history returns no baseline", fresh_store().baseline("tps") is None)

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", ", ".join(FAIL))
sys.exit(1 if FAIL else 0)
