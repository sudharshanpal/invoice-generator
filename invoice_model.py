"""Builds the data payload for the invoice page and tracks invoice numbers."""

from __future__ import annotations

import datetime as dt
import json
import os
from dataclasses import asdict, dataclass

from calendar_client import CalendarEvent

STATE_FILE = "state.json"
DEFAULT_START_NUMBER = 6


def peek_next_invoice_number() -> int:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return int(json.load(f).get("next_invoice_number", DEFAULT_START_NUMBER))
        except (ValueError, json.JSONDecodeError):
            return DEFAULT_START_NUMBER
    return DEFAULT_START_NUMBER


def set_next_invoice_number(value: int) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"next_invoice_number": int(value)}, f, indent=2)


def bump_invoice_number() -> int:
    current = peek_next_invoice_number()
    set_next_invoice_number(current + 1)
    return current


@dataclass
class LineItem:
    date_label: str
    description: str
    quantity: float  # hours
    rate: float


def event_to_line_item(event: CalendarEvent, default_rate: float) -> dict:
    data = asdict(
        LineItem(
            date_label=event.date_label,
            description=event.title,
            quantity=event.duration_hours,
            rate=default_rate,
        )
    )
    data["start_iso"] = event.start.isoformat()
    return data


def _long_date(d: dt.date) -> str:
    return d.strftime("%B ") + str(d.day) + f", {d.year}"


def _month_end(year: int, month: int) -> dt.date:
    if month == 12:
        first_of_next = dt.date(year + 1, 1, 1)
    else:
        first_of_next = dt.date(year, month + 1, 1)
    return first_of_next - dt.timedelta(days=1)


def build_page_payload(
    events: list[CalendarEvent],
    config: dict,
    start_year: int,
    start_month: int,
    end_year: int | None = None,
    end_month: int | None = None,
) -> dict:
    if end_year is None:
        end_year = start_year
    if end_month is None:
        end_month = start_month

    default_rate = float(config["invoice"].get("default_rate", 25.00))
    terms_days = int(config["invoice"].get("payment_terms_days", 15))

    # Invoice date is the last day of the final billed month.
    invoice_date = _month_end(end_year, end_month)
    due_date = invoice_date + dt.timedelta(days=terms_days)

    start_name = dt.date(start_year, start_month, 1).strftime("%B").upper()
    end_name = dt.date(end_year, end_month, 1).strftime("%B").upper()
    is_range = (start_year, start_month) != (end_year, end_month)
    title_span = f"{start_name}\u2013{end_name}" if is_range else start_name

    return {
        "business": config["business"],
        "recipients": config["recipients"],
        "currency": config["business"].get("currency", "CAD"),
        "invoice_title": f"{title_span} INVOICE",
        "invoice_number": peek_next_invoice_number(),
        "invoice_date": _long_date(invoice_date),
        "due_date": _long_date(due_date),
        "default_rate": default_rate,
        "events": [event_to_line_item(e, default_rate) for e in events],
    }
