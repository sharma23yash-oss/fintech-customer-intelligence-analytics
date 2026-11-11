"""Command line interface.

  python -m friction_detector.cli build-db
  python -m friction_detector.cli run-daily --as-of 2026-10-31
  python -m friction_detector.cli replay --start 2026-10-24 --end 2026-10-31
"""
import argparse
import json

from . import config as C
from . import db, reports


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="friction_detector", description="Brokerage Friction Detector (SYNTHETIC data)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build-db", help="build SQLite database from data/synthetic/*.csv")
    d = sub.add_parser("run-daily", help="run detection for one as-of date and write the daily reports")
    d.add_argument("--as-of", default=C.SNAPSHOT_DATE)
    d.add_argument("--llm", action="store_true", help="use the optional LLM for the summary wording if a key is configured")
    r = sub.add_parser("replay", help="run consecutive days so 'newly flagged' can be computed")
    r.add_argument("--start", default="2026-10-24")
    r.add_argument("--end", default=C.SNAPSHOT_DATE)
    a = p.parse_args(argv)
    if a.cmd == "build-db":
        print(json.dumps(db.build_database(), indent=2))
    elif a.cmd == "run-daily":
        res = reports.run_daily(as_of=a.as_of, use_llm=a.llm)
        print(json.dumps(res["manifest"], indent=2))
        print("reports written to", res["out_dir"])
    elif a.cmd == "replay":
        for s in reports.replay(start=a.start, end=a.end):
            print(f"{s['run_date']}: flagged={s['flagged']:,} new={s['newly_flagged']:,} dropped={s['no_longer_flagged']:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
