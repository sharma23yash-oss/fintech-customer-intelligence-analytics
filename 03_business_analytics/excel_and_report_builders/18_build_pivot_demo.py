"""Phase 4 / Module A - companion workbook with REAL PivotTables (SYNTHETIC data), built through LibreOffice's UNO DataPilot API.
openpyxl cannot author PivotTable caches, so this workbook is produced by LibreOffice and saved as .xlsx; Excel opens the pivots natively.
Run: python3 18_build_pivot_demo.py   (needs LibreOffice + its python 'uno' module)"""
import subprocess, time, sys, os
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CFG_CLEAN = ROOT / "data" / "cleaned"
OUT = ROOT / "03_business_analytics" / "excel" / "Fintech_PivotTables_Demo.xlsx"
TMP = Path(__import__("tempfile").gettempdir()) / "pivot_src.xlsx"
U = pd.read_csv(CFG_CLEAN / "Cleaned_Users.csv", usecols=["user_id", "registration_date", "acquisition_channel", "device_type", "city", "funnel_mature", "kyc_asof", "bank_asof", "deposit_asof", "trade_asof"])
U["reg_month_key"] = pd.to_datetime(U.registration_date).dt.year * 100 + pd.to_datetime(U.registration_date).dt.month
U = U.drop(columns="registration_date")
A = pd.read_csv(CFG_CLEAN / "Cleaned_Monthly_Activity.csv")
A["activity_month_key"] = A.activity_month.str.replace("-", "").astype(int); A["registration_month_key"] = A.registration_month.str.replace("-", "").astype(int)
A = A[["user_id", "registration_month_key", "activity_month_key", "months_since_registration", "active_in_month", "trade_count", "trading_value_inr"]]
T = pd.read_csv(CFG_CLEAN / "Cleaned_Support_Tickets.csv")[["ticket_id", "category", "priority", "status", "csat_score", "is_resolved"]]
with pd.ExcelWriter(TMP) as w:
    U[U.funnel_mature == 1].to_excel(w, "Users_Mature", index=False); U.to_excel(w, "Users_All", index=False)
    A.to_excel(w, "Activity_Data", index=False); T.to_excel(w, "Tickets_Data", index=False)
shape = {"Users_Mature": U[U.funnel_mature == 1].shape, "Users_All": U.shape, "Activity_Data": A.shape, "Tickets_Data": T.shape}

port = 2002
proc = subprocess.Popen(["soffice", "--headless", "--invisible", "--norestore", f"--accept=socket,host=localhost,port={port};urp;"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
import uno
from com.sun.star.beans import PropertyValue
from com.sun.star.table import CellAddress, CellRangeAddress
from com.sun.star.sheet.DataPilotFieldOrientation import ROW, COLUMN, DATA
from com.sun.star.sheet.GeneralFunction import SUM, COUNT, AVERAGE
ctx = None
for _ in range(60):
    try:
        local = uno.getComponentContext(); res = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
        ctx = res.resolve(f"uno:socket,host=localhost,port={port};urp;StarOffice.ComponentContext"); break
    except Exception: time.sleep(1)
assert ctx, "could not connect to LibreOffice"
desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
pv = lambda n, v: PropertyValue(Name=n, Value=v)
doc = desktop.loadComponentFromURL(TMP.as_uri(), "_blank", 0, (pv("Hidden", True),))
S = doc.Sheets


def pivot(name, src, ncols, rows, cols, data, target_sheet, title):
    rng_rows = shape[src][0]
    sh = S.getByName(src); sidx = list(S.ElementNames).index(src)
    S.insertNewByName(target_sheet, S.Count); t = S.getByName(target_sheet)
    t.getCellByPosition(0, 0).String = title
    dp = t.getDataPilotTables(); d = dp.createDataPilotDescriptor()
    d.setSourceRange(CellRangeAddress(sidx, 0, 0, ncols - 1, rng_rows))
    flds = d.getDataPilotFields()
    names = [flds.getByIndex(i).getName() if hasattr(flds.getByIndex(i), "getName") else flds.getByIndex(i).Name for i in range(flds.Count)]
    for n in rows: flds.getByName(n).Orientation = ROW
    for n in cols: flds.getByName(n).Orientation = COLUMN
    for n, fn in data:
        f = flds.getByName(n); f.Orientation = DATA; f.Function = fn
    dp.insertNewByName(name, CellAddress(S.Count - 1, 0, 2), d)
    return t


pivot("pvt_Funnel_by_Channel", "Users_Mature", 9, ["acquisition_channel"], [], [("kyc_asof", SUM), ("bank_asof", SUM), ("deposit_asof", SUM), ("trade_asof", SUM), ("user_id", COUNT)], "PT1_Funnel_by_Channel", "PT1 - Mature-cohort funnel by channel (sum of 0/1 stage flags; count of user_id = mature users)")
pivot("pvt_Reg_Month_Channel", "Users_All", 10, ["reg_month_key"], ["acquisition_channel"], [("user_id", COUNT)], "PT2_Registrations", "PT2 - Registrations by month x channel (count of user_id)")
pivot("pvt_Cohort_Retention", "Activity_Data", 7, ["registration_month_key"], ["months_since_registration"], [("active_in_month", AVERAGE)], "PT3_Cohort_Retention", "PT3 - Cohort retention (average of active_in_month; format cells as %)")
pivot("pvt_Tickets_Category_Priority", "Tickets_Data", 6, ["category"], ["priority"], [("ticket_id", COUNT)], "PT4_Tickets", "PT4 - Support tickets by category x priority (count of ticket_id)")
pivot("pvt_Monthly_Trading", "Activity_Data", 7, ["activity_month_key"], [], [("trading_value_inr", SUM), ("trade_count", SUM)], "PT5_Monthly_Trading", "PT5 - Monthly trading value (INR) and trades")
doc.storeToURL(OUT.as_uri(), (pv("FilterName", "Calc MS Excel 2007 XML"),))
doc.close(True)
try: desktop.terminate()
except Exception: pass
proc.wait(timeout=30)
print("saved", OUT, OUT.stat().st_size // 1024, "KB")
