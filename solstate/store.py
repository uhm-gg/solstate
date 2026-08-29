"""Local history store.

Anomaly detection needs a baseline, and none of the public APIs expose the
minute-resolution history we want, so every snapshot is appended here. SQLite
keeps the tool dependency-free and single-file.
"""
import json
import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    ts REAL PRIMARY KEY,
    epoch INTEGER, slot INTEGER,
    payload TEXT
);
CREATE TABLE IF NOT EXISTS metrics (
    ts REAL, name TEXT, value REAL,
    PRIMARY KEY (ts, name)
);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(name, ts);
CREATE TABLE IF NOT EXISTS anomalies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL, metric TEXT, severity TEXT, message TEXT,
    value REAL, baseline REAL
);
"""

# Flattened metrics we track over time for baselines and sparklines.
TRACKED = {
    "tps": ("network", "tps_avg_30m"),
    "tps_nonvote": ("network", "tps_nonvote_avg_30m"),
    "slot_time": ("network", "slot_time_avg_30m"),
    "validators_active": ("validators", "active"),
    "validators_delinquent": ("validators", "delinquent"),
    "delinquent_pct": ("validators", "delinquent_pct"),
    "nakamoto": ("validators", "nakamoto_coefficient"),
    "total_stake_sol": ("validators", "total_stake_sol"),
    "sol_price": ("price", "price_usd"),
    "tvl_usd": ("tvl", "tvl_usd"),
    "stablecoins_usd": ("stablecoins", "total_usd"),
    "dex_volume_24h": ("dex_volume", "total_24h"),
    "fees_24h": ("fees", "total_24h"),
}


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path), timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)
        self.db.commit()

    def save(self, snap):
        ts = snap["meta"]["ts"]
        self.db.execute(
            "INSERT OR REPLACE INTO snapshots(ts,epoch,slot,payload) VALUES(?,?,?,?)",
            (ts, (snap.get("network") or {}).get("epoch"),
             (snap.get("network") or {}).get("slot"), json.dumps(snap)))
        rows = []
        for name, (sect, key) in TRACKED.items():
            v = (snap.get(sect) or {}).get(key)
            if isinstance(v, (int, float)):
                rows.append((ts, name, float(v)))
        self.db.executemany(
            "INSERT OR REPLACE INTO metrics(ts,name,value) VALUES(?,?,?)", rows)
        self.db.commit()
        return len(rows)

    def series(self, name, limit=500):
        return [(r["ts"], r["value"]) for r in self.db.execute(
            "SELECT ts, value FROM metrics WHERE name=? ORDER BY ts DESC LIMIT ?",
            (name, limit)).fetchall()][::-1]

    def baseline(self, name, exclude_last=True, limit=200):
        """Mean and stdev of prior observations, excluding the current one so a
        reading cannot dampen the baseline it is being tested against."""
        vals = [v for _, v in self.series(name, limit)]
        if exclude_last and vals:
            vals = vals[:-1]
        n = len(vals)
        if n < 3:
            return None
        mean = sum(vals) / n
        var = sum((v - mean) ** 2 for v in vals) / n
        return {"n": n, "mean": mean, "stdev": var ** 0.5,
                "min": min(vals), "max": max(vals)}

    def record_anomalies(self, ts, anomalies):
        if not anomalies:
            return
        self.db.executemany(
            "INSERT INTO anomalies(ts,metric,severity,message,value,baseline) "
            "VALUES(?,?,?,?,?,?)",
            [(ts, a["metric"], a["severity"], a["message"],
              a.get("value"), a.get("baseline")) for a in anomalies])
        self.db.commit()

    def recent_anomalies(self, hours=24, limit=50):
        return [dict(r) for r in self.db.execute(
            "SELECT * FROM anomalies WHERE ts > ? ORDER BY id DESC LIMIT ?",
            (time.time() - hours * 3600, limit)).fetchall()]

    def snapshot_count(self):
        return self.db.execute("SELECT COUNT(*) n FROM snapshots").fetchone()["n"]

    def previous(self):
        r = self.db.execute(
            "SELECT payload FROM snapshots ORDER BY ts DESC LIMIT 1 OFFSET 1").fetchone()
        return json.loads(r["payload"]) if r else None
