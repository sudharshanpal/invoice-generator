"""Google Calendar authentication and event fetching."""

from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


@dataclass
class CalendarEvent:
    title: str
    start: dt.datetime
    end: dt.datetime

    @property
    def duration_hours(self) -> float:
        seconds = (self.end - self.start).total_seconds()
        return round(seconds / 3600.0, 4)

    @property
    def date_label(self) -> str:
        # %-d is not portable to Windows, so build the day without zero-padding.
        return self.start.strftime("%B ") + str(self.start.day)


def _get_credentials() -> Credentials:
    creds: Credentials | None = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"'{CREDENTIALS_FILE}' not found. Download your OAuth client "
                    "credentials from Google Cloud Console and save them here. "
                    "See the README for setup."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return creds


def _month_bounds(year: int, month: int) -> tuple[dt.datetime, dt.datetime]:
    start = dt.datetime(year, month, 1, tzinfo=dt.timezone.utc)
    if month == 12:
        end = dt.datetime(year + 1, 1, 1, tzinfo=dt.timezone.utc)
    else:
        end = dt.datetime(year, month + 1, 1, tzinfo=dt.timezone.utc)
    return start, end


def _parse_dt(value: dict) -> dt.datetime:
    # Timed events carry "dateTime"; all-day events carry "date".
    if "dateTime" in value:
        raw = value["dateTime"].replace("Z", "+00:00")
        return dt.datetime.fromisoformat(raw)
    return dt.datetime.fromisoformat(value["date"]).replace(
        tzinfo=dt.timezone.utc
    )


def fetch_events_for_month(
    year: int, month: int, calendar_id: str = "primary"
) -> list[CalendarEvent]:
    return fetch_events_for_range(year, month, year, month, calendar_id)


def fetch_events_for_range(
    start_year: int,
    start_month: int,
    end_year: int,
    end_month: int,
    calendar_id: str = "primary",
) -> list[CalendarEvent]:
    creds = _get_credentials()
    service = build("calendar", "v3", credentials=creds)

    time_min, _ = _month_bounds(start_year, start_month)
    _, time_max = _month_bounds(end_year, end_month)

    events: list[CalendarEvent] = []
    page_token = None
    while True:
        response = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                pageToken=page_token,
                maxResults=2500,
            )
            .execute()
        )

        for item in response.get("items", []):
            start_obj = item.get("start", {})
            end_obj = item.get("end", {})
            if not start_obj or not end_obj:
                continue
            events.append(
                CalendarEvent(
                    title=item.get("summary", "(no title)"),
                    start=_parse_dt(start_obj),
                    end=_parse_dt(end_obj),
                )
            )

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    events.sort(key=lambda e: e.start)
    return events
