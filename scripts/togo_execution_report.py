"""Write one year of Togo's budget execution to an xlsx file: the DGBF's standard tables,
its execution report tables (--sigfip) or a ministry's compte administratif (--ca).

Reads boost.tgo_execution and boost.tgo_execution_detail straight from the configured
database (no query cache), with the same environment as the dashboard:

    python scripts/togo_execution_report.py --year 2025 --out execution_2025.xlsx
    python scripts/togo_execution_report.py --year 2025 --sigfip --out sigfip_2025.xlsx
    python scripts/togo_execution_report.py --year 2025 --ca --ministry 210 --out ca_210_2025.xlsx
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.togo_ca_report import build_ca_report  # noqa: E402
from components.togo_execution import normalise_detail, normalise_execution  # noqa: E402
from components.togo_execution_report import build_report  # noqa: E402
from components.togo_sigfip_report import build_sigfip_report  # noqa: E402
from queries import QueryService  # noqa: E402


def _content(args):
    service = QueryService.get_instance()
    if args.ca:
        detail = service.get_togo_execution_detail(args.year, args.ministry, persistent=False)
        return build_ca_report(normalise_detail(detail), args.year, args.ministry)
    df = normalise_execution(service.get_togo_execution_data(persistent=False))
    if args.sigfip:
        detail = service.get_togo_execution_detail(args.year, persistent=False)
        return build_sigfip_report(df, normalise_detail(detail), args.year)
    return build_report(df, args.year)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--year", type=int, required=True, help="budget year, e.g. 2025")
    parser.add_argument("--out", required=True, help="path of the xlsx file to write")
    workbook = parser.add_mutually_exclusive_group()
    workbook.add_argument("--sigfip", action="store_true", help="the DGBF's execution report tables")
    workbook.add_argument("--ca", action="store_true", help="the compte administratif of --ministry")
    parser.add_argument("--ministry", help="ministry (section) code for --ca, e.g. 210")
    args = parser.parse_args(argv)
    if args.ca and not args.ministry:
        parser.error("--ca requires --ministry")

    try:
        content = _content(args)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    with open(args.out, "wb") as f:
        f.write(content)
    print(f"{args.out}: {len(content)} bytes, year {args.year}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
