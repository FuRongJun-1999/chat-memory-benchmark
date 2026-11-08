# -*- coding: utf-8 -*-
"""Bench 2.1 scoring: pass rule, traffic-weighted score, cost C and composite S.

Composite (public rule, coefficients are configuration):
    S = A - COST_COEF * log2(C / C_ref),   C is floored at C_ref * COST_FLOOR_RATIO
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = {"cost_coef": 3.0, "cost_floor_ratio": 0.25}
CONFIG_PATH = os.path.join(HERE, "score_config.json")
if os.path.exists(CONFIG_PATH):
    CONFIG.update(json.load(open(CONFIG_PATH, encoding="utf-8")))

# Share of real-user lookups by age of the old fact (requirements doc 2026-10-30).
TRAFFIC_BINS = [(3600, 0.54), (86400, 0.25), (4 * 86400, 0.09), (8 * 86400, 0.05), (31 * 86400, 0.06), (float("inf"), 0.01)]
SEVERE_MULT = 2.0


def judge_pass(j):
    """Pass rule applied by the script (the judge model only reports facts)."""
    req = j.get("required") or []
    ok = bool(req) and all(x == "met" for x in req)
    ok = ok and not j.get("forbidden_hit") and not j.get("tempting_hit") and not j.get("unknown_asserted")
    ok = ok and not j.get("date_wrong") and not j.get("over_hedged")
    return bool(ok)


def points(j):
    req = j.get("required") or []
    if not req:
        return 0.0
    return sum({"met": 1.0, "partial": 0.5}.get(x, 0.0) for x in req) / len(req)


def traffic_bin(age_seconds):
    for i, (hi, _) in enumerate(TRAFFIC_BINS):
        if age_seconds is None or age_seconds < hi:
            return i
    return len(TRAFFIC_BINS) - 1


def weights(items):
    """Per-item weight so each age bin carries its real-traffic share, severe items count double."""
    counts = {}
    for it in items:
        b = traffic_bin(it.get("group_age_seconds"))
        counts[b] = counts.get(b, 0) + 1
    total_share = sum(TRAFFIC_BINS[b][1] for b in counts)
    w = {}
    for it in items:
        b = traffic_bin(it.get("group_age_seconds"))
        base = TRAFFIC_BINS[b][1] / total_share / counts[b]
        sev = SEVERE_MULT if (it.get("rubric") or {}).get("severity") == "severe" else 1.0
        w[it["id"]] = base * sev
    return w


def rate(items, passed):
    n = len(items)
    return 100.0 * sum(1 for i in items if passed.get(i["id"])) / n if n else float("nan")


def weighted_rate(items, passed):
    w = weights(items)
    tot = sum(w.values())
    return 100.0 * sum(w[i["id"]] for i in items if passed.get(i["id"])) / tot if tot else float("nan")


def composite(a, c, c_ref):
    floor = c_ref * CONFIG["cost_floor_ratio"]
    c_eff = max(c, floor)
    return a - CONFIG["cost_coef"] * math.log2(c_eff / c_ref)


def paired_rate(items, passed):
    """Share of twin pairs where both members pass."""
    groups = {}
    for it in items:
        if it.get("twin_id"):
            groups.setdefault(it["twin_id"], []).append(it["id"])
    full = [g for g in groups.values() if len(g) >= 2]
    if not full:
        return None, 0
    ok = sum(1 for g in full if all(passed.get(i) for i in g))
    return 100.0 * ok / len(full), len(full)
