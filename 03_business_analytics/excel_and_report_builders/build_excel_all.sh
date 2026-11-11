#!/usr/bin/env bash
# Build -> recalculate (LibreOffice) -> finalise (XLOOKUP) for the Excel analytics workbook.
# ARCHIVAL BUILDER: needs LibreOffice and an xlsx recalculation helper (set RECALC=/path/to/recalc.py). The committed
# workbook is already built; you only need this to regenerate it.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
: "${RECALC:?Set RECALC to a recalc.py that recalculates an .xlsx in place with LibreOffice (see README of this folder)}"
python3 "$HERE/16_build_advanced_excel.py"
python3 "$RECALC" "$HERE/../excel/Fintech_Advanced_Excel_Analytics.xlsx" 500
python3 "$HERE/17_finalize_excel.py"
