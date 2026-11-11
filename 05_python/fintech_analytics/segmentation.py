"""Customer segmentation: (1) rule-based journey segment (Phase 3 rule); (2) K-means behavioural clusters (scikit-learn)."""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score
from sklearn.preprocessing import StandardScaler
from . import config as C


def journey_segment(users):
    """Rule-based journey segment. Onboarding users within the historical max stage lag are 'in-flight'; beyond it 'stalled'."""
    u = users
    last = u[["registration_date", "kyc_date_asof", "bank_date_asof", "deposit_date_asof"]].max(axis=1)
    lag = (C.SNAPSHOT - last).dt.days
    since_trade = (C.SNAPSHOT - u.trade_date_asof).dt.days
    st = u.furthest_stage_asof
    inflight = ((st == "Registered") & (lag <= C.MAX_LAG["Registered"])) | ((st == "KYC Completed") & (lag <= C.MAX_LAG["KYC Completed"])) \
        | ((st == "Bank Linked") & (lag <= C.MAX_LAG["Bank Linked"])) | ((st == "Funded") & (lag <= C.MAX_LAG["Funded"]))
    conds = [inflight, st == "Registered", st == "KYC Completed", st == "Bank Linked", st == "Funded", since_trade <= 30,
             u.dormant_3m_monthly == 1, u.trade_months_6m >= 4, u.trade_months_6m >= 2]
    labs = ["01 New / in-flight onboarding", "02 KYC-pending (stalled)", "03 Bank-link pending (stalled)", "04 Deposit-pending (stalled)",
            "05 Deposited, never traded (stalled)", "06 First-time trader (<=30d since first trade)", "09 Inactive trader (no activity Aug-Oct)",
            "08 High-engagement trader (>=4 trading months of last 6)", "07 Repeat trader (2-3 trading months of last 6)"]
    return pd.Series(np.select(conds, labs, default="10 Occasional trader (0-1 trading months of last 6)"), index=u.index, name="journey_segment")


def journey_summary(users):
    s = journey_segment(users)
    t = users.assign(journey_segment=s).groupby("journey_segment").agg(users=("user_id", "size"), avg_tenure_days=("tenure_days", "mean"),
        avg_trading_value_6m_inr=("trading_value_6m_inr", "mean"), tickets_per_user=("ticket_count", "mean"))
    t["share_pct"] = 100 * t.users / t.users.sum()
    return t.round(2).reset_index()


def kmeans_features(users):
    km = users[users.tenure_days >= 90].copy()
    f = pd.DataFrame(dict(activity_ratio=km.activity_ratio, trade_months_6m=km.trade_months_6m, log_trading_value_6m=np.log1p(km.trading_value_6m_inr),
                          months_since_last_active=km.months_since_last_active_monthly.fillna(12), log_first_deposit=np.log1p(km.first_deposit_amount_asof_inr.fillna(0)),
                          ticket_count=km.ticket_count.clip(upper=5), funnel_depth=km.furthest_stage_asof.map(C.STAGE_ORDER)), index=km.index)
    return km, f


def kmeans_segments(users, k_range=range(2, 9), seed=C.SEED, min_ari=0.85):
    """K-means on standardised behaviour features (users with tenure >= 90 d). K rule fixed up-front: among k>=3 keep stability ARI >= min_ari,
    then highest silhouette. Returns (labelled users, selection table, profile table)."""
    km_u, f = kmeans_features(users)
    Z = StandardScaler().fit_transform(f); rng = np.random.default_rng(seed)
    sel = []
    for k in k_range:
        km = KMeans(k, n_init=10, random_state=seed).fit(Z)
        labs = [KMeans(k, n_init=3, random_state=s).fit(Z[rng.choice(len(Z), len(Z), replace=True)]).predict(Z) for s in range(5)]
        ari = np.mean([adjusted_rand_score(labs[i], labs[j]) for i in range(5) for j in range(i + 1, 5)])
        sel.append(dict(k=k, inertia=km.inertia_, silhouette=silhouette_score(Z, km.labels_, sample_size=4000, random_state=seed), bootstrap_stability_ari=ari))
    sel = pd.DataFrame(sel); cand = sel[(sel.k >= 3) & (sel.bootstrap_stability_ari >= min_ari)]
    K = int(cand.loc[cand.silhouette.idxmax(), "k"]) if len(cand) else int(sel[sel.k >= 3].loc[sel[sel.k >= 3].silhouette.idxmax(), "k"])
    km = KMeans(K, n_init=20, random_state=seed).fit(Z)
    km_u["kmeans_cluster"] = km.labels_
    prof = f.assign(cluster=km.labels_).groupby("cluster").mean()
    prof["size"] = pd.Series(km.labels_).value_counts().sort_index().values; prof["share_pct"] = 100 * prof["size"] / len(km_u)
    prof["first_trade_rate_pct"] = 100 * km_u.groupby("kmeans_cluster").trade_asof.mean()
    prof["dormant_3m_pct"] = 100 * km_u.groupby("kmeans_cluster").dormant_3m_monthly.mean()
    return km_u, sel.round(4), prof.round(3).reset_index(), K
