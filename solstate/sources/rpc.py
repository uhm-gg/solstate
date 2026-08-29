"""Solana JSON-RPC collector.

Uses only public, keyless endpoints and fails over between them, because the
whole point of this tool is that it runs with zero configuration and zero
accounts. Endpoints that started demanding keys (Ankr, dRPC) are deliberately
not in the default list.
"""
import time

from solstate.http import post_json

DEFAULT_ENDPOINTS = [
    "https://api.mainnet-beta.solana.com",
    "https://solana-rpc.publicnode.com",
]


class RpcError(RuntimeError):
    pass


class SolanaRpc:
    def __init__(self, endpoints=None, timeout=25):
        self.endpoints = list(endpoints or DEFAULT_ENDPOINTS)
        self.timeout = timeout
        self.last_used = None
        self.failures = {}

    def call(self, method, params=None):
        """Try each endpoint in turn; raise only if every one fails."""
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
        errors = []
        for ep in self.endpoints:
            try:
                d = post_json(ep, body, timeout=self.timeout, retries=2)
                if "error" in d:
                    raise RpcError(str(d["error"])[:160])
                self.last_used = ep
                return d["result"]
            except Exception as e:
                self.failures[ep] = str(e)[:160]
                errors.append(f"{ep}: {type(e).__name__}: {str(e)[:100]}")
        raise RpcError(f"all endpoints failed for {method} -- " + " | ".join(errors))

    # -------------------------------------------------------------- network
    def network(self):
        t0 = time.time()
        epoch = self.call("getEpochInfo")
        perf = self.call("getRecentPerformanceSamples", [30])
        health = "ok"
        try:
            self.call("getHealth")
        except Exception as e:
            health = str(e)[:80]
        version = self.call("getVersion")

        # Each sample covers samplePeriodSecs of real time.
        tps = tps_nonvote = slot_time = 0.0
        if perf:
            s = perf[0]
            secs = s.get("samplePeriodSecs") or 60
            tps = s.get("numTransactions", 0) / secs
            tps_nonvote = s.get("numNonVoteTransactions", 0) / secs
            slot_time = secs / s["numSlots"] if s.get("numSlots") else 0.0

        # A longer window smooths the spikiness of a single 60s sample.
        span_tx = sum(s.get("numTransactions", 0) for s in perf)
        span_nv = sum(s.get("numNonVoteTransactions", 0) for s in perf)
        span_slots = sum(s.get("numSlots", 0) for s in perf)
        span_secs = sum(s.get("samplePeriodSecs") or 60 for s in perf) or 1

        slots_left = epoch["slotsInEpoch"] - epoch["slotIndex"]
        avg_slot = (span_secs / span_slots) if span_slots else 0.4

        return {
            "health": health,
            "version": version.get("solana-core"),
            "feature_set": version.get("feature-set"),
            "endpoint": self.last_used,
            "slot": epoch["absoluteSlot"],
            "block_height": epoch["blockHeight"],
            "epoch": epoch["epoch"],
            "slot_index": epoch["slotIndex"],
            "slots_in_epoch": epoch["slotsInEpoch"],
            "epoch_progress_pct": epoch["slotIndex"] / epoch["slotsInEpoch"] * 100,
            "epoch_eta_seconds": slots_left * avg_slot,
            "transaction_count": epoch.get("transactionCount"),
            "tps": tps,
            "tps_nonvote": tps_nonvote,
            "tps_avg_30m": span_tx / span_secs,
            "tps_nonvote_avg_30m": span_nv / span_secs,
            "slot_time_s": slot_time,
            "slot_time_avg_30m": avg_slot,
            "vote_share_pct": (1 - span_nv / span_tx) * 100 if span_tx else 0.0,
            "samples": [
                {"slot": s["slot"], "tps": s.get("numTransactions", 0) / (s.get("samplePeriodSecs") or 60),
                 "tps_nonvote": s.get("numNonVoteTransactions", 0) / (s.get("samplePeriodSecs") or 60),
                 "slot_time": (s.get("samplePeriodSecs") or 60) / s["numSlots"] if s.get("numSlots") else 0}
                for s in perf
            ],
            "collect_ms": round((time.time() - t0) * 1000),
        }

    # ------------------------------------------------------------ validators
    def validators(self, top_n=20):
        t0 = time.time()
        va = self.call("getVoteAccounts")
        cur, delq = va.get("current", []), va.get("delinquent", [])
        stakes = sorted((v["activatedStake"] / 1e9 for v in cur + delq), reverse=True)
        total = sum(stakes)

        # Nakamoto coefficient: how few validators it takes to halt the chain
        # (>33% of stake). The single most honest decentralisation number.
        nakamoto, run = 0, 0.0
        for s in stakes:
            run += s
            nakamoto += 1
            if total and run > total / 3:
                break

        top = sorted(cur, key=lambda v: -v["activatedStake"])[:top_n]
        superminority, run = 0, 0.0
        for s in stakes:
            run += s
            superminority += 1
            if total and run > total * 0.5:
                break

        zero_comm = sum(1 for v in cur if v.get("commission") == 0)
        comms = [v.get("commission", 0) for v in cur]

        return {
            "active": len(cur),
            "delinquent": len(delq),
            "total": len(cur) + len(delq),
            "delinquent_pct": len(delq) / max(1, len(cur) + len(delq)) * 100,
            "total_stake_sol": total,
            "delinquent_stake_sol": sum(v["activatedStake"] for v in delq) / 1e9,
            "nakamoto_coefficient": nakamoto,
            "superminority": superminority,
            "top1_share_pct": (stakes[0] / total * 100) if total and stakes else 0,
            "top10_share_pct": (sum(stakes[:10]) / total * 100) if total else 0,
            "top50_share_pct": (sum(stakes[:50]) / total * 100) if total else 0,
            "zero_commission_validators": zero_comm,
            "median_commission": sorted(comms)[len(comms) // 2] if comms else 0,
            "top_validators": [
                {"vote_pubkey": v["votePubkey"], "node_pubkey": v.get("nodePubkey"),
                 "stake_sol": v["activatedStake"] / 1e9,
                 "share_pct": v["activatedStake"] / 1e9 / total * 100 if total else 0,
                 "commission": v.get("commission"),
                 "epoch_credits": (v.get("epochCredits") or [[0, 0, 0]])[-1][1]}
                for v in top
            ],
            "delinquent_validators": [
                {"vote_pubkey": v["votePubkey"], "stake_sol": v["activatedStake"] / 1e9}
                for v in sorted(delq, key=lambda v: -v["activatedStake"])[:10]
            ],
            "collect_ms": round((time.time() - t0) * 1000),
        }

    # ---------------------------------------------------------------- supply
    def supply(self):
        s = self.call("getSupply", [{"excludeNonCirculatingAccountsList": True}])["value"]
        infl = self.call("getInflationRate")
        circ, non = s["circulating"] / 1e9, s["nonCirculating"] / 1e9
        return {
            "total_sol": s["total"] / 1e9,
            "circulating_sol": circ,
            "non_circulating_sol": non,
            "circulating_pct": circ / (circ + non) * 100 if (circ + non) else 0,
            "inflation_total_pct": infl.get("total", 0) * 100,
            "inflation_validator_pct": infl.get("validator", 0) * 100,
            "inflation_epoch": infl.get("epoch"),
        }
