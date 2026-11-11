# GitHub profile advice

## Repository settings

| Setting | Recommendation |
|---|---|
| **Name** | `fintech-customer-intelligence-analytics` (keep it; it states domain + method, is searchable, and is not tied to any company) |
| **Description** (≤ 350 characters) | `End-to-end analytics case study on a synthetic Indian brokerage dataset: SQL, Python, Excel, Power BI build kit, growth experiments and a Streamlit friction-detector prototype. 100% synthetic data.` |
| **Website field** | `https://yashify.tech` |
| **Topics** | `fintech` `data-analytics` `customer-analytics` `sql` `python` `pandas` `excel` `power-bi` `cohort-analysis` `funnel-analysis` `retention-analysis` `ab-testing` `streamlit` `portfolio-project` `synthetic-data` `brokerage` |
| **Visibility** | Public |
| **Licence** | MIT (already in the repository) |
| **Features** | Turn off Wikis and Projects if unused; leave Issues on |
| **Social preview** | Upload the banner described below (Settings → Social preview) |

## README opening (already in the README)

A centred title, one-line question, badges, then a blockquote that states, before anything else, that the data is synthetic, there is no ROI and the Power BI work is a kit. Recruiters read the first screen: honesty there builds more trust than a flashy number.

## Profile headline and bio

| Where | Text |
|---|---|
| GitHub bio (≤ 160 characters) | `MBA (Finance & Marketing), MANIT Bhopal · Fintech growth & customer analytics · SQL, Python, Excel · yashify.tech` |
| LinkedIn headline | `MBA (Finance & Marketing) | Fintech & growth analytics | SQL · Python · Excel` |
| Profile README opening line | `I analyse customer journeys in fintech: where users drop, which spend produces real customers, and what to fix first.` |

## Pinned repositories (six slots)

1. **fintech-customer-intelligence-analytics**: the analyst flagship.
2. The two published Indian-market repos you already have (for example `Bharat-equity-skills` and `dalal-street-skills`), since they show finance domain knowledge and shipping habit.
3. `advanced-portfolio-optimizer` (quantitative finance).
4. One more project that shows a different skill (for example `spy-upi`).

Order by what the target role wants: for analyst roles put this repository first. Give every pinned repository a clear description and topics; unpinned repos with no README or description dilute the page.

## Commit organisation

The repository is **initialised but not committed**; commit in logical steps so the history reads like the work. Suggested sequence (conventional-commit style):

| # | Commit | Contents |
|---|---|---|
| 1 | `chore: add licence, gitignore and requirements` | `LICENSE`, `.gitignore`, `requirements.txt` |
| 2 | `data: add synthetic raw and cleaned datasets with dictionary` | `data/` |
| 3 | `docs: add data audit and cleaning pipeline` | `01_data_audit/`, `02_data_cleaning/` |
| 4 | `feat: add business analytics modules and Excel workbooks` | `03_business_analytics/` |
| 5 | `feat: add SQL query library` | `04_sql/` |
| 6 | `feat: add Python package, pipeline and notebooks` | `05_python/`, `assets/charts/` |
| 7 | `feat: add Power BI build kit and mockups` | `06_dashboard/` |
| 8 | `docs: add growth strategy and experiment designs` | `07_growth_strategy/` |
| 9 | `feat: add AI friction detector prototype` | `08_ai_friction_detector/` |
| 10 | `docs: add README, project documentation and recruiter pack` | `README.md`, `documentation/`, `reports/`, `assets/architecture/` |

Commit messages: imperative, under 72 characters, one purpose each. After publishing, add a release tag (for example `v1.0`) so the first version is easy to cite.

## Habits that raise credibility

* Keep the README's first screen honest and scannable; put limitations in the README, not just a sub-file.
* Do not add stars-chasing badges or inflated claims.
* Add real Power BI screenshots only when they exist.
* Respond to issues and questions; a maintained repo beats a perfect abandoned one.

---

# Banner design specification

No image was generated; this is a brief for you or a designer (Canva or Figma).

| Item | Specification |
|---|---|
| Use | GitHub social preview and README header |
| Size | 1280 × 640 px (2:1), PNG, under 1 MB; keep important content inside the central 1,000 × 500 px |
| Background | Solid navy `#0B1F3A`, optional very subtle diagonal line pattern at 5 % opacity |
| Accent | Muted green `#2E8B57` used only for one thin rule under the title and for the funnel highlight |
| Text colour | White `#FFFFFF`; secondary text `#B8C4D6` |
| Title | "Fintech Customer Intelligence & Growth Analytics", bold sans-serif (Inter or similar), about 56 px, left-aligned |
| Subtitle | "Funnel · Retention · Campaigns · Support · Experiments" at about 26 px |
| Graphic | Right side: a simplified five-bar descending funnel (Registered → KYC → Bank → Deposit → First trade) in white at 15–25 % opacity, with the KYC step highlighted in green. No real data labels. |
| Badge strip | Bottom left: small pills "SQL", "Python", "Excel", "Power BI kit", "Streamlit" |
| Required label | Bottom right, small but legible: "100% SYNTHETIC DATA" |
| Do not include | Any broker logo or name, stock-chart cliché imagery, photographs of people, real-looking account screens, invented KPI claims |
| Accessibility | Contrast ratio of at least 7:1 between text and background; alt text: "Banner: Fintech Customer Intelligence and Growth Analytics, synthetic data" |
