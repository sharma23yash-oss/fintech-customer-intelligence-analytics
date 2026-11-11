"""Phase 5 - emit Power BI build artifacts (SYNTHETIC data model).
Writes, from the single source of truth (powerbi_measures.py + model_tables_meta.json):
  06_dashboard/dax/Measure_Library.dax, DimDate.dax, DAX_Measure_Library.md
  06_dashboard/power_query/*.pq (one query per CSV) + DataFolder parameter + Power_Query_Transformations.md
  06_dashboard/theme/Fintech_Theme_Light.json, Fintech_Theme_Navy.json
  06_dashboard/tmdl_scaffold/Fintech_Growth.SemanticModel/...  (UNTESTED scaffold - never opened in Power BI Desktop)
Run: python3 21_emit_powerbi_artifacts.py
"""
import json, re, sys
from collections import OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1] / "05_python"))   # build_scripts + fintech_analytics package
import powerbi_measures as PM

ROOT = HERE.parents[1]
PB = ROOT / "06_dashboard"
META = json.loads((PB / "validation" / "model_tables_meta.json").read_text())
for d in ("dax", "power_query", "theme", "tmdl_scaffold"):
    (PB / d).mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------------------------- shared model definition
SORT_BY = {  # (table, column) -> sort-by column
    ("DimDate", "MonthLabel"): "MonthSort", ("DimCampaign", "Channel"): "ChannelSort", ("DimCity", "CityKey"): "CitySort",
    ("DimDevice", "DeviceKey"): "DeviceSort", ("DimStage", "StageName"): "StageOrder", ("FactCustomer", "InactivityBucket"): "InactivitySort",
    ("FactTicket", "Priority"): "PrioritySort", ("FactTicket", "BacklogAgeBucket"): "BacklogSort"}
# (from_table, from_col, to_table, to_col, active)
REL = []
for fact in ("FactCustomer", "FactActivity", "FactTicket"):
    for dim, col in (("DimCampaign", "CampaignKey"), ("DimCity", "CityKey"), ("DimDevice", "DeviceKey"), ("DimSegment", "SegmentKey")):
        REL.append((fact, col, dim, col, True))
REL += [("FactCustomer", "RegistrationDate", "DimDate", "Date", True), ("FactActivity", "ActivityMonthDate", "DimDate", "Date", True),
        ("FactTicket", "CreatedDate", "DimDate", "Date", True)]
HIDDEN = {"FactCustomer": {"CampaignKey", "CityKey", "DeviceKey", "SegmentKey", "InactivitySort"},
          "FactActivity": {"CampaignKey", "CityKey", "DeviceKey", "SegmentKey"},
          "FactTicket": {"CampaignKey", "CityKey", "DeviceKey", "SegmentKey", "PrioritySort", "BacklogSort"}}
DIMDATE_COLS = OrderedDict([("Date", "date"), ("Year", "int"), ("Quarter", "text"), ("MonthNumber", "int"), ("MonthStart", "date"), ("MonthLabel", "text"),
                            ("MonthSort", "int"), ("WeekdayNumber", "int"), ("WeekdayName", "text"), ("IsMonthStart", "int")])
TABLE_ORDER = ["DimDate", "DimCampaign", "DimCity", "DimDevice", "DimSegment", "DimStage", "FactCustomer", "FactActivity", "FactTicket"]
M_TYPE = {"text": "type text", "int": "Int64.Type", "number": "type number", "date": "type date"}
TMDL_TYPE = {"text": "string", "int": "int64", "number": "double", "date": "dateTime"}


# --------------------------------------------------------------------------------------------- DAX pretty-printer (whitespace only)
def _scan_top(s, ch):
    """indices of `ch` at paren-depth 0 outside strings / [brackets] / 'quoted names'."""
    out, depth, i, n = [], 0, 0, len(s)
    mode = None
    while i < n:
        c = s[i]
        if mode == '"':
            if c == '"': mode = None
        elif mode == "[":
            if c == "]": mode = None
        elif mode == "'":
            if c == "'": mode = None
        else:
            if c in '"[\'': mode = c
            elif c == "(": depth += 1
            elif c == ")": depth -= 1
            elif c == ch and depth == 0: out.append(i)
        i += 1
    return out


def _match(s, i):
    depth, mode = 0, None
    for k in range(i, len(s)):
        c = s[k]
        if mode == '"':
            if c == '"': mode = None
        elif mode == "[":
            if c == "]": mode = None
        elif mode == "'":
            if c == "'": mode = None
        else:
            if c in '"[\'': mode = c
            elif c == "(": depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0: return k
    return -1


def _fmt(s, ind, width=96):
    s = s.strip()
    if ind + len(s) <= width: return s
    opens = _scan_top(s, "(") if False else None
    # first '(' outside strings/brackets
    mode, p = None, -1
    for k, c in enumerate(s):
        if mode == '"':
            if c == '"': mode = None
        elif mode == "[":
            if c == "]": mode = None
        elif mode == "'":
            if c == "'": mode = None
        else:
            if c in '"[\'': mode = c
            elif c == "(": p = k; break
    if p < 0: return s
    q = _match(s, p)
    if q < 0: return s
    head, inner, tail = s[: p + 1], s[p + 1: q], s[q:]
    commas = _scan_top(inner, ",")
    args, last = [], 0
    for c in commas: args.append(inner[last:c]); last = c + 1
    args.append(inner[last:])
    pad = " " * (ind + 4)
    body = (",\n").join(pad + _fmt(a, ind + 4, width) for a in args)
    return f"{head}\n{body}\n{' ' * ind}{tail}"


def pretty(expr):
    """Re-flow a single-line DAX expression over several lines. Only whitespace changes (asserted by the caller)."""
    e = expr
    if "VAR " in e or " RETURN " in e:
        parts = re.split(r"\s+(?=VAR\s)|\s+(?=RETURN\s)", e)
        lines = []
        for part in parts:
            if part.startswith("RETURN"):
                lines.append("RETURN"); lines.append("    " + _fmt(part[len("RETURN"):].strip(), 4))
            elif part.startswith("VAR"):
                nm, _, rest = part[3:].strip().partition("=")
                lines.append(f"VAR {nm.strip()} = " + _fmt(rest.strip(), 4))
            else:
                lines.append(_fmt(part, 0))
        return "\n".join(lines)
    return _fmt(e, 0)


def ws(s): return re.sub(r"\s+", "", s)


FOLDERS = list(OrderedDict.fromkeys(m[0] for m in PM.M))
for folder, name, dax, fmt, desc in PM.M:
    assert ws(pretty(dax)) == ws(dax), name

# --------------------------------------------------------------------------------------------- 1. DAX artifacts
(PB / "dax" / "DimDate.dax").write_text(PM.DIM_DATE_DAX.rstrip() + "\n")
lines = ["// Fintech growth analytics - SYNTHETIC data. DAX measure library (" + str(len(PM.M)) + " measures).",
         "// Paste each block into Power BI Desktop > Modeling > New measure, with the table `_Measures` selected,",
         "// or import with Tabular Editor. Set the format string and display folder shown in the header comment.",
         "// NOT executed in a DAX engine in this environment; logic verified with the pandas oracle (verify_phase5.py).", ""]
for folder in FOLDERS:
    lines += ["// " + "=" * 78, f"// Display folder: {folder}", "// " + "=" * 78, ""]
    for fo, name, dax, fmt, desc in PM.M:
        if fo != folder: continue
        lines += [f"// {name}  |  format: {fmt}  |  {desc}", f"[{name}] =" if False else f"{name} =", pretty(dax), ""]
(PB / "dax" / "Measure_Library.dax").write_text("\n".join(lines))

md = ["# DAX Measure Library", "",
      "Synthetic data (fictional Indian retail brokerage, INR, snapshot 2026-10-31). **" + str(len(PM.M)) + " measures** in the `_Measures` table, grouped by display folder.", "",
      "> **Verification status.** Power BI Desktop is not available in the build environment, so this DAX has *not been executed in a DAX engine*. "
      "Each measure's logic was re-implemented in pandas on the same star-schema CSVs and checked against validated Phase 3/4 figures and independent SQL "
      "(`06_dashboard/build_scripts/verify_phase5.py`, results in `06_dashboard/validation/`). After you build the model, compare cards with `DAX_Oracle_Expected_Values.csv`.", "",
      "## How to read the measures", "",
      "- **Mature cohort**: funnel rates use customers registered before 2026-10 (`FactCustomer[FunnelMature] = 1`). October-2026 registrants have not had time to finish onboarding.",
      "- **CAC family** divides *recorded campaign spend* by paid registrations. Spend is not dated in the source data, so these measures deliberately ignore the date, city, device and segment slicers (`REMOVEFILTERS`) and show a scope note. Organic campaigns return **blank**, not zero.",
      "- **Churn proxies**: *Inactive 90d* and *Dormant 3m* are inactivity proxies, not confirmed churn.",
      "- **Segments** are a snapshot attribute as of 2026-10-31, so a month slicer combined with a segment slicer shows customers currently in that segment.",
      "- **Budget indicators** (Cost Efficiency Index, Budget Signal) are directional: they compare cost per first trade to the peer median. The data has no revenue, so they are not ROI.", "",
      "## Prerequisites", "", "1. Calculated table `DimDate` - see [DimDate.dax](DimDate.dax); mark it as the date table on `[Date]`.",
      "2. Empty measure host table: `_Measures = ROW(\"Placeholder\", BLANK())` (calculated table); hide its column.",
      "3. Relationships as in `docs/Data_Model.md` (15 one-to-many relationships, all active). The cohort matrix needs no extra relationship: it uses `FactActivity[RegMonthDate]` (rows) and `FactActivity[MonthsSinceRegistration]` (columns) directly.", ""]
for folder in FOLDERS:
    ms = [m for m in PM.M if m[0] == folder]
    md += [f"## {folder} ({len(ms)})", "", "| Measure | Format | Purpose |", "|---|---|---|"]
    for fo, name, dax, fmt, desc in ms:
        md.append(f"| {name} | `{fmt}` | {desc.replace('|', '/')} |")
    md.append("")
    for fo, name, dax, fmt, desc in ms:
        md += [f"### {name}", "", "```dax", f"{name} =", pretty(dax), "```", ""]
(PB / "dax" / "DAX_Measure_Library.md").write_text("\n".join(md))

# --------------------------------------------------------------------------------------------- 2. Power Query
def m_query(table, cols):
    pairs = ", ".join(f'{{"{c}", {M_TYPE[t]}}}' for c, t in cols.items())
    return (f"// {table} - SYNTHETIC data. One query per CSV; load enabled. Requires the DataFolder parameter (see 00_DataFolder.pq).\n"
            "let\n"
            f'    Source   = Csv.Document(File.Contents(DataFolder & "\\{table}.csv"), [Delimiter = ",", Columns = {len(cols)}, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),\n'
            "    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),\n"
            f"    Typed    = Table.TransformColumnTypes(Promoted, {{{pairs}}}, \"en-US\")\n"
            "in\n    Typed\n")


DATA_FOLDER_M = ('"C:\\Path\\To\\fintech-customer-intelligence-analytics\\06_dashboard\\data" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]\n')
(PB / "power_query" / "00_DataFolder.pq").write_text("// Parameter query: folder that contains the 8 star-schema CSV files (no trailing backslash). Change once, refresh all.\n" + DATA_FOLDER_M)
for i, t in enumerate(["DimCampaign", "DimCity", "DimDevice", "DimSegment", "DimStage", "FactCustomer", "FactActivity", "FactTicket"], start=1):
    (PB / "power_query" / f"{i:02d}_{t}.pq").write_text(m_query(t, META[t]["columns"]))

pq = ["# Power Query transformation instructions", "",
      "Synthetic data. The 8 star-schema CSVs in `06_dashboard/data/` are already clean (produced and validated by `06_dashboard/build_scripts/19_build_powerbi_model_data.py`, 27 integrity checks). "
      "Power Query therefore only has to **load and type** them; no business logic lives in M. All business logic is in DAX so every figure stays traceable.", "",
      "## Steps", "",
      "1. **Home > Transform data > New Source > Blank Query**, open *Advanced Editor*, paste `00_DataFolder.pq`, set the path of your local `06_dashboard/data` folder, and name the query `DataFolder` (Home > Manage Parameters also works).",
      "2. For each file `01_...` to `08_...` create a blank query, paste the M, and name the query exactly as the table (`DimCampaign`, `FactCustomer`, ...).",
      "3. **Close & Apply.** `DimDate` and `_Measures` are *not* Power Query tables - they are DAX calculated tables (see `dax/`).", "",
      "## What each query does", "",
      "| Step | M function | Why |", "|---|---|---|",
      "| Source | `Csv.Document(File.Contents(DataFolder & \"\\\\Table.csv\"), [Encoding = 65001, QuoteStyle = QuoteStyle.Csv])` | UTF-8 CSV; quote-aware so text with commas is safe |",
      "| Promoted | `Table.PromoteHeaders(..., [PromoteAllScalars = true])` | first row becomes column names |",
      "| Typed | `Table.TransformColumnTypes(..., \"en-US\")` | explicit types; fixed culture so ISO dates (`yyyy-mm-dd`) and `.` decimals parse the same on any machine |", "",
      "Blank cells in integer columns (e.g. `DaysRegToKYC` for customers who never completed KYC, `CSAT` for unrated tickets) stay `null` on purpose: DAX `AVERAGE`, `MEDIAN` and `PERCENTILE` ignore blanks, which is the intended behaviour.", "",
      "## Column types per table", ""]
for t in TABLE_ORDER[1:]:
    cols = META[t]["columns"]
    pq += [f"### {t} ({META[t]['rows']:,} rows, {len(cols)} columns)", "", "| Column | Type |", "|---|---|"] + [f"| {c} | {ty} |" for c, ty in cols.items()] + [""]
pq += ["## Model-side settings after load (cannot be stored in M)", "",
       "- Set *Sort by column* as listed in `docs/Data_Model.md` (Month label by MonthSort, Channel by ChannelSort, Priority by PrioritySort, ...).",
       "- Set *Summarization = Don't summarize* on every numeric column (use measures, not implicit aggregation).",
       "- Hide key and sort helper columns in the fact tables.",
       "- Date columns: format `yyyy-mm-dd`.", ""]
(PB / "power_query" / "Power_Query_Transformations.md").write_text("\n".join(pq))

# --------------------------------------------------------------------------------------------- 3. Themes (palettes validated with the dataviz validator)
LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
DARK = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"]


def theme(name, colors, bg, fg, sub, card, border, header_bg, seq):
    s = lambda c: {"solid": {"color": c}}
    return {"name": name, "dataColors": [c.upper() for c in colors], "background": bg.upper(), "foreground": fg.upper(), "tableAccent": colors[0].upper(),
            "good": "#0CA30C", "neutral": "#FAB219", "bad": "#D03B3B", "maximum": seq[2], "center": seq[1], "minimum": seq[0],
            "textClasses": {"callout": {"fontSize": 24, "fontFace": "Segoe UI Semibold", "color": fg}, "title": {"fontSize": 12, "fontFace": "Segoe UI Semibold", "color": fg},
                            "header": {"fontSize": 11, "fontFace": "Segoe UI Semibold", "color": fg}, "label": {"fontSize": 10, "fontFace": "Segoe UI", "color": sub}},
            "visualStyles": {"*": {"*": {
                "title": [{"show": True, "fontColor": s(fg), "fontSize": 12, "fontFamily": "Segoe UI Semibold", "alignment": "left"}],
                "background": [{"show": True, "color": s(card), "transparency": 0}],
                "border": [{"show": True, "color": s(border), "radius": 6}],
                "categoryAxis": [{"labelColor": s(sub), "fontSize": 10, "showAxisTitle": False}],
                "valueAxis": [{"labelColor": s(sub), "fontSize": 10, "showAxisTitle": False, "gridlineColor": s(border)}],
                "legend": [{"labelColor": s(sub), "fontSize": 10, "position": "Top"}],
                "labels": [{"color": s(fg), "fontSize": 10}]}},
                "page": {"*": {"background": [{"color": s(bg), "transparency": 0}], "outspace": [{"color": s(bg)}]}}}}


light = theme("Fintech Light (synthetic demo)", LIGHT, "#F4F6FA", "#0B1F3A", "#52606D", "#FFFFFF", "#E3E8EF", "#0B1F3A", ["#CDE2FB", "#6DA7EC", "#0D366B"])
navy = theme("Fintech Navy (synthetic demo)", DARK, "#0B1F3A", "#F0EFEC", "#C3C2B7", "#12294A", "#24406B", "#071529", ["#184F95", "#3987E5", "#CDE2FB"])
for nm, th in (("Fintech_Theme_Light.json", light), ("Fintech_Theme_Navy.json", navy)):
    (PB / "theme" / nm).write_text(json.dumps(th, indent=2))
    json.loads((PB / "theme" / nm).read_text())

# --------------------------------------------------------------------------------------------- 4. TMDL scaffold (UNTESTED)
SM = PB / "tmdl_scaffold" / "Fintech_Growth.SemanticModel"
(SM / "definition" / "tables").mkdir(parents=True, exist_ok=True)
T = "\t"
q = lambda n: f"'{n}'" if re.search(r"[^A-Za-z0-9_]", n) else n
(SM / "definition.pbism").write_text(json.dumps({"version": "4.0", "settings": {}}, indent=2))
(SM / "definition" / "database.tmdl").write_text("database Fintech_Growth\n\tcompatibilityLevel: 1600\n")
(SM / "definition" / "model.tmdl").write_text("model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tdiscourageImplicitMeasures\n\n"
                                              + "\n".join(f"ref table {t}" for t in TABLE_ORDER + ["_Measures"]) + "\n\nref expression DataFolder\n")
(SM / "definition" / "expressions.tmdl").write_text("expression DataFolder = " + DATA_FOLDER_M.replace("\n", "") + "\n")
rel = []
for ft, fc, tt, tc, act in REL:
    rel.append(f"relationship rel_{ft}_{fc}_{tt}\n{T}fromColumn: {ft}.{fc}\n{T}toColumn: {tt}.{tc}\n" + ("" if act else f"{T}isActive: false\n"))
(SM / "definition" / "relationships.tmdl").write_text("\n".join(rel))


def tmdl_cols(table, cols):
    out = []
    for c, ty in cols.items():
        out.append(f"{T}column {q(c)}\n{T}{T}dataType: {TMDL_TYPE[ty]}")
        if ty == "date": out.append(f"{T}{T}formatString: yyyy-mm-dd")
        if table == "DimDate" and c == "Date": out.append(f"{T}{T}isKey")
        if c in HIDDEN.get(table, ()) or (table.startswith("Dim") and c.endswith("Sort") and c != "StageOrder") or c in ("MonthSort",): out.append(f"{T}{T}isHidden")
        out.append(f"{T}{T}summarizeBy: none")
        out.append(f"{T}{T}sourceColumn: {c}")
        if (table, c) in SORT_BY: out.append(f"{T}{T}sortByColumn: {SORT_BY[(table, c)]}")
        out.append("")
    return out


for t in TABLE_ORDER:
    cols = DIMDATE_COLS if t == "DimDate" else META[t]["columns"]
    lines = [f"table {t}"]
    if t == "DimDate": lines.append(f"{T}dataCategory: Time")
    lines.append("")
    lines += tmdl_cols(t, cols)
    if t == "DimDate":
        lines += [f"{T}partition DimDate = calculated", f"{T}{T}mode: import", f"{T}{T}source = " + " ".join(PM.DIM_DATE_DAX.split("=", 1)[1].split())]
    else:
        body = m_query(t, cols).split("\n", 1)[1].rstrip("\n").split("\n")
        lines += [f"{T}partition {t} = m", f"{T}{T}mode: import", f"{T}{T}source ="] + [f"{T}{T}{T}{T}{ln}" for ln in body]
    (SM / "definition" / "tables" / f"{t}.tmdl").write_text("\n".join(lines) + "\n")
ml = ["table _Measures", ""]
for fo, name, dax, fmt, desc in PM.M:
    ml += [f"{T}measure {q(name)} = {dax}", f"{T}{T}formatString: {fmt}" if fmt != PM.TXT else f"{T}{T}formatString: General", f"{T}{T}displayFolder: {fo}", f"{T}{T}description: {desc}", ""]
ml += [f"{T}column Placeholder", f"{T}{T}dataType: string", f"{T}{T}isHidden", f"{T}{T}sourceColumn: [Placeholder]", "",
       f"{T}partition _Measures = calculated", f"{T}{T}mode: import", f'{T}{T}source = ROW("Placeholder", BLANK())']
(SM / "definition" / "tables" / "_Measures.tmdl").write_text("\n".join(ml) + "\n")
(PB / "tmdl_scaffold" / "README.md").write_text(
    "# TMDL semantic-model scaffold - UNTESTED\n\n"
    "Generated by `06_dashboard/build_scripts/21_emit_powerbi_artifacts.py` from the same sources as the DAX library and Power Query scripts: 9 tables, "
    f"{len(REL)} relationships (all active), {len(PM.M)} measures, sort-by and hidden-column settings.\n\n"
    "**Status: this folder has never been opened in Power BI Desktop or Tabular Editor.** TMDL syntax was written from the public format description and "
    "may need small fixes. It is a head start for the manual build, not a deliverable PBIX. If it does not open, ignore it and follow "
    "`docs/Implementation_Guide.md`.\n\n"
    "To try it: Power BI Desktop > File > Open > *Semantic model folder* (preview feature 'Power BI Project (.pbip)' + 'TMDL' must be enabled), "
    "set the `DataFolder` expression to your local data folder, then refresh.\n")

# --------------------------------------------------------------------------------------------- summary
print(f"measures: {len(PM.M)} in {len(FOLDERS)} folders | relationships: {len(REL)} | tables: {len(TABLE_ORDER)}")
for p in sorted((PB).rglob("*")):
    if p.is_file() and p.parent.name in ("dax", "power_query", "theme", "tables", "definition", "tmdl_scaffold", "Fintech_Growth.SemanticModel"):
        print(f"  {p.relative_to(PB)}  {p.stat().st_size:,} B")
