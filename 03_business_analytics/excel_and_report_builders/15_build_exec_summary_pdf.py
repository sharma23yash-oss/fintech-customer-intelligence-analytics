"""
Phase 3 - Executive_Summary.pdf (2-3 pages) built with reportlab from Phase 3 results.
Run: python3 15_build_exec_summary_pdf.py        Output: reports/Fintech_Executive_Summary.pdf
All data are synthetic.
"""
import json
from pathlib import Path
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from PIL import Image as PILImage

import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "05_python")); from fintech_analytics import config as CFG
BUILD = ROOT / "reports" / "_build"
CH = CFG.CHARTS_DIR
blocks = json.load(open(BUILD / "report_content.json"))
R = json.load(open(CFG.p3_path("results.json")))
rec = pd.read_csv(CFG.p3_path("m8_prioritisation.csv"), keep_default_na=False)
F = R["funnel"]
NAVY, BLUE, INK, MUTED = colors.HexColor("#0D366B"), colors.HexColor("#1C5CAB"), colors.HexColor("#1B1B1A"), colors.HexColor("#52514E")
S = lambda name, **k: ParagraphStyle(name, fontName=k.pop("font", "Helvetica"), textColor=k.pop("color", INK), **k)
st = dict(
    title=S("t", fontSize=21, leading=25, font="Helvetica-Bold", color=NAVY, spaceAfter=4),
    sub=S("s", fontSize=10.5, leading=14, color=MUTED, spaceAfter=6),
    warn=S("w", fontSize=8.8, leading=11.5, font="Helvetica-Bold", color=colors.HexColor("#9A3412"), spaceAfter=8),
    h=S("h", fontSize=12.5, leading=16, font="Helvetica-Bold", color=BLUE, spaceBefore=8, spaceAfter=4),
    p=S("p", fontSize=9.4, leading=13, spaceAfter=4),
    b=S("b", fontSize=9.4, leading=12.8, leftIndent=14, bulletIndent=2, spaceAfter=4),
    cap=S("c", fontSize=7.6, leading=10, color=MUTED, spaceAfter=6),
    kv=S("kv", fontSize=17, leading=20, font="Helvetica-Bold", color=NAVY),
    kl=S("kl", fontSize=7.8, leading=10, color=MUTED),
    small=S("sm", fontSize=8.3, leading=11.2, color=MUTED),
)


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def img(name, w):
    pw, ph = PILImage.open(CH / ("phase3_" + name)).size
    return Image(str(CH / ("phase3_" + name)), width=w, height=w * ph / pw)


# five findings text from the report content (first bullets block after the "five most important" heading)
idx = next(i for i, b in enumerate(blocks) if b.get("text") == "The five most important findings")
top5 = blocks[idx + 1]["items"]
heads = ["KYC drives the largest loss", "Few registrants reach a first trade", "Referral beats paid on quality and cost", "Retention decays steadily", "Support load sits in onboarding"]

story = [Paragraph("Fintech Growth Analytics: Executive Summary", st["title"]),
         Paragraph("Customer acquisition, funnel, retention, campaigns and support | Prepared by Yash Sharma | Snapshot 2026-10-31", st["sub"]),
         Paragraph("SYNTHETIC DATA: fictional dataset of 10,000 users (Nov 2025 - Oct 2026, INR). Not real customer, company or market data. No revenue, profit or ROI is calculated. Portfolio project, not professional brokerage work.", st["warn"])]

tiles = [(f"{F['KYC Completed']['conv_reg']*100:.1f}%", "Registered -> KYC"), (f"{F['First Trade']['conv_reg']*100:.1f}%", "Registered -> first trade"),
         (f"{R['m3']*100:.1f}%", "M3 retention"), (f"{R['median_days_reg_to_trade']:.0f} days", "Median reg. -> first trade"), (f"Rs {2690000/8122:,.0f}", "Blended paid CAC")]
cells = [[Paragraph(v, st["kv"]), ] for v, _ in tiles]
t = Table([[Paragraph(v, st["kv"]) for v, _ in tiles], [Paragraph(l, st["kl"]) for _, l in tiles]], colWidths=[1.44 * inch] * 5)
t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F6FA")), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, 0), 7), ("BOTTOMPADDING", (0, 1), (-1, 1), 7),
                       ("LINEAFTER", (0, 0), (-2, -1), 2, colors.white)]))
story += [t, Paragraph("Headline KPIs: mature cohorts (registered before Oct 2026, n=9,116). ACTUAL values calculated from the synthetic data.", st["cap"]), Spacer(1, 4)]
story.append(Paragraph("The five most important findings", st["h"]))
for h, txt in zip(heads, top5):
    story.append(Paragraph(f"<b>{esc(h)}.</b> {esc(txt)}", st["b"], bulletText="•"))

story.append(Paragraph("Priorities (recommendations, not results)", st["h"]))
for r in rec.head(6).itertuples():
    story.append(Paragraph(f"<b>{r.priority_rank}.</b> {esc(r.recommendation)} <font color='#52514E'>[impact {r.impact}, complexity {r.complexity}, {esc(r.time_to_benefit)}]</font>", st["b"], bulletText="•"))

story.append(KeepTogether([Paragraph("Funnel and campaign efficiency", st["h"]), img("c01_funnel.png", 6.2 * inch), Spacer(1, 4), img("c04_cost_per_first_trader.png", 6.2 * inch)]))
story.append(KeepTogether([Paragraph("Retention", st["h"]), img("c05_retention.png", 6.6 * inch)]))
story.append(Paragraph("Proposed experiments", st["h"]))
story.append(Paragraph("Ten experiments are proposed (guided KYC, assisted KYC, UPI-first bank link, quick-amount deposit, guided first trade, referral prompt, habit nudges, KYC status tracker, win-back, paid-social pre-qualification page). "
                       "None has been run; baselines are actual, effect sizes are assumptions, and the traffic constraint (about 190 registrations a week) makes retention and paid-social tests slow. See Growth_Experiments.xlsx.", st["p"]))
story.append(Paragraph("Limitations", st["h"]))
for t_ in ["Synthetic data: patterns reflect how the dataset was generated (for example, ticket priority has no effect on resolution time).",
           "Funnel flags and the monthly activity log disagree for many users (91-98% in stalled segments), so segment sizes are indicative.",
           "Inactivity flags are proxies, not churn; recent cohorts are excluded or eligibility-limited; ticket, early-trading and channel patterns are associations, not causal effects.",
           "No revenue or cost-to-serve data: cost per first trader is a cost metric, not ROI. K-means (silhouette 0.33) and the early-warning model (AUC about 0.57) are descriptive only."]:
    story.append(Paragraph(esc(t_), st["b"], bulletText="•"))


def footer(c, d):
    c.saveState(); c.setFont("Helvetica", 7.5); c.setFillColor(MUTED)
    c.drawString(0.75 * inch, 0.5 * inch, "Fintech Growth Analytics | SYNTHETIC DATA")
    c.drawRightString(letter[0] - 0.75 * inch, 0.5 * inch, f"Page {d.page}")
    c.restoreState()


doc = SimpleDocTemplate(str(ROOT / "reports" / "Fintech_Executive_Summary.pdf"), pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch, topMargin=0.7 * inch, bottomMargin=0.8 * inch,
                        title="Fintech Growth Analytics - Executive Summary (synthetic data)", author="Yash Sharma")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("pdf written")
