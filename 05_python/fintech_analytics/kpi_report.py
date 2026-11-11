"""Automated KPI report: computes the headline KPIs from the cleaned tables, compares them with the validated Phase 3 results,
and writes KPI_Report.md / kpi_values.csv / kpi_values.json (+ charts). All data are synthetic."""
import json
import numpy as np
import pandas as pd
from . import config as C, funnel as F, cohort as K, support as S, campaign as CP, segmentation as SG


def compute_kpis(d):
    u, a, t, c = d["users"], d["activity"], d["tickets"], d["campaigns"]
    ft = F.funnel_table(u); ret = K.retention_summary(a); mau = K.mau_table(u, a); rep = K.repeat_trading(u); tk = S.ticket_kpis(t, len(u))
    e30 = u[u.eligible_30d == 1]; e90 = u[u.eligible_90d == 1]
    k = {
        "total_registrations": len(u), "mature_users": int(u.funnel_mature.sum()),
        "funnel_registered": int(ft.reached["Registered"]), "funnel_kyc": int(ft.reached["KYC Completed"]), "funnel_bank": int(ft.reached["Bank Linked"]),
        "funnel_deposit": int(ft.reached["First Deposit"]), "funnel_trade": int(ft.reached["First Trade"]), "funnel_active30": int(ft.reached["Active (30d)"]),
        "conv_kyc_pct": ft.step_conversion_pct["KYC Completed"], "conv_bank_pct": ft.step_conversion_pct["Bank Linked"],
        "conv_deposit_pct": ft.step_conversion_pct["First Deposit"], "conv_trade_pct": ft.step_conversion_pct["First Trade"],
        "reg_to_trade_pct": ft.pct_of_registered["First Trade"],
        "m1_retention_pct": 100 * ret["M1"], "m3_retention_pct": 100 * ret["M3"], "m6_retention_pct": 100 * ret["M6"],
        "mau_latest": int(mau.mau.iloc[-1]), "mau_first": int(mau.mau.iloc[0]),
        "active_30d_pct": 100 * e30.active_30d_adj.mean(), "inactive_90d_proxy_pct": 100 * e90.inactive_90d_adj.mean(),
        "dormant_3m_pct": K.dormancy_rate(u)["dormant_3m_pct"],
        "repeat_pct_of_traders": rep["repeat_pct_of_traders"], "repeat_base_users": rep["base_users"],
        "tickets": tk["tickets"], "tickets_per_1000_users": tk["tickets_per_1000_users"], "users_with_ticket_pct": tk["users_with_ticket_pct"],
        "resolved_pct": tk["resolved_pct"], "open_tickets": tk["open"], "escalated_tickets": tk["escalated"],
        "median_resolution_h": tk["median_resolution_h"], "mean_resolution_h": tk["mean_resolution_h"], "p90_resolution_h": tk["p90_resolution_h"],
        "csat_mean": tk["csat_mean"],
    }
    for ch, n in u.groupby("acquisition_channel").size().items(): k[f"registrations_{ch}"] = int(n)
    return k


def phase3_targets():
    r = json.loads(C.PHASE3_RESULTS.read_text())
    f = r["funnel"]
    # (python key, Phase 3 value, absolute tolerance)
    return {
        "total_registrations": (r["n_users"], 0), "mature_users": (r["n_mature"], 0),
        "funnel_registered": (f["Registered"]["reached"], 0), "funnel_kyc": (f["KYC Completed"]["reached"], 0), "funnel_bank": (f["Bank Linked"]["reached"], 0),
        "funnel_deposit": (f["First Deposit"]["reached"], 0), "funnel_trade": (f["First Trade"]["reached"], 0),
        "conv_kyc_pct": (100 * f["KYC Completed"]["conv_prev"], .06), "conv_bank_pct": (100 * f["Bank Linked"]["conv_prev"], .06),
        "conv_deposit_pct": (100 * f["First Deposit"]["conv_prev"], .06), "conv_trade_pct": (100 * f["First Trade"]["conv_prev"], .06),
        "m1_retention_pct": (100 * r["m1"], .01), "m3_retention_pct": (100 * r["m3"], .01), "m6_retention_pct": (100 * r["m6"], .01),
        "mau_latest": (r["mau_last"], 0), "mau_first": (r["mau_first"], 0),
        "active_30d_pct": (100 * r["active30"], .01), "inactive_90d_proxy_pct": (100 * r["inactive90"], .01), "dormant_3m_pct": (100 * r["dormant3m"], .01),
        "repeat_pct_of_traders": (100 * r["repeat_trader_share_of_traders"], .01), "repeat_base_users": (r["repeat_base_n"], 0),
        "tickets": (r["tickets"], 0), "tickets_per_1000_users": (r["tickets_per_1000_users"], .01), "users_with_ticket_pct": (100 * r["users_with_ticket_pct"], .01),
        "resolved_pct": (100 * r["resolved_pct"], .01), "open_tickets": (r["open_n"], 0), "escalated_tickets": (r["escalated_n"], 0),
        "median_resolution_h": (r["res_median"], .05), "mean_resolution_h": (r["res_mean"], .001), "p90_resolution_h": (r["res_p90"], .05),
        "csat_mean": (r["csat_mean"], .001),
    }


def compare_to_phase3(kpis):
    rows = []
    for key, (target, tol) in phase3_targets().items():
        v = kpis[key]
        rows.append(dict(kpi=key, python_value=round(float(v), 4), phase3_value=round(float(target), 4), abs_diff=round(abs(float(v) - float(target)), 4), tolerance=tol,
                         status="MATCH" if abs(float(v) - float(target)) <= tol + 1e-9 else "DIFF"))
    return pd.DataFrame(rows)


def build_report(d, out_dir=None):
    """Compute KPIs, verify vs Phase 3, write the report files, return (kpis, comparison DataFrame, markdown text)."""
    out = out_dir or C.OUT_DIR; out.mkdir(parents=True, exist_ok=True)
    k = compute_kpis(d); cmp_ = compare_to_phase3(k)
    sc = CP.campaign_scorecard(d["users"], d["campaigns"]); seg = SG.journey_summary(d["users"])
    ft = F.funnel_table(d["users"]); cat = S.category_table(d["tickets"])
    ok = int((cmp_.status == "MATCH").sum())
    md = ["# Automated KPI Report", "", "> **All data are synthetic** (fictional Indian retail brokerage; 10,000 users; Nov 2025 - Oct 2026; INR; snapshot 2026-10-31).",
          "> Generated by `fintech_analytics.kpi_report`. Retention/inactivity flags are proxies, not confirmed churn.", "",
          f"**Verification vs validated Phase 3 results: {ok}/{len(cmp_)} KPIs match within tolerance.**", "",
          "## Headline KPIs", "", "| KPI | Value |", "|---|---|",
          f"| Registrations (total / mature cohort) | {k['total_registrations']:,} / {k['mature_users']:,} |",
          f"| Registered -> first trade (mature) | {k['reg_to_trade_pct']:.1f}% |",
          f"| M1 / M3 / M6 retention (calendar-month proxy) | {k['m1_retention_pct']:.1f}% / {k['m3_retention_pct']:.1f}% / {k['m6_retention_pct']:.1f}% |",
          f"| MAU, Oct-2026 | {k['mau_latest']:,} |",
          f"| Dormant 3 months (churn proxy) | {k['dormant_3m_pct']:.1f}% |",
          f"| Repeat traders (share of ever-traders, >= 4 observed months) | {k['repeat_pct_of_traders']:.1f}% |",
          f"| Support tickets / per 1,000 users | {k['tickets']:,} / {k['tickets_per_1000_users']:.0f} |",
          f"| Median / mean resolution time | {k['median_resolution_h']:.1f} h / {k['mean_resolution_h']:.1f} h |",
          f"| CSAT (mean, rated tickets) | {k['csat_mean']:.2f} |",
          f"| Unresolved tickets (open + escalated) | {k['open_tickets'] + k['escalated_tickets']:,} |", "",
          "## Funnel (mature cohort)", "", ft.reset_index(names="stage")[["stage", "reached", "pct_of_registered", "step_conversion_pct", "users_lost"]].to_markdown(index=False), "",
          "## Campaign scorecard", "", sc[["campaign_name", "channel", "registered_users", "cac_inr", "first_trade_rate_mature_pct", "cost_per_first_trader_inr", "m3_retention_pct"]].to_markdown(index=False), "",
          "## Journey segments", "", seg.to_markdown(index=False), "",
          "## Support categories", "", cat[["category", "tickets", "share_pct", "median_resolution_h", "avg_csat", "unresolved"]].to_markdown(index=False), "",
          "## Verification detail", "", cmp_.to_markdown(index=False), ""]
    text = "\n".join(md)
    (out / "KPI_Report.md").write_text(text)
    cmp_.to_csv(out / "kpi_verification_vs_phase3.csv", index=False)
    pd.Series(k).rename("value").to_csv(out / "kpi_values.csv")
    (out / "kpi_values.json").write_text(json.dumps({a: (float(b) if isinstance(b, (int, float, np.floating, np.integer)) else b) for a, b in k.items()}, indent=1))
    return k, cmp_, text
