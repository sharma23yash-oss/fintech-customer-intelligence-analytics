"""Phase 5 - render dashboard MOCKUPS (PNG) and the data-model diagram from the star-schema CSVs (SYNTHETIC data).
These are static matplotlib renderings of the intended Power BI pages - NOT Power BI screenshots. Every number is computed from
06_dashboard/data and cross-asserted against 06_dashboard/validation/DAX_Oracle_Expected_Values.csv.
Run: python3 22_render_mockups.py"""
import sys, textwrap
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "05_python"))
import powerbi_measures as PM
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib import font_manager as fm

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
D = ROOT / "06_dashboard" / "data"; OUT = ROOT / "06_dashboard" / "mockups"; OUT.mkdir(exist_ok=True)
fams = {f.name for f in fm.fontManager.ttflist}
FONT = "Inter" if "Inter" in fams else "DejaVu Sans"
plt.rcParams.update({"font.family": FONT, "axes.unicode_minus": False})

NAVY, CANVAS, CARD, BORDER, INK, SUB, MUTED = "#0B1F3A", "#F4F6FA", "#FFFFFF", "#E3E8EF", "#0B1F3A", "#52606D", "#8A94A0"
BLUE, ORANGE = "#2a78d6", "#eb6834"                                   # categorical slots 1-2 (validated palette)
RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#256abf", "#184f95", "#0d366b"]   # ordinal blue steps 250..700 (nearest-surface >= 2:1)
SEQ = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
GOOD, WARN, BAD = "#0ca30c", "#fab219", "#d03b3b"
W, H = 1600, 900
rd = lambda n, dates=(): pd.read_csv(D / f"{n}.csv", parse_dates=list(dates))
DC, DSEG = rd("DimCampaign"), rd("DimSegment")
FC = rd("FactCustomer", ["RegistrationDate"]); FA = rd("FactActivity", ["ActivityMonthDate", "RegMonthDate"]); FT = rd("FactTicket", ["CreatedDate"])
EXP = pd.read_csv(ROOT / "06_dashboard/validation/DAX_Oracle_Expected_Values.csv"); EXP = EXP[EXP.context == "no filters"].set_index("measure").oracle_value
FC = FC.merge(DC[["CampaignKey", "Channel", "IsPaid"]], on="CampaignKey"); FT = FT.merge(DC[["CampaignKey", "Channel"]], on="CampaignKey")
MONTHS = pd.date_range("2025-11-01", "2026-10-01", freq="MS"); ML = [m.strftime("%b %y") for m in MONTHS]
inr = lambda v: f"Rs {v:,.0f}"


# ------------------------------------------------------------------------------------------ drawing helpers
class Page:
    def __init__(self, title, subtitle, slicers, page_no):
        self.fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=CANVAS)
        self.bg = self.fig.add_axes([0, 0, 1, 1]); self.bg.set_xlim(0, W); self.bg.set_ylim(H, 0); self.bg.axis("off")
        self.bg.add_patch(Rectangle((0, 0), W, 64, color=NAVY))
        self.bg.text(24, 24, title, color="white", fontsize=17, fontweight="semibold", va="center")
        self.bg.text(24, 47, subtitle, color="#B7C4D6", fontsize=9, va="center")
        self.bg.text(W - 24, 24, "SYNTHETIC DATA  |  MOCKUP - not a Power BI screenshot", color="#FAB219", fontsize=9, fontweight="semibold", va="center", ha="right")
        self.bg.text(W - 24, 47, f"Fictional Indian retail brokerage  |  INR  |  snapshot 2026-10-31  |  page {page_no} of 4", color="#B7C4D6", fontsize=8.5, va="center", ha="right")
        x = 24
        for lab, val in slicers:
            w = 30 + 7.0 * len(lab) + 7.6 * len(val)
            self.bg.add_patch(FancyBboxPatch((x, 74), w, 24, boxstyle="round,pad=0,rounding_size=12", fc=CARD, ec=BORDER, lw=1))
            self.bg.text(x + 12, 86, lab, fontsize=8, color=MUTED, va="center"); self.bg.text(x + 12 + 7.0 * len(lab) + 8, 86, val, fontsize=8.5, color=INK, va="center", fontweight="semibold")
            x += w + 8
        self.bg.text(W - 24, 86, "Slicers: month | campaign | city | channel | customer segment", fontsize=8, color=MUTED, va="center", ha="right")
        self.bg.text(24, 890, "All figures are computed from synthetic data (06_dashboard/data) and match 06_dashboard/validation/DAX_Oracle_Expected_Values.csv. "
                     "Inactive 90d / Dormant 3m are churn proxies, not confirmed churn.", fontsize=7.5, color=MUTED, va="center")

    def card(self, x, y, w, h, title, sub=None):
        self.bg.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=6", fc=CARD, ec=BORDER, lw=1))
        self.bg.text(x + 14, y + 17, title, fontsize=10.5, fontweight="semibold", color=INK, va="center")
        if sub: self.bg.text(x + 14, y + 33, sub, fontsize=7.8, color=MUTED, va="center")

    def axes(self, x, y, w, h):
        a = self.fig.add_axes([x / W, 1 - (y + h) / H, w / W, h / H]); a.set_facecolor(CARD)
        for s in ("top", "right"): a.spines[s].set_visible(False)
        for s in ("left", "bottom"): a.spines[s].set_color(BORDER)
        a.tick_params(colors=SUB, labelsize=7.8, length=0); a.grid(axis="y", color=BORDER, lw=0.7); a.set_axisbelow(True); return a

    def kpi(self, x, y, w, h, label, value, sub=None, tone=None):
        self.bg.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=6", fc=CARD, ec=BORDER, lw=1))
        self.bg.add_patch(Rectangle((x, y + 8), 3, h - 16, color=BLUE))
        self.bg.text(x + 14, y + 17, label, fontsize=8.3, color=SUB, va="center")
        self.bg.text(x + 14, y + 44, value, fontsize=19 if len(value) <= 9 else 15.5, fontweight="semibold", color=INK, va="center")
        if sub: self.bg.text(x + 14, y + 66, sub, fontsize=7.4, color=MUTED, va="center")

    def kpis(self, items, y=108, h=78):
        n = len(items); gap = 10; w = (W - 48 - gap * (n - 1)) / n
        for i, it in enumerate(items): self.kpi(24 + i * (w + gap), y, w, h, *it)

    def save(self, name):
        self.fig.savefig(OUT / name, dpi=100, facecolor=CANVAS); plt.close(self.fig)


def hbar(ax, labels, vals, fmt, color=BLUE, xmax=None, colors=None, fs=8):
    y = np.arange(len(vals))[::-1]
    ax.barh(y, vals, color=colors or color, height=max(0.3, min(0.62, 0.62 * len(vals) / 7)))
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=fs, color=INK); ax.grid(False); ax.grid(axis="x", color=BORDER, lw=0.6)
    ax.spines["left"].set_visible(False); ax.set_xticks([]); ax.spines["bottom"].set_visible(False)
    xm = xmax or max(vals) * 1.22; ax.set_xlim(0, xm)
    for yy, v in zip(y, vals): ax.text(v + xm * 0.012, yy, fmt(v), va="center", fontsize=fs, color=INK, fontweight="semibold")


def ml_axis(ax, every=1):
    ax.set_xticks(range(0, 12, every)); ax.set_xticklabels([ML[i].replace(" ", "\n") for i in range(0, 12, every)], fontsize=7.4, linespacing=1.1)


def callout(page, x, y, w, h, title, lines):
    page.card(x, y, w, h, title)
    yy = y + 40
    for ln in lines:
        wrapped = textwrap.wrap(ln, int(w / 6.6))
        page.bg.text(x + 16, yy, "•", fontsize=9, color=BLUE, va="top")
        for k, wl in enumerate(wrapped): page.bg.text(x + 30, yy + 15 * k, wl, fontsize=9, color=INK, va="top")
        yy += 15 * len(wrapped) + 11


# ------------------------------------------------------------------------------------------ shared metrics (same logic as the DAX / oracle)
mature = FC[FC.FunnelMature == 1]
stages = [("Registered", len(mature)), ("KYC completed", int(mature.KYCDone.sum())), ("Bank linked", int(mature.BankLinked.sum())),
          ("First deposit", int(mature.Deposited.sum())), ("First trade", int(mature.Traded.sum())), ("Active (30d)", int(((mature.Traded == 1) & (mature.Active30d == 1)).sum()))]
losses = [stages[i - 1][1] - stages[i][1] for i in range(1, 6)]; loss_share = [l / sum(losses) for l in losses]
assert stages[0][1] == 9116 and stages[-1][1] == 2808 and abs(loss_share[0] - 0.426) < 1e-3
assert EXP["Registered Customers"] == len(FC) and abs(EXP["First Trade Activation Rate"] - stages[4][1] / stages[0][1]) < 1e-9
mau = FA.groupby("ActivityMonthDate").ActiveInMonth.sum().reindex(MONTHS)
regs = FC.groupby(FC.RegistrationDate.dt.to_period("M").dt.to_timestamp()).size().reindex(MONTHS)
assert mau.iloc[-1] == EXP["MAU"] and regs.sum() == 10000
ch_order = DC.drop_duplicates("Channel").sort_values("ChannelSort").Channel.tolist()
spend_ch = DC.groupby("Channel").CampaignSpendINR.sum()


def campaign_table():
    rows = []
    for _, c in DC.iterrows():
        u = FC[FC.CampaignKey == c.CampaignKey]; mt = u[u.FunnelMature == 1]
        kr, tr = mt.KYCDone.mean(), mt.Traded.mean(); cac = c.CampaignSpendINR / len(u) if c.IsPaid == 1 else np.nan
        rows.append(dict(key=c.CampaignKey, channel=c.Channel, paid=c.IsPaid, spend=c.CampaignSpendINR, regs=len(u), kyc_rate=kr, trade_rate=tr, cac=cac,
                         cost_kyc=cac / kr if c.IsPaid else np.nan, cost_trade=cac / tr if c.IsPaid else np.nan, tier=c.Phase3Tier, sig=c.Phase3SignificantAt5pct,
                         m3=FA[(FA.CampaignKey == c.CampaignKey) & (FA.MonthsSinceRegistration == 3)].ActiveInMonth.mean()))
    t = pd.DataFrame(rows); med = t.cost_trade.median(); t["index"] = med / t.cost_trade
    t["signal"] = np.where(t.paid == 0, "n/a", np.where(t["index"] >= 1.15, "Efficient", np.where(t["index"] <= 0.85, "Costly", "In line"))); return t, med


CT, MED = campaign_table()
p3 = pd.read_csv(ROOT / "03_business_analytics" / "summary" / "Campaign_Performance.csv").set_index("campaign_id")
for _, r in CT[CT.paid == 1].iterrows():
    assert abs(r.cost_trade - p3.loc[r.key, "cost_per_first_trade_at_maturity_inr"]) < 0.5 and abs(r.cac - p3.loc[r.key, "cac_inr"]) < 1e-3, r.key
paid_total = FC[FC.IsPaid == 1]; blended_cac = DC.CampaignSpendINR.sum() / len(paid_total); assert abs(blended_cac - EXP["CAC"]) < 1e-6


# ================================================================================ PAGE 1 - Executive overview
def page1():
    p = Page("Executive Overview", "Growth, activation, engagement and support at a glance", [("Month", "Nov 25 - Oct 26"), ("Campaign", "All"), ("City", "All"), ("Channel", "All"), ("Segment", "All")], 1)
    p.kpis([("Registered customers", f"{EXP['Registered Customers']:,.0f}", "Nov 25 - Oct 26"), ("KYC completion rate", f"{EXP['KYC Completion Rate']:.1%}", "mature cohort, n = 9,116"),
            ("First-trade activation", f"{EXP['First Trade Activation Rate']:.1%}", "registered -> first trade"), ("MAU (Oct 26)", f"{EXP['MAU']:,.0f}", f"{EXP['MAU Share of Customers']:.1%} of customers"),
            ("30-day retention", f"{EXP['30-Day Retention']:.1%}", "active last 30 days (eligible)"), ("CAC (blended, paid)", inr(EXP["CAC"]), "spend / paid registrations"),
            ("Campaign spend", inr(EXP["Total Campaign Spend"]), "recorded, 10 campaigns"), ("Support tickets", f"{EXP['Tickets']:,.0f}", f"{EXP['Tickets per 1000 Customers']:.0f} per 1,000 customers")])
    top, rh = 200, 320
    # monthly acquisition
    p.card(24, top, 500, rh, "Monthly acquisition", "Registered customers per month")
    a = p.axes(44, top + 52, 464, rh - 76); a.bar(range(12), regs.values, color=BLUE, width=0.66); ml_axis(a); a.set_yticks([])
    a.spines["left"].set_visible(False); a.grid(False)
    for i, v in enumerate(regs.values): a.text(i, v + regs.max() * 0.015, f"{v:,.0f}", ha="center", fontsize=7.4, color=INK)
    a.set_ylim(0, regs.max() * 1.12)
    # funnel
    p.card(536, top, 520, rh, "Customer activation funnel", "Mature cohort (registered before Oct 26); share of registered")
    a = p.axes(640, top + 52, 396, rh - 76)
    hbar(a, [s[0] for s in stages], [s[1] for s in stages], lambda v: f"{v:,.0f}  ({v / stages[0][1]:.0%})", colors=RAMP, xmax=stages[0][1] * 1.42)
    p.bg.text(552, top + rh - 14, f"Largest step loss: registered -> KYC ({loss_share[0]:.1%} of all funnel losses)", fontsize=8, color=SUB, va="center")
    # channel performance
    p.card(1068, top, 508, rh, "Channel performance", "First-trade activation rate (mature) | registrations | CAC")
    cp = FC[FC.FunnelMature == 1].groupby("Channel").Traded.mean().reindex(ch_order); nreg = FC.groupby("Channel").size().reindex(ch_order)
    cac_ch = (spend_ch / nreg).where(spend_ch > 0)
    o = cp.sort_values(ascending=False).index.tolist(); a = p.axes(1180, top + 52, 380, rh - 76)
    hbar(a, o, [cp[c] for c in o], lambda v: f"{v:.1%}", xmax=cp.max() * 1.7)
    for yy, c in zip(np.arange(len(o))[::-1], o):
        a.text(cp.max() * 1.66, yy, f"{nreg[c]:,} | " + (f"Rs {cac_ch[c]:,.0f}" if not np.isnan(cac_ch[c]) else "no spend"), ha="right", va="center", fontsize=7.6, color=SUB)
    # engagement trend
    top2 = top + rh + 12; rh2 = 900 - 20 - top2 - 6
    p.card(24, top2, 760, rh2, "Customer engagement trend", "Monthly active users (customers with activity in the month)")
    a = p.axes(44, top2 + 52, 724, rh2 - 88); a.plot(range(12), mau.values, color=BLUE, lw=2.2, marker="o", ms=5, mfc=CARD, mew=1.8); ml_axis(a); a.set_yticks([]); a.spines["left"].set_visible(False); a.grid(False)
    for i in (0, 5, 11): a.text(i, mau.values[i] + mau.max() * 0.06, f"{mau.values[i]:,.0f}", ha="center", fontsize=8.2, color=INK, fontweight="semibold")
    a.set_ylim(0, mau.max() * 1.2)
    best = cp.drop("Organic").idxmax(); worst = cp.idxmin(); pdr, odr = FC[(FC.IsPaid == 1) & (FC.FunnelMature == 1)].Traded.mean(), FC[(FC.IsPaid == 0) & (FC.FunnelMature == 1)].Traded.mean()
    callout(p, 796, top2, 780, rh2, "What the data says (Phase 3 findings)", [
        f"KYC is the biggest onboarding bottleneck: {losses[0]:,} of {sum(losses):,} funnel losses ({loss_share[0]:.1%}); step conversion {stages[1][1] / stages[0][1]:.1%}.",
        f"End-to-end activation is {EXP['First Trade Activation Rate']:.1%}; {mature.Deposited.sum() - mature.Traded.sum():,} funded customers have not traded yet (idle deposits, not revenue).",
        f"Channel quality differs: {best} activates {cp[best]:.1%} of mature registrants at CAC Rs {cac_ch[best]:,.0f}; {worst} activates {cp[worst]:.1%} at CAC Rs {cac_ch[worst]:,.0f}.",
        f"Organic registrants activate at {odr:.1%} versus {pdr:.1%} for paid; organic has no recorded spend, so no CAC.",
        f"Retention after registration: M1 {EXP['M1 Retention']:.1%}, M3 {EXP['M3 Retention']:.1%}, M6 {EXP['M6 Retention']:.1%}; {EXP['Dormant 3m Rate']:.1%} of customers are dormant (3-month proxy, not churn).",
        f"Support load is {EXP['Tickets per 1000 Customers']:.0f} tickets per 1,000 customers; {int(EXP['Backlog over 90 Days'])} unresolved tickets are older than 90 days.",
        "Associations only: these are observational patterns in synthetic data, not proof that a channel or campaign caused the difference."])
    p.save("Page1_Executive_Overview.png")


# ================================================================================ PAGE 2 - Acquisition & marketing
def page2():
    p = Page("Acquisition & Marketing", "Campaign efficiency, channel mix, geography and device", [("Month", "Nov 25 - Oct 26"), ("Campaign", "All"), ("City", "All"), ("Channel", "All"), ("Segment", "All")], 2)
    pdf = CT[CT.paid == 1]
    p.kpis([("Total campaign spend", inr(DC.CampaignSpendINR.sum()), "recorded, paid campaigns"), ("Paid registrations", f"{len(paid_total):,}", f"{len(paid_total) / len(FC):.1%} of all"),
            ("Blended CAC", inr(blended_cac), "spend / paid registrations"), ("Median cost per KYC", inr(pdf.cost_kyc.median()), "CAC / mature KYC rate"),
            ("Median cost per 1st trade", inr(MED), "CAC / mature trade rate"), ("Organic registrations", f"{(FC.IsPaid == 0).sum():,}", f"{(FC.IsPaid == 0).mean():.1%} of all, no spend")])
    top, rh = 200, 318
    p.card(24, top, 470, rh, "Cost per first trade by paid campaign", f"Rs per first-trading customer | dashed line = peer median Rs {MED:,.0f}")
    s = pdf.sort_values("cost_trade"); a = p.axes(100, top + 52, 380, rh - 90)
    cols = [GOOD if i >= 1.15 else BAD if i <= 0.85 else BLUE for i in s["index"]]
    a.axvline(MED, color=SUB, lw=1, ls="--", zorder=0); hbar(a, s.key, s.cost_trade.values, lambda v: f"Rs {v:,.0f}", colors=cols, xmax=s.cost_trade.max() * 1.25)
    for t_ in a.texts: t_.set_bbox(dict(fc=CARD, ec="none", pad=1.5))
    for lx, col, lab in ((40, GOOD, "efficient (index >= 1.15)"), (190, BAD, "costly (index <= 0.85)"), (320, BLUE, "in line")):
        p.bg.add_patch(Rectangle((lx, top + rh - 19), 9, 9, color=col)); p.bg.text(lx + 14, top + rh - 14, lab, fontsize=7.6, color=SUB, va="center")
    p.card(506, top, 380, rh, "CAC by channel", "Recorded spend / registrations (paid channels)")
    pc = [c for c in ch_order if spend_ch[c] > 0]; cacv = {c: spend_ch[c] / (FC.Channel == c).sum() for c in pc}; o = sorted(pc, key=lambda c: -cacv[c])
    a = p.axes(600, top + 52, 270, rh - 66); hbar(a, o, [cacv[c] for c in o], lambda v: f"Rs {v:,.0f}", xmax=max(cacv.values()) * 1.35)
    p.card(898, top, 330, rh, "Paid vs organic acquisition", "Share of registrations")
    a = p.axes(918, top + 70, 290, 70); paid_n, org_n = len(paid_total), int((FC.IsPaid == 0).sum())
    a.barh([0], [paid_n], color=BLUE, height=0.6); a.barh([0], [org_n], left=[paid_n], color=ORANGE, height=0.6, edgecolor=CARD, lw=2)
    a.set_xlim(0, paid_n + org_n); a.set_ylim(-0.5, 1.0); a.axis("off")
    a.text(paid_n / 2, 0, f"Paid {paid_n / 10000:.1%}", ha="center", va="center", color="white", fontsize=9, fontweight="semibold"); a.text(paid_n + org_n, 0.52, f"Organic {org_n / 10000:.1%}", ha="right", va="bottom", color=INK, fontsize=9, fontweight="semibold")
    ft = FC.groupby("IsPaid").apply(lambda d: d[d.FunnelMature == 1].Traded.mean())
    for k, (lab, val, col) in enumerate([("Paid", ft[1], BLUE), ("Organic", ft[0], ORANGE)]):
        p.bg.add_patch(Rectangle((918, top + 170 + k * 34), 10, 10, color=col)); p.bg.text(936, top + 175 + k * 34, f"{lab}: first-trade activation {val:.1%}", fontsize=8.6, color=INK, va="center")
    p.bg.text(918, top + 258, "Organic cost is not recorded, so it has no CAC", fontsize=7.8, color=SUB, va="center"); p.bg.text(918, top + 273, "(shown blank, not zero).", fontsize=7.8, color=SUB, va="center")
    p.card(1240, top, 336, rh, "Registrations by city", "All campaigns"); cty = FC.groupby("CityKey").size().sort_values(ascending=False)
    a = p.axes(1320, top + 52, 240, rh - 66); hbar(a, cty.index, cty.values, lambda v: f"{v:,}", xmax=cty.max() * 1.28, fs=7.6)
    top2 = top + rh + 12; rh2 = 900 - 20 - top2 - 6
    p.card(24, top2, 360, rh2, "Registrations by device"); dev = FC.groupby("DeviceKey").size().sort_values(ascending=False)
    a = p.axes(90, top2 + 40, 270, 112); hbar(a, dev.index, dev.values, lambda v: f"{v:,}  ({v / 10000:.0%})", xmax=dev.max() * 1.5)
    p.bg.text(38, top2 + 178, "First-trade activation by device (mature cohort)", fontsize=9.2, fontweight="semibold", color=INK, va="center")
    dact = FC[FC.FunnelMature == 1].groupby("DeviceKey").Traded.mean().reindex(dev.index); a = p.axes(90, top2 + 196, 270, 112)
    hbar(a, dact.index, dact.values, lambda v: f"{v:.1%}", xmax=dact.max() * 1.5)
    p.card(396, top2, 1180, rh2, "Campaign ranking & budget optimisation indicators", "Directional only: the data has no revenue, so signals compare cost per first trade to the peer median - they are not ROI")
    hdr = ["Campaign", "Channel", "Spend", "Regs", "CAC", "Cost / KYC", "Cost / 1st trade", "Index", "Budget signal", "Phase 3 tier"]; xs = [412, 490, 590, 680, 750, 830, 930, 1050, 1120, 1250]
    for x, h_ in zip(xs, hdr): p.bg.text(x, top2 + 52, h_, fontsize=7.8, color=SUB, fontweight="semibold", va="center")
    p.bg.plot([408, 1560], [top2 + 62, top2 + 62], color=BORDER, lw=1)
    T = CT.sort_values(["paid", "cost_trade"], ascending=[False, True]); rh_ = (rh2 - 76) / len(T)
    for i, r in enumerate(T.itertuples()):
        yy = top2 + 62 + rh_ * (i + 0.5); f = lambda v: "-" if np.isnan(v) else f"Rs {v:,.0f}"
        sig = {"Efficient": ("▲ Efficient", GOOD), "Costly": ("▼ Costly", BAD), "In line": ("● In line", SUB), "n/a": ("n/a (organic)", MUTED)}[r.signal]
        vals = [r.key, r.channel, f"{r.spend:,.0f}" if r.paid else "-", f"{r.regs:,}", f(r.cac), f(r.cost_kyc), f(r.cost_trade), "-" if np.isnan(r.index) else f"{r.index:.2f}", sig[0], r.tier.split(" - ")[0] + " - " + r.tier.split(" - ")[1][:22]]
        for x, v, k in zip(xs, vals, range(10)): p.bg.text(x, yy, v, fontsize=8, color=sig[1] if k == 8 else INK, va="center", fontweight="semibold" if k in (0, 8) else "normal")
    p.save("Page2_Acquisition_Marketing.png")


# ================================================================================ PAGE 3 - Retention & segmentation
def page3():
    p = Page("Retention & Segmentation", "Cohort retention, engagement, inactivity and customer segments", [("Month", "Nov 25 - Oct 26"), ("Campaign", "All"), ("City", "All"), ("Channel", "All"), ("Segment", "All")], 3)
    p.kpis([("MAU (Oct 26)", f"{EXP['MAU']:,.0f}", f"{EXP['MAU Share of Customers']:.1%} of customers"), ("M1 retention", f"{EXP['M1 Retention']:.1%}", "active 1 month after reg."), ("M3 retention", f"{EXP['M3 Retention']:.1%}", "active 3 months after reg."),
            ("M6 retention", f"{EXP['M6 Retention']:.1%}", "active 6 months after reg."), ("Inactive > 90 days", f"{EXP['Inactive 90d Rate']:.1%}", "proxy, not churn"), ("Dormant 3m", f"{EXP['Dormant 3m Rate']:.1%}", "proxy, not churn"),
            ("Repeat trader share", f"{EXP['Repeat Trader Share']:.1%}", "of ever-traders")])
    top, rh = 200, 330
    p.card(24, top, 760, rh, "Cohort retention heatmap", "Share of the registration-month cohort active k months later (k = months since registration)")
    piv = FA.groupby([FA.RegMonthDate, "MonthsSinceRegistration"]).ActiveInMonth.mean().unstack(); piv = piv.reindex(MONTHS); piv = piv[[c for c in range(0, 12)]]
    a = p.axes(100, top + 62, 664, rh - 80); a.grid(False); vmax = np.nanmax(piv.values); vmin = np.nanmin(piv.values)
    for i in range(12):
        for j in range(12):
            v = piv.values[i, j]
            if np.isnan(v): continue
            idx = int(round((v - vmin) / (vmax - vmin) * (len(SEQ) - 1))); a.add_patch(Rectangle((j, 11 - i), 1, 1, fc=SEQ[idx], ec=CARD, lw=1.5))
            a.text(j + 0.5, 11 - i + 0.5, f"{v:.0%}", ha="center", va="center", fontsize=6.9, color="white" if idx >= 6 else INK)
    a.set_xlim(0, 12); a.set_ylim(0, 12); a.set_xticks(np.arange(12) + 0.5); a.set_xticklabels([f"M{k}" for k in range(12)], fontsize=7.4); a.set_yticks(np.arange(12) + 0.5)
    a.set_yticklabels(ML[::-1], fontsize=7.4); a.spines["left"].set_visible(False); a.spines["bottom"].set_visible(False)
    p.card(796, top, 390, rh, "Inactive-customer distribution", "Days since last activity (customers with 31+ days tenure)")
    e = FC[FC.Eligible30d == 1]; ib = e.groupby(["InactivitySort", "InactivityBucket"]).size().reset_index(name="n").sort_values("InactivitySort"); ib["share"] = ib.n / ib.n.sum()
    a = p.axes(826, top + 52, 340, rh - 74); a.bar(range(len(ib)), ib.share, color=[RAMP[i] for i in (0, 1, 2, 4, 5)], width=0.66); a.set_xticks(range(len(ib))); a.set_xticklabels(ib.InactivityBucket, fontsize=7.8); a.set_yticks([]); a.spines["left"].set_visible(False); a.grid(False)
    for i, v in enumerate(ib.share): a.text(i, v + 0.008, f"{v:.1%}", ha="center", fontsize=8, color=INK, fontweight="semibold")
    a.set_ylim(0, ib.share.max() * 1.18)
    p.card(1198, top, 378, rh, "M3 retention by acquisition channel", "Active 3 months after registration")
    m3 = FA.merge(DC[["CampaignKey", "Channel"]], on="CampaignKey"); m3 = m3[m3.MonthsSinceRegistration == 3].groupby("Channel").ActiveInMonth.mean().sort_values(ascending=False)
    a = p.axes(1290, top + 52, 270, rh - 66); hbar(a, m3.index, m3.values, lambda v: f"{v:.1%}", xmax=m3.max() * 1.3)
    top2 = top + rh + 12; rh2 = 900 - 20 - top2 - 6
    p.card(24, top2, 760, rh2, "Customer segments (journey rule, snapshot 2026-10-31)", "Customers per segment; segments are mutually exclusive")
    seg = FC.groupby("SegmentKey").size().reindex(DSEG.SegmentKey).values; names = list(DSEG.SegmentName)
    o = np.argsort(-seg); a = p.axes(340, top2 + 44, 420, rh2 - 56); hbar(a, [names[i] for i in o], seg[o], lambda v: f"{v:,}  ({v / 10000:.1%})", xmax=seg.max() * 1.45, fs=7.6)
    p.card(796, top2, 380, rh2, "Trading activity", "Customers who traded in the month")
    tr = FA.groupby("ActivityMonthDate").TradedInMonth.sum().reindex(MONTHS); a = p.axes(824, top2 + 52, 336, rh2 - 88)
    a.plot(range(12), tr.values, color=BLUE, lw=2.2, marker="o", ms=4.5, mfc=CARD, mew=1.6); ml_axis(a, 2); a.set_yticks([]); a.spines["left"].set_visible(False); a.grid(False); a.set_ylim(0, tr.max() * 1.2)
    for i in (0, 11): a.text(i, tr.values[i] + tr.max() * 0.06, f"{tr.values[i]:,.0f}", ha="center", fontsize=8, color=INK, fontweight="semibold")
    callout(p, 1188, top2, 388, rh2, "Reading the heatmap", [f"Retention falls from {EXP['M1 Retention']:.0%} at M1 to {EXP['M6 Retention']:.0%} at M6 on average.", "Recent cohorts have fewer observed months, so their right-hand cells are blank by design.",
                                                         "Inactivity and dormancy are proxies - not confirmed churn.", "Segments are a snapshot as of 2026-10-31; a month slicer filters each customer by registration month, not by segment history."])
    p.save("Page3_Retention_Segmentation.png")


# ================================================================================ PAGE 4 - Customer operations
def page4():
    p = Page("Customer Operations", "Support demand, resolution speed, satisfaction and onboarding friction", [("Month", "Nov 25 - Oct 26"), ("Campaign", "All"), ("City", "All"), ("Channel", "All"), ("Segment", "All")], 4)
    p.kpis([("Support tickets", f"{EXP['Tickets']:,.0f}", "Nov 25 - Oct 26"), ("Tickets / 1,000 customers", f"{EXP['Tickets per 1000 Customers']:.0f}", "vs customers to date"), ("Resolved rate", f"{EXP['Resolved Rate']:.1%}", "of all tickets"),
            ("Escalation rate", f"{EXP['Escalated Tickets'] / EXP['Tickets']:.1%}", f"{EXP['Escalated Tickets']:.0f} escalated"), ("Median resolution", f"{EXP['Median Resolution Hours']:.1f} h", "resolved tickets"),
            ("CSAT (1-5)", f"{EXP['CSAT']:.2f}", "rated tickets"), ("Backlog > 90 days", f"{EXP['Backlog over 90 Days']:.0f}", "unresolved tickets")])
    top, rh = 200, 330
    p.card(24, top, 500, rh, "Ticket volume", "Tickets created per month"); tv = FT.groupby(FT.CreatedDate.dt.to_period("M").dt.to_timestamp()).size().reindex(MONTHS)
    a = p.axes(44, top + 52, 464, rh - 76); a.bar(range(12), tv.values, color=BLUE, width=0.66); ml_axis(a); a.set_yticks([]); a.spines["left"].set_visible(False); a.grid(False); a.set_ylim(0, tv.max() * 1.14)
    for i, v in enumerate(tv.values): a.text(i, v + tv.max() * 0.015, f"{v:,}", ha="center", fontsize=7.4, color=INK)
    p.card(536, top, 520, rh, "Tickets per 1,000 customers", "Monthly tickets / customers registered to date x 1,000"); cum = regs.cumsum(); tp = tv / cum * 1000
    a = p.axes(556, top + 52, 484, rh - 76); a.plot(range(12), tp.values, color=BLUE, lw=2.2, marker="o", ms=4.5, mfc=CARD, mew=1.6); ml_axis(a); a.set_yticks([]); a.spines["left"].set_visible(False); a.grid(False); a.set_ylim(0, tp.max() * 1.2)
    for i in (0, 5, 11): a.text(i, tp.values[i] + tp.max() * 0.06, f"{tp.values[i]:.0f}", ha="center", fontsize=8, color=INK, fontweight="semibold")
    p.card(1068, top, 508, rh, "Ticket categories", "Tickets | median resolution hours | CSAT")
    cat = FT.groupby("Category").agg(n=("TicketID", "size"), med=("ResolutionHours", "median"), cs=("CSAT", "mean")).sort_values("n", ascending=False); a = p.axes(1200, top + 52, 360, rh - 66)
    hbar(a, cat.index, cat.n.values, lambda v: f"{v:,}", xmax=cat.n.max() * 1.9)
    for yy, (c, r) in zip(np.arange(len(cat))[::-1], cat.iterrows()): a.text(cat.n.max() * 1.88, yy, f"{r.med:.1f} h | CSAT {r.cs:.2f}", ha="right", va="center", fontsize=7.6, color=SUB)
    top2 = top + rh + 12; rh2 = 900 - 20 - top2 - 6
    p.card(24, top2, 380, rh2, "Priority distribution", "Share of tickets"); pr = FT.groupby("Priority").size().reindex(["High", "Medium", "Low"]); a = p.axes(110, top2 + 44, 280, rh2 - 56)
    hbar(a, pr.index, pr.values, lambda v: f"{v:,}  ({v / pr.sum():.1%})", colors=[RAMP[5], RAMP[3], RAMP[1]], xmax=pr.max() * 1.6)
    p.card(416, top2, 400, rh2, "Backlog ageing (unresolved tickets)", "Open + escalated, by age"); bk = FT[FT.IsUnresolved == 1].groupby(["BacklogSort", "BacklogAgeBucket"]).size().reset_index(name="n").sort_values("BacklogSort")
    a = p.axes(436, top2 + 52, 364, rh2 - 74); a.bar(range(len(bk)), bk.n, color=BLUE, width=0.66); a.set_xticks(range(len(bk))); a.set_xticklabels(bk.BacklogAgeBucket, fontsize=7.6); a.set_yticks([]); a.spines["left"].set_visible(False); a.grid(False)
    for i, v in enumerate(bk.n): a.text(i, v + bk.n.max() * 0.02, f"{v:,}", ha="center", fontsize=8, color=INK, fontweight="semibold")
    a.set_ylim(0, bk.n.max() * 1.15)
    p.card(828, top2, 748, rh2, "Onboarding bottlenecks in support", "Tickets that relate to an onboarding stage | share raised while that stage was still pending")
    ob = FT[FT.RelatedFunnelStage != "none"].groupby("RelatedFunnelStage").agg(n=("TicketID", "size"), pend=("StagePendingAtTicket", "mean")).sort_values("n", ascending=False)
    a = p.axes(960, top2 + 52, 600, rh2 - 66); hbar(a, [{"kyc": "KYC", "bank": "Bank linking", "deposit": "First deposit", "trade": "First trade"}.get(i, i) for i in ob.index], ob.n.values, lambda v: f"{v:,}", xmax=ob.n.max() * 1.9)
    for yy, (c, r) in zip(np.arange(len(ob))[::-1], ob.iterrows()): a.text(ob.n.max() * 1.88, yy, f"{r.pend:.0%} raised while stage pending", ha="right", va="center", fontsize=7.8, color=SUB)
    p.save("Page4_Customer_Operations.png")


# ================================================================================ Data model diagram
def erd():
    fig = plt.figure(figsize=(16, 9), dpi=100, facecolor=CARD); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")
    ax.text(24, 30, "Power BI data model - star schema", fontsize=16, fontweight="semibold", color=INK, va="center")
    ax.text(24, 54, "Synthetic data  |  every relationship is one-to-many, single direction (dimension -> fact)  |  15 relationships, all active  |  DIAGRAM - not a Power BI screenshot", fontsize=8.5, color=SUB, va="center")
    box = {}

    def table(name, x, y, w, cols, color, rows):
        h = 40 + 17 * len(cols); box[name] = (x, y, w, h)
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=5", fc=CARD, ec=color, lw=1.6, zorder=3))
        ax.add_patch(Rectangle((x, y), w, 26, color=color, zorder=4)); ax.text(x + 10, y + 13, name, color="white", fontsize=9.6, fontweight="semibold", va="center", zorder=5)
        ax.text(x + w - 10, y + 13, rows, color="white", fontsize=7.8, va="center", ha="right", zorder=5)
        for i, c in enumerate(cols): ax.text(x + 10, y + 42 + 17 * i, c, fontsize=7.8, color=INK, va="center", zorder=5)

    table("DimCampaign", 40, 90, 340, ["CampaignKey (key)", "CampaignName, Channel (sort: ChannelSort)", "SourcePlatform, ChannelGroup, AcquisitionType", "IsPaid, CampaignSpendINR, SpendBasis", "Phase3Tier, Phase3OverallScore", "Phase3FirstTradeP_Holm, Phase3SignificantAt5pct"], BLUE, "10 rows")
    table("DimCity", 430, 90, 230, ["CityKey (key, sort: CitySort)"], BLUE, "11 rows")
    table("DimDevice", 700, 90, 230, ["DeviceKey (key, sort: DeviceSort)"], BLUE, "3 rows")
    table("DimSegment", 970, 90, 290, ["SegmentKey (key)", "SegmentName, SegmentGroup", "RecommendedAction"], BLUE, "10 rows")
    table("DimStage (disconnected)", 1300, 90, 260, ["StageOrder, StageName", "funnel axis via SELECTEDVALUE"], MUTED, "6 rows")
    FY = 330
    table("FactCustomer", 40, FY, 470, ["CustomerID (grain)", "RegistrationDate", "CampaignKey, CityKey, DeviceKey, SegmentKey", "KYCDone, BankLinked, Deposited, Traded (+ dates)", "FunnelMature, Eligible30d, Eligible90d", "Days* stage lags, Active30d, Inactive90d, Dormant3m", "TenureDays, MonthsObserved, TradeMonths", "TradingValue6mINR, M1/M3/M6Retained", "DaysSinceLastActivity, InactivityBucket"], "#256abf", "10,000 rows")
    table("FactActivity", 560, FY, 470, ["CustomerID, MonthsSinceRegistration", "ActivityMonthDate  (active -> DimDate)", "RegMonthDate  (cohort axis, no relationship)", "CampaignKey, CityKey, DeviceKey, SegmentKey", "ActiveInMonth, TradedInMonth, DepositedInMonth", "TradeCount, TradingValueINR", "DepositValueINR, WithdrawalValueINR, NetFlowINR"], "#256abf", "64,645 rows")
    table("FactTicket", 1080, FY, 480, ["TicketID (grain), CustomerID", "CreatedDate", "CampaignKey, CityKey, DeviceKey, SegmentKey", "Category, Priority, Status", "IsResolved, IsUnresolved, IsEscalated", "ResolutionHours, CSAT, TicketAgeDays", "BacklogAgeBucket, RelatedFunnelStage", "StagePendingAtTicket"], "#256abf", "7,614 rows")
    table("DimDate (calculated)", 560, 640, 470, ["Date (key) - marked as date table", "Year, Quarter, MonthNumber, MonthStart", "MonthLabel (sort: MonthSort), WeekdayName, IsMonthStart"], NAVY, "365 rows")
    cx = lambda n: box[n][0] + box[n][2] / 2; bot = lambda n: box[n][1] + box[n][3]
    BUS = 275
    for d in ("DimCampaign", "DimCity", "DimDevice", "DimSegment"):
        ax.plot([cx(d), cx(d)], [bot(d), BUS], color=SUB, lw=1.3, zorder=1); ax.text(cx(d) + 6, bot(d) + 12, "1", fontsize=8.5, color=INK, fontweight="semibold")
    ax.plot([cx("DimCampaign"), cx("FactTicket")], [BUS, BUS], color=SUB, lw=1.3, zorder=1)
    for f in ("FactCustomer", "FactActivity", "FactTicket"):
        ax.plot([cx(f), cx(f)], [BUS, FY], color=SUB, lw=1.3, zorder=1); ax.text(cx(f) + 6, FY - 8, "*", fontsize=11, color=INK, fontweight="semibold")
    ax.text(290, BUS + 16, "CampaignKey | CityKey | DeviceKey | SegmentKey - each dimension filters all three facts", fontsize=8, color=SUB, va="center")
    BUS2 = 590
    ax.plot([cx("FactCustomer"), cx("FactTicket")], [BUS2, BUS2], color=SUB, lw=1.3, zorder=1)
    ax.plot([cx("DimDate (calculated)")] * 2, [BUS2, 640], color=SUB, lw=1.3, zorder=1); ax.text(cx("DimDate (calculated)") + 6, 628, "1", fontsize=8.5, color=INK, fontweight="semibold")
    for f, lab in (("FactCustomer", "RegistrationDate"), ("FactTicket", "CreatedDate")):
        ax.plot([cx(f)] * 2, [BUS2, bot(f)], color=SUB, lw=1.3, zorder=1); ax.text(cx(f) + 6, bot(f) + 14, "*", fontsize=11, color=INK, fontweight="semibold"); ax.text(cx(f) + 16, BUS2 - 8, f"{f}[{lab}]", fontsize=8, color=SUB)
    x_act = cx("FactActivity") - 60; ax.plot([x_act] * 2, [BUS2, bot("FactActivity")], color=SUB, lw=1.3, zorder=1); ax.text(x_act + 6, bot("FactActivity") + 14, "*", fontsize=11, color=INK, fontweight="semibold")
    ax.text(x_act - 8, BUS2 - 8, "FactActivity[ActivityMonthDate]", fontsize=8, color=SUB, ha="right")
    ax.text(40, 780, "Grain: FactCustomer = one row per customer | FactActivity = one row per customer per observed month | FactTicket = one row per support ticket.", fontsize=8.8, color=SUB, va="center")
    ax.text(40, 804, f"Measures live in a hidden _Measures table ({len(PM.M)} measures in 7 display folders). Dimension keys are repeated on each fact, so every slicer filters all three facts directly.", fontsize=8.8, color=SUB, va="center")
    ax.text(40, 828, "DimStage is intentionally disconnected: it only supplies the funnel stage axis, and measures switch on SELECTEDVALUE(DimStage[StageName]).", fontsize=8.8, color=SUB, va="center")
    fig.savefig(OUT / "Data_Model_Star_Schema.png", dpi=100, facecolor=CARD); plt.close(fig)


for fn in (page1, page2, page3, page4, erd): fn()
print("mockups written:", *sorted(p.name for p in OUT.glob("*.png")), sep="\n  ")
