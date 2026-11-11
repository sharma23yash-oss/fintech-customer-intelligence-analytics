"""Brokerage Customer Friction Detector - AI Operations Intelligence (SYNTHETIC DATA PROTOTYPE).

Run:  streamlit run app/streamlit_app.py
Reads db/friction.db (build with: python -m friction_detector.cli build-db && ... run-daily).
Read-only: this app never sends messages and never touches trades, deposits or withdrawals.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import altair as alt
import pandas as pd
import streamlit as st

from friction_detector import config as C
from friction_detector.insights import (LLMConfig, daily_operational_summary, explain_customer, llm_rewrite,
                                        safe_customer_payload)
from friction_detector import db as dbm
from friction_detector.reports import build_stats

st.set_page_config(page_title="Friction Detector (synthetic)", layout="wide")

BAND_ORDER = ["High", "Medium", "Low"]


@st.cache_data(show_spinner=False)
def load(db_path: str, mtime: float):
    conn = dbm.connect(db_path)
    cf = pd.read_sql("SELECT * FROM customer_friction", conn)
    tk = pd.read_sql("SELECT * FROM tickets", conn)
    runs = pd.read_sql("SELECT * FROM friction_runs ORDER BY run_date", conn)
    snap = pd.read_sql("SELECT run_date, user_id FROM friction_snapshot", conn)
    cfg, _ = dbm.load_config_from_db(conn)
    conn.close()
    return cf, tk, runs, snap, cfg.to_dict()


db_file = Path(C.DB_PATH)
st.warning("**SYNTHETIC DATA** - fictional customers, prototype only. "
           "Scores are heuristics, not predictions. No messages are sent.")
if not db_file.exists():
    st.error("Database not found. Run: `python -m friction_detector.cli build-db` then `run-daily`.")
    st.stop()

cf, tickets, runs, snap, cfg = load(str(db_file), db_file.stat().st_mtime)
if runs.empty:
    st.error("The database has no daily runs yet. Run: `python -m friction_detector.cli replay --start 2026-10-24 --end 2026-10-31` (or `run-daily --as-of 2026-10-31`).")
    st.stop()
run_date = runs["run_date"].max()
latest = runs.iloc[-1]
cf["registration_date"] = pd.to_datetime(cf["registration_date"])

st.title("Brokerage Customer Friction Detector")
st.caption(f"AI Operations Intelligence prototype | run date {run_date} | data_label = SYNTHETIC")

# ---------------------------------------------------------------- sidebar filters
st.sidebar.header("Filters")
cities = st.sidebar.multiselect("City", sorted(cf["city"].dropna().unique()))
channels = st.sidebar.multiselect("Acquisition channel", sorted(cf["acquisition_channel"].dropna().unique()))
months = sorted(cf["registration_month"].dropna().unique())
mrange = st.sidebar.select_slider("Registration month", options=months, value=(months[0], months[-1]))
cats = st.sidebar.multiselect("Friction category (primary)", C.FLAGGED_CATEGORIES)
bands = st.sidebar.multiselect("Priority band", BAND_ORDER)
only_high_conf = st.sidebar.checkbox("High data confidence only", value=False,
                                     help="Hide customers whose activity log contradicts the funnel record.")

f = cf[(cf["registration_month"] >= mrange[0]) & (cf["registration_month"] <= mrange[1])]
if cities:
    f = f[f["city"].isin(cities)]
if channels:
    f = f[f["acquisition_channel"].isin(channels)]
flagged = f[f["is_flagged"] == 1]
if cats:
    flagged = flagged[flagged["primary_category"].isin(cats)]
if bands:
    flagged = flagged[flagged["priority_band"].isin(bands)]
if only_high_conf:
    flagged = flagged[flagged["data_confidence"] == "HIGH"]

view = st.sidebar.radio("View", ["Overview", "Customer lookup", "Daily report", "Method & limits"])

# ---------------------------------------------------------------- overview
if view == "Overview":
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Customers analysed", f"{len(f):,}")
    c2.metric("Customers flagged", f"{len(flagged):,}", help="Share of analysed customers: "
              f"{len(flagged) / max(len(f), 1) * 100:.1f}%")
    c3.metric("High priority", f"{int((flagged['priority_band'] == 'High').sum()):,}")
    c4.metric("Verify-first (LOW confidence)", f"{int((flagged['data_confidence'] == 'LOW').sum()):,}")
    st.caption("Metrics follow the sidebar filters. Within-window customers (not yet flagged): "
               f"{int((f['primary_category'] == C.WITHIN_WINDOW).sum()):,}.")

    left, right = st.columns(2)
    with left:
        st.subheader("Friction category distribution")
        d = flagged["primary_category"].value_counts().rename_axis("category").reset_index(name="customers")
        st.altair_chart(alt.Chart(d).mark_bar().encode(
            y=alt.Y("category:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260)),
            x=alt.X("customers:Q", title="customers"),
            tooltip=["category", "customers"]).properties(height=260), width="stretch")
        st.dataframe(d, hide_index=True, width="stretch")
    with right:
        st.subheader("Priority distribution (heuristic score)")
        p = flagged["priority_band"].value_counts().reindex(BAND_ORDER).fillna(0).astype(int)
        pd_ = p.rename_axis("band").reset_index(name="customers")
        st.altair_chart(alt.Chart(pd_).mark_bar().encode(
            x=alt.X("band:N", sort=BAND_ORDER, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("customers:Q", title="customers"), tooltip=["band", "customers"]).properties(height=260),
            width="stretch")
        st.dataframe(p.rename_axis("band").reset_index(name="customers"), hide_index=True, width="stretch")

    st.subheader("Work queue - highest priority first")
    q = flagged.sort_values(["priority_score", "days_overdue"], ascending=False).head(200)
    st.dataframe(q[["user_id", "primary_category", "priority_band", "priority_score", "stage_name", "days_overdue",
                    "days_inactive", "tickets_unresolved", "data_confidence", "city", "acquisition_channel"]],
                 hide_index=True, width="stretch")
    st.caption("Showing the top 200 of the filtered list. Download the full list from the Daily report view.")

# ---------------------------------------------------------------- lookup
elif view == "Customer lookup":
    uid = st.text_input("Synthetic user ID", placeholder="e.g. U100109").strip().upper()
    if uid:
        row = cf[cf["user_id"] == uid]
        if row.empty:
            st.error(f"No customer {uid!r} in the synthetic dataset.")
        else:
            r = row.iloc[0].to_dict()
            exp = explain_customer(r, cfg)
            a, b, c = st.columns(3)
            a.metric("Primary category", r["primary_category"])
            b.metric("Priority", f"{r['priority_band']}", help=f"Heuristic score {r['priority_score']:.1f} / 100 "
                     "(an ordering aid, not a probability)")
            b.caption(f"Score {r['priority_score']:.1f} / 100 (heuristic, not a probability)")
            c.metric("Data confidence", r["data_confidence"])
            st.subheader("Journey status")
            steps = ["Registered", "KYC Completed", "Bank Linked", "Funded", "Traded"]
            st.progress((int(r["stage_idx"]) + 1) / 5, text=f"Furthest completed step: {r['stage_name']} "
                                                            f"({int(r['stage_idx']) + 1} of 5). Status: {r['journey_status']}")
            st.write(f"Registered {str(r['registration_date'])[:10]} | {r['city']} | {r['acquisition_channel']} | "
                     f"{int(r['tenure_days'])} days since registration")
            st.subheader("Why flagged / not flagged")
            for w in exp["why_flagged"]:
                st.write("- " + w)
            for n in exp["notes"]:
                st.info(n)
            st.subheader("Recommended intervention (suggestion only)")
            text = exp["recommended_intervention"]
            use_llm = False
            if LLMConfig.from_env().available and st.checkbox("Reword with LLM (sends de-identified bands only)"):
                text, use_llm = llm_rewrite("customer intervention", safe_customer_payload(r, exp), text)
            st.success(f"**{exp['owner_team']}**: {text}")
            st.caption(("Reworded by LLM. " if use_llm else "Rule-based text. ") + exp["disclaimer"])
            st.subheader("Priority score breakdown")
            bd = pd.DataFrame({"component": ["Days since registration (0-10)", "Funnel stage (0-20)", "Inactivity (0-20)",
                                              "Support history (0-20)", "Customer activity (0-10)",
                                              "Prior transactions (0-20)"],
                               "points": [r["pts_days_since_registration"], r["pts_funnel_stage"], r["pts_inactivity"],
                                          r["pts_support"], r["pts_activity"], r["pts_prior_transactions"]]})
            st.dataframe(bd, hide_index=True, width="stretch")
            st.subheader("Support ticket history")
            t = tickets[tickets["user_id"] == uid].sort_values("created_date")
            if t.empty:
                st.write("No tickets for this customer.")
            else:
                st.dataframe(t[["ticket_id", "created_date", "category", "priority", "status",
                                "resolution_time_hours", "csat_score"]], hide_index=True, width="stretch")
            h = snap[snap["user_id"] == uid]["run_date"].tolist()
            st.caption(f"Flagged in {len(h)} of {len(runs)} stored daily runs." if h else "Not flagged in any stored run.")
    else:
        st.write("Enter a synthetic user ID to see the journey, flag reason, intervention and tickets.")
        st.write("Examples from today's top of queue: " + ", ".join(
            cf[cf.is_flagged == 1].sort_values("priority_score", ascending=False)["user_id"].head(5)))

# ---------------------------------------------------------------- daily report
elif view == "Daily report":
    prev = runs[runs["run_date"] < run_date]["run_date"].max() if len(runs) > 1 else None
    new_ids = set()
    if prev:
        a = set(snap[snap.run_date == run_date].user_id)
        b = set(snap[snap.run_date == prev].user_id)
        new_ids = a - b
    ff = cf.copy()
    ff["owner_team"] = ff["primary_category"].map(C.OWNER_TEAM).fillna("")
    ff["is_new_today"] = ff["user_id"].isin(new_ids).astype(int)
    stats = build_stats(ff, run_date, prev, new_ids, int(latest["no_longer_flagged"]))
    st.caption("The summary below covers ALL customers for the stored run. The exception report and CSV downloads "
               "further down follow the sidebar filters.")
    st.markdown(daily_operational_summary(stats))
    st.subheader("Run history")
    st.dataframe(runs[["run_date", "customers_analysed", "customers_flagged", "newly_flagged", "no_longer_flagged"]],
                 hide_index=True, width="stretch")
    st.subheader("Exception report (current filters)")
    rep = flagged.assign(data_label="SYNTHETIC",
                         is_new_today=flagged["user_id"].isin(new_ids).astype(int),
                         owner_team=flagged["primary_category"].map(C.OWNER_TEAM)
                         ).sort_values(["priority_score", "days_overdue"], ascending=False)
    cols = ["data_label", "user_id", "primary_category", "friction_categories", "priority_band", "priority_score",
            "score_type", "stage_name", "days_overdue", "days_inactive", "tickets_unresolved", "data_confidence",
            "owner_team", "is_new_today", "city", "acquisition_channel"]
    st.dataframe(rep[cols].head(500), hide_index=True, width="stretch")
    st.download_button("Download exception report (CSV)", rep[cols].to_csv(index=False).encode(),
                       file_name=f"exception_report_{run_date}_SYNTHETIC.csv", mime="text/csv")
    st.download_button("Download newly flagged only (CSV)", rep[rep.is_new_today == 1][cols].to_csv(index=False).encode(),
                       file_name=f"newly_flagged_{run_date}_SYNTHETIC.csv", mime="text/csv")

# ---------------------------------------------------------------- method
else:
    st.subheader("How customers are flagged")
    st.markdown(f"""
- **Rule-based detection.** Each customer's furthest consecutive step (Registered, KYC, Bank linked, Funded, Traded) is
  derived from dated events. A step is flagged only when the customer has waited **longer than the 95th percentile of
  completion lags** observed for that step in this dataset (KYC {cfg['window_kyc_days']} d, bank {cfg['window_bank_days']} d,
  deposit {cfg['window_deposit_days']} d, first trade {cfg['window_trade_days']} d). Customers inside the window are **not** flagged.
- **Inactivity:** traded, registered at least {cfg['min_tenure_for_inactivity_days']} days ago, and no activity for more than
  {cfg['inactivity_days']} days. This is a proxy, not a churn label.
- **Support:** {cfg['repeated_ticket_min']}+ tickets, or an unresolved ticket (escalated, or open past a {cfg['open_ticket_grace_days']}-day grace period).
- **Priority score (0-100)** adds six transparent components. It is a **heuristic ordering aid, not a probability** and was
  not trained or validated against outcomes. scikit-learn is intentionally not used: there are no ground-truth labels.
- **Data confidence LOW** means the monthly activity log contradicts the funnel record for this customer (for example trades in the
  log but no first trade recorded). Verify in the source system first.
""")
    st.subheader("Limits")
    st.markdown("""
- Synthetic data, one snapshot (31 Oct 2026). Not production, not validated on real customers.
- Replay of earlier dates is approximate for inactivity and ticket state.
- The optional LLM path sends only bucketed, de-identified fields and is off unless an API key is configured.
- This tool reads data and writes reports. It sends no messages and starts no trades, deposits or withdrawals.
""")
