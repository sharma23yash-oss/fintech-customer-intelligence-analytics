"""Support operations analytics: volume, SLA proxies, CSAT, backlog, repeat contactors."""
import numpy as np
import pandas as pd
from .eda import style, BLUE, GREY, INK, ORANGE
import matplotlib.pyplot as plt


def ticket_kpis(tickets, n_users=10000):
    r = tickets.resolution_time_hours.dropna()
    return dict(tickets=len(tickets), tickets_per_1000_users=1000 * len(tickets) / n_users, users_with_ticket_pct=100 * tickets.user_id.nunique() / n_users,
                resolved_pct=100 * tickets.is_resolved.mean(), open=int((tickets.status == "Open").sum()), escalated=int((tickets.status == "Escalated").sum()),
                unresolved=int(tickets.is_unresolved.sum()), median_resolution_h=float(r.median()), mean_resolution_h=float(r.mean()),
                p90_resolution_h=float(r.quantile(.9)), csat_mean=float(tickets.csat_score.mean()),
                csat_top_box_pct=100 * float((tickets.csat_score.dropna() >= 4).mean()), csat_bottom_box_pct=100 * float((tickets.csat_score.dropna() <= 2).mean()))


def category_table(tickets):
    g = tickets.groupby("category")
    t = pd.DataFrame({"tickets": g.size(), "users_affected": g.user_id.nunique(), "high_priority": g.priority.apply(lambda s: (s == "High").sum()),
                      "escalated": g.status.apply(lambda s: (s == "Escalated").sum()), "unresolved": g.is_unresolved.sum(),
                      "median_resolution_h": g.resolution_time_hours.median(), "mean_resolution_h": g.resolution_time_hours.mean(), "avg_csat": g.csat_score.mean()})
    t["share_pct"] = 100 * t.tickets / t.tickets.sum()
    return t.round(2).sort_values("tickets", ascending=False).reset_index()


def backlog_table(tickets):
    u = tickets[tickets.is_unresolved == 1]
    return u.pivot_table(index="backlog_age_bucket", columns="priority", values="ticket_id", aggfunc="count", fill_value=0)\
            .reindex(["0-30d", "31-90d", "91-180d", ">180d"]).assign(total=lambda d: d.sum(axis=1)).reset_index()


def repeat_contactors(tickets, min_tickets=3):
    c = tickets.groupby("user_id").agg(tickets=("ticket_id", "size"), categories=("category", "nunique"), unresolved=("is_unresolved", "sum"), avg_csat=("csat_score", "mean"))
    return c[c.tickets >= min_tickets].reset_index()


def monthly_ticket_trend(tickets):
    return tickets.groupby("created_month").agg(tickets=("ticket_id", "size"), median_resolution_h=("resolution_time_hours", "median"), avg_csat=("csat_score", "mean")).round(2).reset_index()


def plot_category(tickets, ax=None):
    style(); ax = ax or plt.subplots(figsize=(6.4, 3.4))[1]
    t = category_table(tickets).sort_values("tickets")
    ax.barh(t.category, t.tickets, color=BLUE, height=.6)
    for y, (v, s) in enumerate(zip(t.tickets, t.share_pct)): ax.text(v + 15, y, f"{v:,} ({s:.1f}%)", va="center", fontsize=8, color=INK)
    ax.set_xlim(0, t.tickets.max() * 1.25); ax.set_title("Support tickets by category (synthetic)"); ax.set_xlabel("Tickets")
    return ax
