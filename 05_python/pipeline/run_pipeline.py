"""One-command pipeline (SYNTHETIC DATA): load -> validate -> EDA -> funnel -> campaign -> cohort -> segmentation -> support -> KPI report.
Usage:  python3 run_pipeline.py [--skip-kmeans]      Outputs: 05_python/outputs/ (tables/*.csv, KPI_Report.md) and assets/charts/python_*.png"""
import argparse, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # 05_python/ (holds the fintech_analytics package)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fintech_analytics import config as C, loading, cleaning, eda, funnel, campaign, cohort, segmentation, support, kpi_report


def main(skip_kmeans=False):
    t0 = time.time(); out = C.OUT_DIR; (out / "tables").mkdir(parents=True, exist_ok=True); C.CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    d = loading.load_all(); u, a, t, c = d["users"], d["activity"], d["tickets"], d["campaigns"]
    chk = cleaning.validate_cleaned(d); chk.to_csv(out / "tables" / "validation_checks.csv", index=False)
    print(f"[1/8] loaded + validated: {int(chk.passed.sum())}/{len(chk)} checks passed")
    if not chk.passed.all(): print(chk[~chk.passed].to_string()); sys.exit(1)
    import pandas as pd
    pd.concat([eda.profile(u, "users"), eda.profile(a, "monthly_activity"), eda.profile(t, "support_tickets"), eda.profile(c, "campaigns")]).to_csv(out / "tables" / "eda_column_profile.csv", index=False)
    cleaning.source_conflict_summary(u, a).to_csv(out / "tables" / "source_conflict_trade.csv")
    for name, fn, arg in [("eda_registrations", eda.plot_registrations, u), ("eda_channel_mix", eda.plot_channel_mix, u), ("eda_first_deposit", eda.plot_deposit_hist, u),
                          ("funnel", funnel.plot_funnel, u), ("retention_curve", cohort.plot_retention_curve, a), ("support_categories", support.plot_category, t)]:
        fn(arg); plt.tight_layout(); plt.savefig(C.CHARTS_DIR / f"python_{name}.png", dpi=130); plt.close("all")
    print("[2/8] EDA tables + charts")
    funnel.funnel_table(u).to_csv(out / "tables" / "funnel_overall.csv"); funnel.funnel_by(u, "acquisition_channel").to_csv(out / "tables" / "funnel_by_channel.csv", index=False)
    funnel.funnel_by(u, "device_type").to_csv(out / "tables" / "funnel_by_device.csv", index=False); funnel.time_to_stage(u).to_csv(out / "tables" / "funnel_time_to_stage.csv")
    print("[3/8] funnel")
    sc = campaign.campaign_scorecard(u, c); sc.to_csv(out / "tables" / "campaign_scorecard.csv", index=False); campaign.channel_scorecard(u).to_csv(out / "tables" / "channel_scorecard.csv", index=False)
    campaign.plot_cost_vs_quality(sc); plt.tight_layout(); plt.savefig(C.CHARTS_DIR / "python_campaign_cost_vs_quality.png", dpi=130); plt.close("all")
    print("[4/8] campaigns")
    m = cohort.retention_matrix(a); m.to_csv(out / "tables" / "cohort_retention_matrix.csv"); cohort.mau_table(u, a).to_csv(out / "tables" / "mau_monthly.csv", index=False)
    cohort.plot_retention_heatmap(m); plt.tight_layout(); plt.savefig(C.CHARTS_DIR / "python_retention_heatmap.png", dpi=130); plt.close("all")
    print("[5/8] cohorts / MAU")
    segmentation.journey_summary(u).to_csv(out / "tables" / "journey_segments.csv", index=False)
    if not skip_kmeans:
        km_u, sel, prof, K = segmentation.kmeans_segments(u); sel.to_csv(out / "tables" / "kmeans_selection.csv", index=False); prof.to_csv(out / "tables" / "kmeans_profile.csv", index=False)
        print(f"[6/8] segmentation (K-means k={K}, n={len(km_u):,})")
    else: print("[6/8] segmentation (journey only; K-means skipped)")
    support.category_table(t).to_csv(out / "tables" / "support_categories.csv", index=False); support.backlog_table(t).to_csv(out / "tables" / "support_backlog.csv", index=False)
    support.monthly_ticket_trend(t).to_csv(out / "tables" / "support_monthly.csv", index=False)
    print("[7/8] support")
    k, cmp_, _ = kpi_report.build_report(d, out)
    print(f"[8/8] KPI report -> {out/'KPI_Report.md'}  | Phase 3 match: {int((cmp_.status=='MATCH').sum())}/{len(cmp_)}  | {time.time()-t0:.0f}s")
    if (cmp_.status != 'MATCH').any(): print(cmp_[cmp_.status != 'MATCH'].to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--skip-kmeans", action="store_true"); main(ap.parse_args().skip_kmeans)
