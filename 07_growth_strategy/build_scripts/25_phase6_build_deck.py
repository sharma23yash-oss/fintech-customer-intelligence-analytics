"""Phase 6: generate the 12-slide Management Presentation (Slides artifact files).

Writes project/deck.json and project/slides/*.html under 07_growth_strategy/deck_src/ (not committed: the deck itself was authored in-app).
All figures are taken from the Phase 3 tables / Phase 6 evidence tables (synthetic data).
No experiments were run and no ROI is computed.
"""
import csv, datetime, json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "deck_src")
ROOT = os.path.abspath(ROOT)
SL = os.path.join(ROOT, "project", "slides")
os.makedirs(SL, exist_ok=True)

DARK, LIGHT, PANEL = "#14213D", "#F6F5F0", "#FDFCF9"
TEAL, AMBER = "#0B7A75", "#F2B544"
TEAL_D = "#5FD0C5"            # teal on dark
BODY, MUTED = "#3F4857", "#5B6472"
BODY_D = "#C9D1E0"
LINE = "#DAD8CE"
TRACK = "#E7E4DA"
HEAD = "'Space Grotesk', Arial, sans-serif"
TXT = "'Inter', Arial, sans-serif"
N = 12


def sec(sid, bg, fg, inner, page, notes, dark=False, footer=True, pad="128px 128px 160px", extra=""):
    foot = ""
    if footer:
        c = BODY_D if dark else MUTED
        foot = (
            f'<p style="position:absolute;left:128px;bottom:64px;width:1200px;font-size:24px;color:{c}">'
            f'Fintech Growth Strategy · Synthetic data · No experiment run, no ROI claimed</p>'
            f'<p style="position:absolute;right:128px;bottom:64px;width:200px;text-align:right;font-size:24px;color:{c}">{page} / {N}</p>'
        )
    return (
        f'<section id="{sid}" data-transition="fade" style="background:{bg};color:{fg};font-family:{TXT};'
        f'display:flex;flex-direction:column;gap:40px;padding:{pad};{extra}">\n'
        f'{inner}\n{foot}\n<aside>{notes}</aside>\n</section>\n'
    )


def title(t, sub=None, dark=False):
    c = LIGHT if dark else DARK
    s = ""
    if sub:
        s = f'<p style="font-size:30px;line-height:1.4;color:{BODY_D if dark else BODY}">{sub}</p>'
    return (
        f'<div style="display:flex;flex-direction:column;gap:12px">'
        f'<h2 style="font-family:{HEAD};font-size:64px;font-weight:600;line-height:1.1;color:{c}">{t}</h2>{s}</div>'
    )


def table(headers, rows, widths, size=26, align=None, bold_first=True):
    align = align or ["left"] * len(headers)
    out = f'<table style="font-size:{size}px;color:{BODY};font-family:{TXT}">'
    out += f'<tr style="background:{DARK}">'
    for h, w, a in zip(headers, widths, align):
        out += f'<th style="width:{w}%;text-align:{a};color:{LIGHT};font-weight:600">{h}</th>'
    out += "</tr>"
    for i, r in enumerate(rows):
        bg = PANEL if i % 2 == 0 else "#EFEDE4"
        out += f'<tr style="background:{bg}">'
        for j, (c, a) in enumerate(zip(r, align)):
            if j == 0 and bold_first:
                out += f'<td style="text-align:{a};color:{DARK}"><b>{c}</b></td>'
            else:
                out += f'<td style="text-align:{a}">{c}</td>'
        out += "</tr>"
    return out + "</table>"


def card(inner, bg=PANEL, border=LINE, gap=10, grow=False):
    f = "flex:1;" if grow else ""
    return (
        f'<div style="{f}display:flex;flex-direction:column;gap:{gap}px;background:{bg};padding:28px;'
        f'border:1px solid {border};border-radius:16px">{inner}</div>'
    )


slides = {}

# 1 cover
slides["cover"] = sec(
    "cover", DARK, LIGHT,
    f'<p style="font-size:26px;letter-spacing:2px;text-transform:uppercase;color:{AMBER};font-weight:600">'
    f'Fictional Indian retail brokerage · Synthetic data</p>'
    f'<h1 style="font-family:{HEAD};font-size:96px;font-weight:600;line-height:1.1;color:{LIGHT}">Fintech Growth Strategy and Operational Optimisation</h1>'
    f'<p style="font-size:32px;line-height:1.4;color:{BODY_D}">Management presentation · Phase 6 · Data snapshot 31 October 2026</p>',
    1,
    "Opening. This deck turns the Phase 1 to 5 analytics into decisions for leadership. All data is synthetic and the company is fictional. "
    "No experiment has been run and no revenue or ROI is claimed.",
    dark=True, footer=False, pad="128px", extra="justify-content:center;gap:40px;",
)

# 2 headline
def stat(big, label, color=TEAL):
    return card(
        f'<p style="font-family:{HEAD};font-size:72px;font-weight:600;line-height:1.1;color:{color}">{big}</p>'
        f'<p style="font-size:28px;line-height:1.4;color:{BODY}">{label}</p>', grow=True, gap=14)

slides["headline"] = sec(
    "headline", LIGHT, DARK,
    title("What the data says", "Three findings drive the recommendations.")
    + '<div style="display:flex;gap:24px">'
    + stat("42.6%", "of funnel losses happen at KYC: 2,687 of 6,308 registrants lost between registration and 30-day activity.")
    + stat("Rs 438 vs Rs 923", "cost per first trade: referral, against the blended paid average. Recorded marketing spend only.")
    + stat("563", "support tickets unresolved for over 90 days, while median resolution stays at 9.4 hours whatever the priority.")
    + "</div>"
    + f'<p style="font-size:32px;line-height:1.4;color:{DARK};font-weight:600">Recommendation: fix onboarding friction and manage campaigns on cost per first trade before adding spend.</p>',
    2,
    "Mature cohort of 9,116 users registered before October 2026. Losses by step: KYC 2,687, bank 784, deposit 1,305, first trade 878, active 654, total 6,308. "
    "Cost per first trade is recorded marketing spend divided by estimated first traders. It excludes every other cost.",
)

# 3 funnel
stages = [("Registered", 9116, None), ("KYC complete", 6429, "70.5%"), ("Bank linked", 5645, "87.8%"),
          ("Deposited", 4340, "76.9%"), ("First trade", 3462, "79.8%"), ("Active, 30 days", 2808, "81.1%")]
rows = ""
for name, n, conv in stages:
    w = round(n / 9116 * 480)
    rows += (
        '<div style="display:flex;gap:20px;align-items:center">'
        f'<p style="width:230px;font-size:26px;color:{DARK};font-weight:600">{name}</p>'
        f'<div style="width:480px;background:{TRACK};border-radius:8px;display:flex"><div style="width:{w}px;height:40px;background:{TEAL};border-radius:8px"></div></div>'
        f'<p style="width:110px;font-size:26px;text-align:right;color:{DARK}">{n:,}</p>'
        f'<p style="width:100px;font-size:26px;text-align:right;color:{MUTED}">{conv or ""}</p></div>'
    )
loss = [("KYC", "2,687", "42.6%"), ("Deposit", "1,305", "20.7%"), ("First trade", "878", "13.9%"),
        ("Bank link", "784", "12.4%"), ("Active", "654", "10.4%")]
lrows = "".join(
    f'<div style="display:flex;gap:12px"><p style="width:150px;font-size:26px;color:{DARK};font-weight:600">{a}</p>'
    f'<p style="width:100px;font-size:26px;text-align:right;color:{DARK}">{b}</p>'
    f'<p style="width:90px;font-size:26px;text-align:right;color:{MUTED}">{c}</p></div>' for a, b, c in loss)
slides["funnel"] = sec(
    "funnel", LIGHT, DARK,
    title("Where the funnel loses users", "Mature cohort: 9,116 registrants. Step conversion shown at the right of each bar.")
    + '<div style="display:flex;gap:48px"><div style="display:flex;flex-direction:column;gap:22px">' + rows + "</div>"
    + card(f'<h3 style="font-size:32px;color:{DARK}">Users lost at each step</h3>' + lrows
           + f'<p style="font-size:24px;line-height:1.4;color:{MUTED}">Share of the 6,308 users lost in total.</p>', gap=16, grow=True)
    + "</div>",
    3,
    "Validated funnel for registrants before October 2026. The October cohort is excluded because it has not had time to progress. "
    "Inactivity is a proxy, not churn. KYC status has a source conflict in 91 to 98 percent of stalled users, so KYC counts need reconciling before any test enrolls users.",
)

# 4 channels
ch = [("Referral", "10.4%", "232", "52.9%", "438", "61.2%"), ("Organic", "18.8%", "n/a", "47.2%", "n/a", "60.4%"),
      ("Paid Search", "26.4%", "390", "36.6%", "1,065", "54.6%"), ("CRM", "5.6%", "160", "34.0%", "472", "56.0%"),
      ("Affiliate", "7.6%", "410", "33.7%", "1,216", "54.4%"), ("Partnerships", "5.8%", "328", "31.1%", "1,052", "50.8%"),
      ("Paid Social", "25.4%", "326", "30.3%", "1,075", "54.1%")]
slides["channels"] = sec(
    "channels", LIGHT, DARK,
    title("Channel quality", "Referral converts best and costs least per first trade. CRM is cheap but small.")
    + table(["Channel", "Share of registrations", "CAC (Rs)", "First-trade rate", "Cost per first trade (Rs)", "Month-3 active"],
            [list(r) for r in ch], [22, 18, 12, 16, 18, 14], size=26, align=["left"] + ["right"] * 5)
    + f'<p style="font-size:24px;line-height:1.4;color:{MUTED}">Cost per first trade = recorded spend ÷ registrations ÷ first-trade rate. Marketing cost only; organic has no recorded cost.</p>',
    4,
    "Channel table from the Phase 3 scorecard. Paid acquisition channels cost Rs 1,052 to 1,216 per first trade against Rs 438 for referral. "
    "Referrer IDs and reward costs are not in the data, so referral attribution is approximate and reward cost is unknown.",
)

# 5 budget scenarios
sc = [("S1", "10% of CMP04 + CMP06 budget", "76,000", "+106 (+3.6%)", "+50", "+22", "+172%"),
      ("S2", "25% of CMP04 + CMP06 budget", "190,000", "+265 (+9.1%)", "+125", "+55", "+172%"),
      ("S3", "15% of CMP04 + CMP06 + CMP09", "142,500", "+194 (+6.7%)", "+90", "+38", "+163%")]
slides["budget"] = sec(
    "budget", LIGHT, DARK,
    title("Budget shift scenarios", "Arithmetic at observed efficiency, not a forecast. Moved budget goes equally to CMP05 and CMP10.")
    + table(["Scenario", "Budget moved (Rs)", "Extra first traders, cost unchanged", "If cost +50%", "If cost +100%", "Break-even cost rise"],
            [[f"{a}: {b}", c, d, e, f, g] for a, b, c, d, e, f, g in sc], [32, 14, 20, 12, 12, 10], size=24,
            align=["left"] + ["right"] * 5)
    + '<div style="display:flex;gap:24px">'
    + card(f'<h3 style="font-size:30px;color:{DARK}">Decision rule</h3><p style="font-size:26px;line-height:1.4;color:{BODY}">Go to stage 2 only if the destination’s marginal cost per first trade is at most Rs 682. Stop if it exceeds Rs 908.</p>', grow=True)
    + card(f'<h3 style="font-size:30px;color:{DARK}">Limit</h3><p style="font-size:26px;line-height:1.4;color:{BODY}">S2 needs CMP05 spend to grow 40% and CMP10 106%. Revenue is not in the data, so no ROI is stated.</p>', grow=True)
    + "</div>",
    5,
    "Baseline is about 2,913 first traders from Rs 2,690,000 paid spend, so blended cost per first trade is Rs 923. "
    "Blended cost after the shift would be Rs 891 in S1 and Rs 846 in S2 if destination campaigns kept their observed efficiency, which is the optimistic case. "
    "Break-even: the destination cost per first trader could rise by this percentage before the shift stops adding first traders.",
)

# 6 CX
cx = [("KYC", "70.5%", "complete; 2,687 stalled", "Checklist, status tracker, assisted KYC"),
      ("Bank link", "87.8%", "link a bank; 784 lost", "UPI-first with one-tap fallback"),
      ("First deposit", "76.9%", "deposit; 1,305 lost", "Quick-amount chips and reminders"),
      ("First trade", "79.8%", "trade; 878 lost", "Guided walkthrough, practice order"),
      ("Support", "54.8%", "of tickets are onboarding", "Priority routing, clear 563-ticket backlog")]
cards = "".join(card(
    f'<h3 style="font-size:32px;color:{DARK}">{a}</h3>'
    f'<p style="font-family:{HEAD};font-size:56px;font-weight:600;line-height:1.1;color:{TEAL}">{b}</p>'
    f'<p style="font-size:26px;line-height:1.4;color:{MUTED}">{c}</p>'
    f'<p style="font-size:26px;line-height:1.4;color:{DARK};font-weight:600">{d}</p>', grow=True, gap=14) for a, b, c, d in cx)
slides["cx"] = sec(
    "cx", LIGHT, DARK,
    title("Customer experience: friction and fixes", "Each stage has a measured loss and a testable fix.")
    + f'<div style="display:flex;gap:24px">{cards}</div>',
    6,
    "Friction by stage from the mature funnel. Fixes map to experiments EXP-01 to EXP-05 and EXP-08. "
    "Step-level event logs do not exist, so why users drop at each step is inferred, not observed. Logging them is part of the Days 1 to 30 data work.",
)

# 7 retention
rt = [("New customers", "601", "Early first-trade milestone in onboarding", "EXP-07"),
      ("Deposited, never traded", "881", "Guided first trade with practice order", "EXP-05"),
      ("First-time traders", "317", "Week-2 and month-1 habit nudges", "EXP-07"),
      ("Repeat traders", "1,684", "Track migration to high engagement", "Monitor"),
      ("High-engagement traders", "896", "Priority support; early-warning on activity drop", "Monitor"),
      ("Inactive traders", "352", "Value-led win-back sequence with a holdout", "EXP-09")]
slides["retention"] = sec(
    "retention", LIGHT, DARK,
    title("Retention by customer group", "Targeted action for each group, sized from the customer journey rule.")
    + table(["Group", "Users", "Action", "Test"], [list(r) for r in rt], [28, 10, 48, 14], size=26, align=["left", "right", "left", "left"])
    + f'<p style="font-size:24px;line-height:1.4;color:{MUTED}">Groups from the journey rule. The wider dormant pool (no activity Aug–Oct 2026) is 1,632 users and feeds EXP-09.</p>',
    7,
    "Segments follow the Phase 4 journey rule. Early engagement is associated with month-3 retention (60.7% vs 50.0%), which is an association, not proof of cause. "
    "The tests will show whether nudges change behaviour.",
)

# 8 support
def sstat(big, label):
    return card(f'<p style="font-family:{HEAD};font-size:80px;font-weight:600;line-height:1.1;color:{TEAL}">{big}</p>'
                f'<p style="font-size:26px;line-height:1.4;color:{BODY}">{label}</p>', grow=True, gap=12)
slides["support"] = sec(
    "support", LIGHT, DARK,
    title("Customer support operations", "Priority does not change how fast tickets are resolved, and the oldest tickets are not being closed.")
    + '<div style="display:flex;gap:24px">'
    + sstat("7,614", "tickets in total; 892 open and 479 escalated.")
    + sstat("563", "unresolved for over 90 days: 355 at 91–180 days, 208 beyond 180.")
    + sstat("9.4h", "median resolution, flat across priority levels (p = 0.59).")
    + sstat("54.8%", "of tickets sit in onboarding categories.")
    + "</div>"
    + card(f'<p style="font-size:28px;line-height:1.4;color:{BODY}">Tickets per 1,000 customer-months rose from 36 (Nov 2025) to 134 (Sep 2026); October reads 218, a spike to validate before acting. SLA compliance is 94.3% and CSAT 3.83, so the SLA measure alone hides the backlog.</p>', gap=12),
    8,
    "Support metrics from the 7,614 synthetic tickets. The Kruskal-Wallis test finds no difference in resolution time across priority levels. "
    "Actions: route by priority, clear the aged backlog to zero by Day 60, and tag every ticket with the journey stage so Product sees the drivers.",
)

# 9 plan
def col(head, focus, items):
    ps = "".join(f'<p style="font-size:26px;line-height:1.4;color:{BODY}">{i}</p>' for i in items)
    return card(f'<h3 style="font-family:{HEAD};font-size:40px;color:{TEAL}">{head}</h3>'
                f'<p style="font-size:26px;line-height:1.4;color:{DARK};font-weight:600">{focus}</p>' + ps, grow=True, gap=14)
slides["plan"] = sec(
    "plan", LIGHT, DARK,
    title("30-60-90 day roadmap", "Foundations first, then tests, then scaling what the evidence supports.")
    + '<div style="display:flex;gap:24px">'
    + col("Days 1–30", "Measure and unblock", ["Growth operating cadence", "Data foundation fixes", "Cost per first trade KPI", "Support SLA and backlog", "KYC fixes: start tests"])
    + col("Days 31–60", "Test and stage", ["Staged budget shift", "Referral prompt", "Quick-amount deposit chips", "Guided first trade", "Early-milestone onboarding", "Win-back with holdout"])
    + col("Days 61–90", "Improve and extend", ["CMP04 and CMP06 plans", "Costed organic channel", "UPI-first bank linking", "Protect top traders"])
    + "</div>",
    9,
    "Fifteen recommendations: seven P1, five P2, three P3. Each has an owner, resources, KPI, measurement frequency and risks in the 30-60-90 plan document. "
    "Day-90 gate: only EXP-02 fully reads out by Day 90, and EXP-09 reads at about Day 93, so the gate is judged on leading indicators plus those two reads.",
)

# 10 experiments
ex = [("EXP-01", "Guided KYC checklist + reminders", "+5 pp", "1,236", "16", "3"),
      ("EXP-02", "Assisted KYC for stalled applicants", "+6 pp", "206", "5", "1"),
      ("EXP-03", "UPI-first bank link", "+4 pp", "897", "10", "2"),
      ("EXP-04", "Quick-amount deposit chips", "+5 pp", "1,027", "10", "1"),
      ("EXP-05", "Guided first trade + practice order", "+5 pp", "915", "14", "2"),
      ("EXP-06", "Referral prompt after first trade", "+50% rel.", "2,657", "15", "2"),
      ("EXP-07", "Habit nudges for first-time traders", "+6 pp", "1,054", "40", "3"),
      ("EXP-08", "KYC status tracker", "−20% rel.", "2,046", "27", "3"),
      ("EXP-09", "Dormant-user win-back", "+6 pp", "1,023", "9", "1"),
      ("EXP-10", "Pre-qualification page, paid social", "+6 pp", "969", "48", "3")]
slides["experiments"] = sec(
    "experiments", LIGHT, DARK,
    title("Experiment roadmap", "Ten proposed tests, none run. Lifts are planning assumptions used only to size each test.")
    + table(["ID", "Test", "Assumed lift", "n per arm", "Weeks", "Wave"], [list(r) for r in ex], [11, 42, 15, 12, 10, 10], size=24,
            align=["left", "left", "right", "right", "right", "right"]),
    10,
    "Sample sizes: two-sided test, alpha 0.05, 80 percent power. About 190 registrations a week limits parallel tests, so EXP-01 and EXP-08 run as a 2x2 factorial and EXP-10 pools CMP03 and CMP04. "
    "EXP-07 and EXP-10 need 40 to 48 weeks at current traffic. If the true effect is half the assumed lift, sample sizes rise about four times. Full detail is in the Growth Experiment Tracker.",
)

# 11 operating model
def fn(name, a, b, lab="Shares"):
    return card(f'<h3 style="font-family:{HEAD};font-size:32px;color:{TEAL}">{name}</h3>'
                f'<p style="font-size:26px;line-height:1.4;color:{BODY}"><b>Owns:</b> {a}</p>'
                f'<p style="font-size:26px;line-height:1.4;color:{BODY}"><b>{lab}:</b> {b}</p>', grow=True, gap=12)
slides["ops"] = sec(
    "ops", LIGHT, DARK,
    title("How teams work together", "A weekly growth review and an experiment review board keep data and feedback moving.")
    + '<div style="display:flex;gap:24px">'
    + fn("Marketing", "channel budgets, CRM sends", "spend and click logs")
    + fn("Product", "KYC, bank, deposit, trade flows", "friction data, ticket themes", "Receives")
    + fn("Customer Support", "ticket SLA and backlog", "weekly themes by journey stage")
    + "</div>"
    + '<div style="display:flex;gap:24px">'
    + fn("Compliance", "rules, reminder and reward terms", "every test before launch", "Reviews")
    + fn("Data Analytics", "metrics, test design, read-outs", "weekly funnel and cost review")
    + fn("Operations", "KYC vendor, support capacity", "vendor cost, capacity data")
    + "</div>",
    11,
    "Operating cadence from recommendation D01. Every experiment has a pre-registered plan, a Compliance review before launch, a read-out by Data Analytics and a logged decision. "
    "Compliance reviews KYC rules, reminders, reward terms and practice-order disclosures.",
)

# 12 assumptions
miss = ["Revenue and fees per user", "Customer lifetime value", "Support cost per ticket", "Dated spend by campaign",
        "Referral reward cost and referrer IDs", "Organic channel cost", "KYC vendor cost and rejection reasons",
        "Click counts by campaign", "Step-level event logs", "Incentive costs"]
miss.append("Cost of any win-back incentive")
li = lambda items, c: "<ul style=\"font-size:26px;line-height:1.5;color:%s\">" % c + "".join(f"<li>{i}</li>" for i in items) + "</ul>"
slides["limits"] = sec(
    "limits", DARK, LIGHT,
    title("Assumptions and missing information", "No ROI or incremental revenue is stated because the inputs do not exist.", dark=True)
    + '<div style="display:flex;gap:64px">'
    + '<div style="flex:1;display:flex;flex-direction:column;gap:16px">'
    + f'<h3 style="font-size:32px;color:{AMBER}">What this analysis is</h3>'
    + li(["All data is synthetic and the company is fictional.", "Inactivity and dormancy are proxies, not churn.",
          "Assumed lifts only size the tests; they are not forecasts.", "No experiment has been conducted.",
          "Budget scenarios are arithmetic at observed efficiency."], BODY_D)
    + "</div>"
    + '<div style="flex:1;display:flex;flex-direction:column;gap:16px">'
    + f'<h3 style="font-size:32px;color:{AMBER}">Needed before any ROI is stated</h3>' + li(miss, BODY_D) + "</div></div>",
    12,
    "The eleven missing items are listed in the Phase 6 missing-information table. Until revenue, fee and cost data exist, the right measures are cost per first trade, "
    "conversion at each step and retention, all of which are computed from the synthetic data.",
    dark=True,
)

order = ["cover", "headline", "funnel", "channels", "budget", "cx", "retention", "support", "plan", "experiments", "ops", "limits"]
assert set(order) == set(slides) and len(order) == N
for sid in order:
    with open(os.path.join(SL, sid + ".html"), "w", encoding="utf-8") as f:
        f.write(slides[sid])

now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
deck = {
    "v": 4,
    "createdOnFiles": {"v": 1, "at": now},
    "lists": "css",
    "title": "Management Presentation – Fintech Growth Strategy & Operational Optimisation",
    "order": order,
    "cover": "cover",
    "sections": {
        "s1": {"description": "Title and purpose of the deck.", "start": "cover"},
        "s2": {"description": "The evidence: funnel, channels and budget scenarios.", "start": "headline"},
        "s3": {"description": "Customer experience, retention and support.", "start": "cx"},
        "s4": {"description": "Delivery: roadmap, experiments and operating model.", "start": "plan"},
        "s5": {"description": "Assumptions and missing information.", "start": "limits"},
    },
    "faces": {
        "space-grotesk": {"family": "Space Grotesk", "href": "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300..700&display=swap"},
        "inter": {"family": "Inter", "href": "https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap"},
    },
    "designSystems": [],
}
with open(os.path.join(ROOT, "project", "deck.json"), "w", encoding="utf-8") as f:
    json.dump(deck, f, ensure_ascii=False, indent=1)
print("wrote", len(order), "slides to", ROOT)
