# Tutoring Invoice Builder

I tutor on the side, and every month I had to make invoices for the classes I
taught. That meant opening Google Calendar, going through the whole month,
finding every class, and manually typing each one into an application like [Wave](https://www.waveapps.com/) as a line item:
the date, the student, how long the class was, the rate. It took me around 30
minutes each month and it was tedious and easy to get wrong.

This tool does that for me. It reads my Google Calendar for a given month,
figures out each class and how long it ran, and builds an invoice I can finish
in a few seconds. What used to take half an hour now takes almost no time.

## How it works

Run one command for the month you want:

```
python invoice.py --month september --year 2026
```

You can also bill a range of months in one invoice:

```
python invoice.py --month september-december --year 2026
```

It pulls every event from your Google Calendar for that month (or range) and opens a page
in your browser with two halves:

- **Left:** a list of every class that month, with a search box.
- **Right:** an invoice laid out like the one Wave produces.

On that page you:

1. Search for a student or group (for example "Siya Advanced") and tick the
   classes you want on this invoice.
2. Pick who to bill from a dropdown.
3. Change anything you need by clicking on it: the rate, a date, a
   description, the invoice number. The total updates as you go.
4. Click **Export PDF** and save it. Done.

The length of each class comes straight from the event's start and end times,
so a one-hour class shows as quantity 1 and a 90-minute class shows as 1.5, at
your hourly rate. You don't have to write the duration anywhere.

Because I bill two different people off the same calendar (a tutoring company
and one private student), I usually run it once and export twice: select the
company's classes and export the first invoice, then clear the selection,
select the private student, switch the recipient, and export the second.

## Setup

### 1. Install the dependencies

You need Python 3.10 or newer. From the project folder:

```
pip install -r requirements.txt
```

### 2. Copy the example config

```
cp config.example.yaml config.yaml
```

Open `config.yaml` and put in your name and address, your usual hourly rate,
and the people you bill. Your real `config.yaml` is kept out of git, so your
personal details are never committed.

### 3. Connect Google Calendar

The tool needs read-only access to your calendar. This is a free, one-time
setup in Google Cloud:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and
   create a project (or pick one you already have).
2. Search for **Google Calendar API** and click **Enable**.
3. Open **APIs & Services → OAuth consent screen**, choose **External**, give
   the app a name, and add your own Google account under **Test users**.
4. Open **APIs & Services → Credentials → Create Credentials → OAuth client
   ID**. For application type choose **Desktop app** (this part matters; a Web
   application type will fail with a redirect error).
5. Download the JSON and save it in the project folder as `credentials.json`.
   See `credentials.example.json` for the shape it should have. A Desktop app
   file starts with `"installed"`.

The first time you run the tool it opens a browser asking you to sign in and
approve access. After that it remembers you, so you only do this once.

## Everyday use

```
python invoice.py --month september --year 2026
```

- `--month` takes a name or a number (`--month 9` or `--month sep` both work).
- `--month` also takes a range with a dash, like `september-december` or
  `9-12`, to put several months on one invoice. If the end month is earlier
  than the start (for example `november-february`), it rolls into the next
  year automatically. The invoice is then titled by its span (for example
  "SEPTEMBER–DECEMBER INVOICE") and dated to the end of the last month.
- `--year` is optional and defaults to the current year. For a range, it's the
  year the range starts in.

The invoice number is remembered between runs and goes up automatically. You
can also set it directly:

```
python invoice.py --set-number 7
```

When you export, the dropdown and the editing controls are hidden, so the PDF
shows only the clean invoice.

## Files

| File | What it does |
|------|--------------|
| `invoice.py` | The command you run: fetches the month and builds the page |
| `calendar_client.py` | Signs in to Google and reads your calendar |
| `invoice_model.py` | Prepares the invoice data and tracks the invoice number |
| `templates/invoice.html.j2` | The invoice page you edit in the browser |
| `config.example.yaml` | Template for your own `config.yaml` |
| `credentials.example.json` | Shows what the Google credentials file looks like |

## Notes

- The tool only reads your calendar. It never changes or deletes anything.
- Personal events (appointments, lunch) just sit in the list unticked and
  never end up on an invoice.
- Recurring classes show up as individual dated entries.
- For the cleanest PDF, turn off headers and footers in your browser's print
  dialog and leave the margins at default.
- `config.yaml`, `credentials.json`, and `token.json` hold personal or secret
  information and are gitignored. Don't commit or share them.
