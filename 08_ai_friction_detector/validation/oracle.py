"""Independent re-implementation of the friction rules in plain Python (no pandas, no engine imports).

Purpose: validate the vectorised engine. It follows the written rules in docs/RULES_AND_SCORING.md
and iterates customer by customer, so a bug in the vectorised code would have to be repeated here
to go unnoticed. It reads the raw CSVs directly.
"""
from __future__ import annotations

import csv
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

PRECEDENCE = ["KYC_PENDING", "BANK_LINK_PENDING", "FIRST_DEPOSIT_PENDING", "FIRST_TRADE_PENDING",
              "INACTIVITY_RISK", "SUPPORT_UNRESOLVED", "REPEATED_SUPPORT_ISSUES"]
JOURNEY_CAT = ["KYC_PENDING", "BANK_LINK_PENDING", "FIRST_DEPOSIT_PENDING", "FIRST_TRADE_PENDING"]
STAGE_PTS = [4, 8, 12, 20, 16]


def _d(s):
    s = (s or "").strip()
    return datetime.strptime(s[:10], "%Y-%m-%d").date() if s else None


def _f(s, default=0.0):
    try:
        return float(s) if str(s).strip() != "" else default
    except ValueError:
        return default


def quantile(vals, q):
    v = sorted(vals)
    if not v:
        return None
    pos = (len(v) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def load(data_dir):
    data_dir = Path(data_dir)
    with open(data_dir / "users.csv", newline="") as fh:
        users = list(csv.DictReader(fh))
    with open(data_dir / "tickets.csv", newline="") as fh:
        tickets = list(csv.DictReader(fh))
    monthly = defaultdict(list)
    with open(data_dir / "monthly_activity.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            monthly[r["user_id"]].append(r)
    return users, tickets, monthly


def run(data_dir, as_of_str):
    as_of = _d(as_of_str)
    users, tickets, monthly = load(data_dir)
    for u in users:
        for c in ("registration_date", "kyc_date_asof", "bank_date_asof", "deposit_date_asof", "trade_date_asof",
                  "last_active_date_adj"):
            u[c] = _d(u[c])

    # ---- windows derived from ALL users (full dataset), like the engine
    pairs = [("registration_date", "kyc_date_asof"), ("kyc_date_asof", "bank_date_asof"),
             ("bank_date_asof", "deposit_date_asof"), ("deposit_date_asof", "trade_date_asof")]
    windows = []
    for a, b in pairs:
        lags = [(u[b] - u[a]).days for u in users if u[a] and u[b] and (u[b] - u[a]).days >= 0]
        windows.append(max(int(math.ceil(quantile(lags, 0.95))), 3))
    deps = sorted(_f(u["first_deposit_amount_asof_inr"]) for u in users if _f(u["first_deposit_amount_asof_inr"]) > 0)
    dep50, dep75 = quantile(deps, 0.5), quantile(deps, 0.75)
    tv = [_f(u["trading_value_6m_inr"]) for u in users if _f(u["total_trades"]) > 0]
    tv75 = quantile(tv, 0.75)

    # ---- tickets per user
    tk = defaultdict(list)
    for t in tickets:
        cd = _d(t["created_date"])
        if cd and cd <= as_of:
            tk[t["user_id"]].append((cd, t["status"].strip().title(), _f(t["resolution_time_hours"])))

    out = {}
    for u in users:
        if u["registration_date"] > as_of:
            continue
        ev = [u["kyc_date_asof"], u["bank_date_asof"], u["deposit_date_asof"], u["trade_date_asof"]]
        stage = 0
        for e in ev:
            if e is not None and e <= as_of:
                stage += 1
            else:
                break
        anchor = [u["registration_date"]] + ev
        anchor_date = anchor[stage]
        tenure = (as_of - u["registration_date"]).days
        dwell = (as_of - anchor_date).days
        stalled = stage < 4 and dwell > windows[stage] if stage < 4 else False
        overdue = dwell - windows[stage] if stalled else 0

        la = u["last_active_date_adj"] or anchor_date
        la = max(la, anchor_date)
        days_inactive = max((as_of - la).days, 0) if la <= as_of else 0
        inact = stage == 4 and tenure >= 31 and days_inactive > 30

        total = unres = esc = flagged_unres = 0
        oldest = 0
        for cd, st, hrs in tk.get(u["user_id"], []):
            total += 1
            resolved_at = datetime.combine(cd, datetime.min.time()) + timedelta(hours=hrs)
            is_unres = (st != "Resolved") or (st == "Resolved" and resolved_at > datetime.combine(as_of, datetime.min.time()))
            if is_unres:
                unres += 1
                age = (as_of - cd).days
                oldest = max(oldest, age)
                is_esc = st == "Escalated"
                esc += int(is_esc)
                if is_esc or age > 2:
                    flagged_unres += 1

        cats = []
        if stalled:
            cats.append(JOURNEY_CAT[stage])
        if inact:
            cats.append("INACTIVITY_RISK")
        if flagged_unres > 0:
            cats.append("SUPPORT_UNRESOLVED")
        if total >= 3:
            cats.append("REPEATED_SUPPORT_ISSUES")
        if cats:
            primary = next(p for p in PRECEDENCE if p in cats)
        elif stage < 4:
            primary = "WITHIN_WINDOW"
        else:
            primary = "NO_FRICTION"
        flagged = bool(cats)

        # data confidence
        log = [r for r in monthly.get(u["user_id"], []) if r["activity_month"] <= as_of_str[:7]]
        lt = sum(_f(r["trade_count"]) for r in log)
        ld = sum(_f(r["deposit_value_inr"]) for r in log)
        act_months = [r["activity_month"] for r in log if _f(r["active_in_month"]) == 1]
        last_m = max(act_months) if act_months else None
        conflict = False
        if primary in JOURNEY_CAT:
            conflict = lt > 0 or (stage < 3 and ld > 0)
        elif primary == "INACTIVITY_RISK":
            cutoff = (as_of - timedelta(days=30)).strftime("%Y-%m")
            conflict = last_m is not None and last_m >= cutoff
        conf = "" if not flagged else ("LOW" if conflict else "HIGH")

        # score
        p1 = 10 * min(1.0, max(tenure, 0) / 90.0)
        p2 = float(STAGE_PTS[stage])
        p3 = 20 * min(1.0, max(days_inactive, 0) / 90.0)
        sup = 12 if esc > 0 else (8 if flagged_unres > 0 else 0)
        sup += 5 if total >= 3 else (2 if total == 2 else 0)
        sup += 3 if oldest > 90 else 0
        p4 = min(20.0, float(sup))
        p5 = (5 if days_inactive <= 30 else 0) + min(5, max(int(_f(u["active_months_6m"])), 0))
        dep = _f(u["first_deposit_amount_asof_inr"]) if stage >= 3 else 0.0
        dp = 8 if dep >= dep75 else (5 if dep >= dep50 else (2 if dep > 0 else 0))
        t6 = _f(u["trading_value_6m_inr"])
        tp = 8 if t6 >= tv75 else (4 if t6 > 0 else 0)
        mp = 4 if _f(u["trade_months_6m"]) >= 2 else 0
        p6 = float(dp + tp + mp)
        raw = p1 + p2 + p3 + p4 + p5 + p6
        score = round(raw, 1) if flagged else 0.0
        band = "NOT_FLAGGED" if not flagged else ("High" if score >= 55 else ("Medium" if score >= 35 else "Low"))
        out[u["user_id"]] = dict(stage_idx=stage, is_flagged=int(flagged), friction_categories="|".join(cats),
                                 primary_category=primary, days_overdue=overdue, days_inactive=days_inactive,
                                 data_confidence=conf, priority_score=score, priority_band=band,
                                 tickets_total=total, tickets_unresolved=unres)
    return out, windows
