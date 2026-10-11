"""Command-line entry point: fetch events for a month or range and build the page.

Examples:
    python invoice.py --month september --year 2026
    python invoice.py --month 9
    python invoice.py --month september-december --year 2026
    python invoice.py --set-number 6
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import webbrowser

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from calendar_client import fetch_events_for_range
from invoice_model import (
    build_page_payload,
    peek_next_invoice_number,
    set_next_invoice_number,
)

CONFIG_FILE = "config.yaml"
TEMPLATE_DIR = "templates"
TEMPLATE_NAME = "invoice.html.j2"
OUTPUT_DIR = "output"

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def parse_month(value: str) -> int:
    value = value.strip().lower()
    if value.isdigit():
        n = int(value)
        if 1 <= n <= 12:
            return n
        raise argparse.ArgumentTypeError(f"month number out of range: {n}")
    if value in MONTHS:
        return MONTHS[value]
    for name, num in MONTHS.items():
        if name.startswith(value):
            return num
    raise argparse.ArgumentTypeError(f"unrecognized month: {value}")


def parse_month_range(value: str, start_year: int):
    """Parse '--month' into (start_year, start_month, end_year, end_month).

    Accepts a single month ('september') or a range ('september-december').
    If the end month is not after the start month, the range is assumed to
    roll into the next year (e.g. 'november-february').
    """
    parts = [p for p in value.replace("..", "-").split("-") if p.strip()]
    if len(parts) == 1:
        m = parse_month(parts[0])
        return start_year, m, start_year, m
    if len(parts) == 2:
        start_m = parse_month(parts[0])
        end_m = parse_month(parts[1])
        end_year = start_year if end_m >= start_m else start_year + 1
        return start_year, start_m, end_year, end_m
    raise argparse.ArgumentTypeError(f"could not parse month range: {value}")


def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        sys.exit(f"Config not found: {CONFIG_FILE}")
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def render_page(payload: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml", "j2"]),
    )
    template = env.get_template(TEMPLATE_NAME)
    return template.render(payload=payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an invoice from Google Calendar.")
    parser.add_argument("--month",
                        help="Month or range, e.g. 'september', '9', or "
                             "'september-december'.")
    parser.add_argument("--year", type=int, default=dt.date.today().year,
                        help="Year (defaults to current year).")
    parser.add_argument("--set-number", type=int,
                        help="Set the next invoice number and exit.")
    parser.add_argument("--no-open", action="store_true",
                        help="Do not auto-open the page in a browser.")
    args = parser.parse_args()

    if args.set_number is not None:
        set_next_invoice_number(args.set_number)
        print(f"Next invoice number set to {args.set_number}.")
        return

    if not args.month:
        parser.error("--month is required (unless using --set-number).")

    start_year, start_month, end_year, end_month = parse_month_range(
        args.month, args.year
    )

    config = load_config()
    calendar_id = config.get("calendar", {}).get("id", "primary")

    start_label = f"{dt.date(start_year, start_month, 1):%B %Y}"
    end_label = f"{dt.date(end_year, end_month, 1):%B %Y}"
    span = start_label if start_label == end_label else f"{start_label} - {end_label}"
    print(f"Fetching events for {span} ...")
    events = fetch_events_for_range(
        start_year, start_month, end_year, end_month, calendar_id
    )
    print(f"  found {len(events)} event(s).")

    payload = build_page_payload(
        events, config, start_year, start_month, end_year, end_month
    )

    html = render_page(payload)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if (start_year, start_month) == (end_year, end_month):
        out_name = f"invoice-{start_year}-{start_month:02d}.html"
    else:
        out_name = (f"invoice-{start_year}-{start_month:02d}"
                    f"_to_{end_year}-{end_month:02d}.html")
    out_path = os.path.join(OUTPUT_DIR, out_name)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    abs_path = os.path.abspath(out_path)
    print(f"\nInvoice builder ready:\n  {abs_path}")
    print(f"Next invoice number is {peek_next_invoice_number()} "
        "(edit it in the page if needed).")
    print("\nIn the page: search + tick classes, pick the recipient, edit "
        "anything, then click 'Export PDF' (choose 'Save as PDF').")

    if not args.no_open:
        webbrowser.open(f"file://{abs_path}")


if __name__ == "__main__":
    main()
