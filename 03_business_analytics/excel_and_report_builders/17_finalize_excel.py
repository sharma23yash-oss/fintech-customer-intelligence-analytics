"""Phase 4 / Module A, stage 3: add live XLOOKUP cells to XLOOKUP_Demo after LibreOffice recalculation.
LibreOffice 24.2 cannot evaluate XLOOKUP, so the cells are injected into the sheet XML with cached values copied from the
equivalent INDEX/MATCH column (D). Excel 2021/365 recalculates them on open (fullCalcOnLoad is switched on).
Run: python3 17_finalize_excel.py   (idempotent)"""
import json, re, shutil, zipfile
from pathlib import Path
from xml.sax.saxutils import escape
import openpyxl

ROOT = Path(__file__).resolve().parents[2]
XL = ROOT / "03_business_analytics" / "excel" / "Fintech_Advanced_Excel_Analytics.xlsx"
meta = json.loads((ROOT / "03_business_analytics" / "excel" / "_build_meta.json").read_text())
rows, forms = meta["xdemo"]["rows"], meta["xdemo"]["formulas"]

wb = openpyxl.load_workbook(XL, data_only=True)
cached = {r: wb["XLOOKUP_Demo"][f"D{r}"].value for r in rows}
names = wb.sheetnames; idx = names.index("XLOOKUP_Demo") + 1
part = f"xl/worksheets/sheet{idx}.xml"

tmp = XL.with_suffix(".tmp")
with zipfile.ZipFile(XL) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == part:
            s = data.decode("utf8")
            for r, f in zip(rows, forms):
                m = re.search(rf'<c r="E{r}"([^>]*?)(?: t="[a-z]+")?>(.*?)</c>', s)
                assert m, f"E{r} not found"
                attrs = re.sub(r'\s*t="[a-z]+"', "", m.group(1))
                v = cached[r]
                ftxt = escape(f.lstrip("="))
                ftxt = ftxt.replace("XLOOKUP(", "_xlfn.XLOOKUP(")
                if isinstance(v, (int, float)):
                    cell = f'<c r="E{r}"{attrs}><f>{ftxt}</f><v>{v!r}</v></c>'
                else:
                    cell = f'<c r="E{r}"{attrs} t="str"><f>{ftxt}</f><v>{escape(str(v))}</v></c>'
                s = s.replace(m.group(0), cell)
            data = s.encode("utf8")
        elif item.filename == "xl/workbook.xml":
            s = data.decode("utf8")
            if "fullCalcOnLoad" not in s:
                s = re.sub(r"<calcPr ", '<calcPr fullCalcOnLoad="1" ', s, count=1)
            data = s.encode("utf8")
        zout.writestr(item, data)
shutil.move(tmp, XL)
chk = zipfile.ZipFile(XL).read(part).decode()
print("XLOOKUP cells injected:", chk.count("_xlfn.XLOOKUP("), "| cached:", cached)
