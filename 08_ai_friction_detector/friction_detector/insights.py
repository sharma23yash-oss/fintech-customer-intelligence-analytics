"""AI insight generator: explanations, interventions and the daily operational summary.

Mode 1 (default, always available): transparent RULE-BASED text built from templates and the
actual rule values. This is the fallback and the source of truth for the facts.

Mode 2 (optional): if an LLM API key is configured in the environment, the rule-based text is
passed to the model ONLY to be re-worded. What is sent is limited to a whitelist of de-identified,
bucketed fields (no user ID, no city, no amounts, no dates). If anything fails the rule-based text
is used. The live LLM call is NOT exercised in the automated tests (no key is available there);
the payload builder and the fallback are.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping

import pandas as pd

from . import config as C

# --------------------------------------------------------------------------- interventions
INTERVENTIONS = {
    C.KYC_PENDING: {
        "action": "Confirm KYC status in the source system, then send the document checklist with a resume link; "
                  "offer an assisted-KYC call-back.",
        "stale_action": "Offer an assisted-KYC call-back; a plain reminder is unlikely to work this late.",
    },
    C.BANK_LINK_PENDING: {
        "action": "Send a bank-linking guide with a UPI-first option and offer help if the first attempt failed.",
        "stale_action": "Offer an assisted bank-link call-back and check open bank-link tickets.",
    },
    C.FIRST_DEPOSIT_PENDING: {
        "action": "Send a first-deposit reminder with low-ticket suggested amounts and an explanation of how funds are protected.",
        "stale_action": "Send a value-led reminder with low-ticket amounts and check deposit-related tickets first.",
    },
    C.FIRST_TRADE_PENDING: {
        "action": "Send a guided first-trade walkthrough (practice order) and a short beginner idea list; no trade is placed by the system.",
        "stale_action": "Offer an assisted first-trade session; the customer funded the account but has not traded.",
    },
    C.INACTIVITY_RISK: {
        "action": "Send a value-led re-engagement message (portfolio or market update, not a discount) and track reactivation with a holdout.",
        "stale_action": "Add to the win-back sequence with a holdout group; avoid repeated messages.",
    },
    C.SUPPORT_UNRESOLVED: {
        "action": "Route to the ticket owner for a status update to the customer today; escalate if past SLA.",
        "stale_action": "Escalate to the team lead: the ticket has been open far beyond normal resolution times.",
    },
    C.REPEATED_SUPPORT_ISSUES: {
        "action": "Team-lead review of the ticket history for a root cause; one consolidated reply instead of separate answers.",
        "stale_action": "Team-lead review of the ticket history for a root cause.",
    },
}
CATEGORY_LABEL = {
    C.KYC_PENDING: "KYC not completed after the normal window",
    C.BANK_LINK_PENDING: "KYC done but no bank account linked after the normal window",
    C.FIRST_DEPOSIT_PENDING: "Bank linked but no first deposit after the normal window",
    C.FIRST_TRADE_PENDING: "Funded but no first trade after the normal window",
    C.INACTIVITY_RISK: "Inactive after first trade",
    C.SUPPORT_UNRESOLVED: "Open or escalated support ticket",
    C.REPEATED_SUPPORT_ISSUES: "Repeated support tickets",
    C.WITHIN_WINDOW: "Pending step but still inside the normal window (not flagged)",
    C.NO_FRICTION: "No friction rule triggered",
}


def _row(row: Mapping[str, Any]) -> dict:
    return dict(row) if not isinstance(row, dict) else row


def explain_customer(row: Mapping[str, Any], cfg_dict: Mapping[str, Any] | None = None) -> dict:
    """Rule-based explanation for one customer row (a dict or pandas Series)."""
    r = _row(row)
    cats = [c for c in str(r.get("friction_categories", "") or "").split("|") if c]
    primary = r.get("primary_category", C.NO_FRICTION)
    why: list[str] = []
    if C.KYC_PENDING in cats or C.BANK_LINK_PENDING in cats or C.FIRST_DEPOSIT_PENDING in cats \
            or C.FIRST_TRADE_PENDING in cats:
        why.append(
            f"Journey: last completed step is '{r['stage_name']}' ({r['anchor_event']} on {str(r['anchor_date'])[:10]}); "
            f"{int(r['dwell_days'])} days have passed. The normal window for the next step is {int(r['window_days'])} days "
            f"(95th percentile of observed completion lags), so the customer is {int(r['days_overdue'])} days past it.")
    if C.INACTIVITY_RISK in cats:
        why.append(
            f"Inactivity: first trade is done but there has been no recorded activity for {int(r['days_inactive'])} days "
            f"(rule: more than {(cfg_dict or {}).get('inactivity_days', 30)} days, customer registered at least "
            f"{(cfg_dict or {}).get('min_tenure_for_inactivity_days', 31)} days ago). This is an inactivity proxy, not churn.")
    if C.SUPPORT_UNRESOLVED in cats:
        why.append(
            f"Support: {int(r['tickets_unresolved'])} unresolved ticket(s)"
            f"{', of which ' + str(int(r['tickets_escalated'])) + ' escalated' if int(r['tickets_escalated']) else ''}; "
            f"the oldest has been open {int(r['oldest_unresolved_days'])} days.")
    if C.REPEATED_SUPPORT_ISSUES in cats:
        why.append(f"Support: {int(r['tickets_total'])} tickets raised in total "
                   f"(rule: {(cfg_dict or {}).get('repeated_ticket_min', 3)} or more).")
    if not cats:
        if primary == C.WITHIN_WINDOW:
            why.append(f"Not flagged: the customer is {int(r['dwell_days'])} days after '{r['anchor_event']}', still inside the "
                       f"normal {int(r['window_days'])}-day window for the next step.")
        else:
            why.append("No rule was triggered for this customer on the as-of date.")

    stale = int(r.get("days_overdue", 0) or 0) > 30 or int(r.get("oldest_unresolved_days", 0) or 0) > 30
    iv = INTERVENTIONS.get(primary)
    action = (iv["stale_action"] if stale else iv["action"]) if iv else "No action needed."
    notes: list[str] = []
    if r.get("data_confidence") == "LOW":
        notes.append("Data confidence LOW: " + str(r.get("conflict_detail")) +
                     ". Verify the real status in the source system before any outreach.")
    if int(r.get("sequence_anomaly", 0) or 0):
        notes.append("Event dates are out of order for this record; check the source data.")
    if len(cats) > 1:
        notes.append("Also flagged for: " + ", ".join(c for c in cats if c != primary) + ".")
    band = r.get("priority_band", "NOT_FLAGGED")
    head = (f"{CATEGORY_LABEL.get(primary, primary)}. "
            + (f"Priority {band} (heuristic score {float(r.get('priority_score', 0)):.1f} of 100)." if band != "NOT_FLAGGED"
               else "Not flagged."))
    return {
        "summary": head,
        "why_flagged": why,
        "recommended_intervention": action,
        "owner_team": C.OWNER_TEAM.get(primary, "-"),
        "notes": notes,
        "disclaimer": "Suggestion only. The priority score is a heuristic ordering aid, not a probability. "
                      "No message has been or will be sent by this tool. Synthetic data.",
        "mode": "rule-based",
    }


# --------------------------------------------------------------------------- daily summary
def daily_operational_summary(stats: Mapping[str, Any]) -> str:
    """Rule-based markdown summary from an aggregate stats dict (see reports.build_stats)."""
    s = stats
    L: list[str] = []
    L.append(f"# Daily friction summary - {s['run_date']}  [SYNTHETIC DATA]")
    L.append("")
    L.append(f"Customers analysed: **{s['analysed']:,}**. Flagged: **{s['flagged']:,}** "
             f"({s['flagged_pct']:.1f}%). High priority: **{s['high_priority']:,}**.")
    if s.get("previous_run_date"):
        L.append(f"Compared with the run of {s['previous_run_date']}: **{s['newly_flagged']:,} newly flagged**, "
                 f"{s['no_longer_flagged']:,} no longer flagged.")
    else:
        L.append("This is the first stored run, so it is a baseline. 'Newly flagged' is not meaningful yet.")
    L.append("")
    L.append("## Most common friction categories (primary category)")
    for cat, n in s["by_category"][:5]:
        L.append(f"- {cat}: {n:,} ({n / max(s['flagged'], 1) * 100:.1f}% of flagged)")
    if s.get("new_by_category"):
        L.append("")
        L.append("## Newly flagged since the previous run")
        for cat, n in s["new_by_category"][:5]:
            L.append(f"- {cat}: {n:,}")
    L.append("")
    L.append("## Priority split (heuristic score, not a probability)")
    L.append(f"- High: {s['priority']['High']:,}; Medium: {s['priority']['Medium']:,}; Low: {s['priority']['Low']:,}")
    L.append("")
    L.append("## Work by team")
    for team, n in s["by_team"]:
        L.append(f"- {team}: {n:,} customers")
    L.append("")
    L.append("## Points to note")
    top_cat, top_n = s["by_category"][0] if s["by_category"] else ("-", 0)
    L.append(f"- The largest group is {top_cat} ({top_n:,} customers). "
             + ("Most of these have waited well beyond the normal window." if s.get("avg_overdue_top", 0) > 30 else ""))
    L.append(f"- {s['verify_first']:,} flagged customers ({s['verify_first_pct']:.0f}%) have data confidence LOW: the "
             "activity log contradicts the funnel record. Verify these in the source system before outreach.")
    if s.get("support_unresolved_old", 0):
        L.append(f"- {s['support_unresolved_old']:,} customers have an unresolved ticket open for more than 90 days.")
    L.append("")
    L.append("_Rule-based summary. Suggestions only: this tool does not send messages or touch money. "
             "The priority score is a heuristic for ordering work._")
    return "\n".join(L)


# --------------------------------------------------------------------------- optional LLM
ALLOWED_CUSTOMER_FIELDS = ("friction_category", "funnel_stage", "overdue_band", "inactivity_band",
                           "unresolved_tickets_band", "priority_band", "data_confidence", "intervention_template")
ALLOWED_DAILY_FIELDS = ("run_label", "analysed_band", "category_counts", "priority_counts", "new_flag_count_band")
_ID_RE = re.compile(r"\bU\d{4,}\b")


def _band(n: float, edges: list[tuple[float, str]], last: str) -> str:
    for lim, lab in edges:
        if n <= lim:
            return lab
    return last


def safe_customer_payload(row: Mapping[str, Any], explanation: Mapping[str, Any]) -> dict:
    """De-identified, bucketed payload. No user ID, city, channel, dates or amounts."""
    r = _row(row)
    p = {
        "friction_category": r.get("primary_category"),
        "funnel_stage": r.get("stage_name"),
        "overdue_band": _band(int(r.get("days_overdue", 0) or 0), [(0, "none"), (14, "1-14 days"), (30, "15-30 days"),
                                                                    (90, "31-90 days")], "over 90 days"),
        "inactivity_band": _band(int(r.get("days_inactive", 0) or 0), [(30, "up to 30 days"), (60, "31-60 days"),
                                                                       (90, "61-90 days")], "over 90 days"),
        "unresolved_tickets_band": _band(int(r.get("tickets_unresolved", 0) or 0), [(0, "none"), (1, "one")], "several"),
        "priority_band": r.get("priority_band"),
        "data_confidence": r.get("data_confidence"),
        "intervention_template": explanation.get("recommended_intervention"),
    }
    assert_payload_safe(p, ALLOWED_CUSTOMER_FIELDS)
    return p


def safe_daily_payload(stats: Mapping[str, Any]) -> dict:
    """Aggregates only; small cells (<5) are suppressed."""
    def supp(n):
        return "<5" if n < 5 else int(n)
    p = {
        "run_label": "synthetic daily run",
        "analysed_band": _band(stats["analysed"], [(1000, "up to 1,000"), (10000, "1,000-10,000")], "over 10,000"),
        "category_counts": {k: supp(v) for k, v in stats["by_category"]},
        "priority_counts": {k: supp(v) for k, v in stats["priority"].items()},
        "new_flag_count_band": _band(stats.get("newly_flagged", 0), [(0, "none"), (100, "up to 100"), (1000, "101-1,000")],
                                     "over 1,000"),
    }
    assert_payload_safe(p, ALLOWED_DAILY_FIELDS)
    return p


def assert_payload_safe(payload: Mapping[str, Any], allowed: tuple[str, ...]) -> None:
    extra = set(payload) - set(allowed)
    if extra:
        raise ValueError(f"payload fields not on the whitelist: {sorted(extra)}")
    blob = json.dumps(payload)
    if _ID_RE.search(blob):
        raise ValueError("payload contains something that looks like a user ID")


@dataclass
class LLMConfig:
    api_key: str | None
    model: str
    endpoint: str = "https://api.anthropic.com/v1/messages"

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
                   model=os.environ.get("FRICTION_LLM_MODEL", "claude-sonnet-5-5"))

    @property
    def available(self) -> bool:
        return bool(self.api_key) and os.environ.get("FRICTION_DISABLE_LLM", "") != "1"


SYSTEM_PROMPT = ("You rewrite short operational notes for a brokerage operations team. The data is synthetic. "
                 "Use ONLY the facts provided. Do not add numbers, causes or promises. Do not state or imply a "
                 "probability. Keep it under 90 words and plain English.")


def llm_rewrite(kind: str, payload: Mapping[str, Any], fallback_text: str, cfg: LLMConfig | None = None,
                transport=None) -> tuple[str, bool]:
    """Return (text, used_llm). Falls back to the rule-based text on any problem."""
    cfg = cfg or LLMConfig.from_env()
    if not cfg.available:
        return fallback_text, False
    body = {"model": cfg.model, "max_tokens": 300, "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": f"Task: {kind}\nFacts (JSON): {json.dumps(payload)}\n"
                                                     f"Draft to improve:\n{fallback_text}"}]}
    try:
        if transport is not None:
            data = transport(cfg, body)
        else:
            req = urllib.request.Request(
                cfg.endpoint, data=json.dumps(body).encode(), method="POST",
                headers={"content-type": "application/json", "x-api-key": cfg.api_key,
                         "anthropic-version": "2023-06-01"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read())
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
        return (text, True) if text else (fallback_text, False)
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, OSError):
        return fallback_text, False
