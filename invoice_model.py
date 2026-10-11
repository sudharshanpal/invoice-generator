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


def build_page_payload(
    events: list[CalendarEvent],
    config: dict,
    year: int,
    month: int,
) -> dict:
    default_rate = float(config["invoice"].get("default_rate", 25.00))
    terms_days = int(config["invoice"].get("payment_terms_days", 15))

    # Default the invoice date to the last day of the billed month.
    if month == 12:
        next_month = dt.date(year + 1, 1, 1)
    else:
        next_month = dt.date(year, month + 1, 1)
    invoice_date = next_month - dt.timedelta(days=1)
    due_date = invoice_date + dt.timedelta(days=terms_days)

    month_name = dt.date(year, month, 1).strftime("%B").upper()

    return {
        "business": config["business"],
        "recipients": config["recipients"],
        "currency": config["business"].get("currency", "CAD"),
        "invoice_title": f"{month_name} INVOICE",
        "invoice_number": peek_next_invoice_number(),
        "invoice_date": _long_date(invoice_date),
        "due_date": _long_date(due_date),
        "default_rate": default_rate,
        "events": [event_to_line_item(e, default_rate) for e in events],
    }
