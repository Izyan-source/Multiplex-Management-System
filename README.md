# Multiplex Management System

A simple Flask interface for the existing MySQL `MultiplexDB` database.
This first increment contains only the dashboard, four live record counts,
and a read-only connection check. Other navigation sections are disabled until
their pages are built.

## Files

- `app.py`: dashboard route and `check-db` command.
- `db.py`: environment configuration, MySQL connection, and count query.
- `templates/`: shared layout and dashboard HTML.
- `static/`: custom CSS and local Bootstrap 5.3.8 CSS.
- `.env.example`: connection settings template.
- `dbms.sql`: original project file, unchanged and never executed by the app.

## Setup

Python 3.9 or newer and your existing MySQL server are required.

```sh
cd "/Users/apple/Desktop/dbms lab"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

If `.venv` already exists, just activate it and install the requirements.
Copy the configuration template once (skip this if you already have `.env`):

```sh
cp .env.example .env
```

Edit `.env` with your existing MySQL username and password. Keep
`DB_NAME=MultiplexDB`. Change the host or port if your server uses other values.
For an intentionally empty MySQL password, use `DB_PASSWORD=""`.
Keep passwords quoted, particularly when they contain spaces or `#`.
The `.env` file is excluded from Git. Exported environment variables take
priority over `.env` values. Restart Flask after changing connection settings.

The application connects to an existing database only. It does not create,
import, reset, seed, or modify any database objects or records. Do not rerun
`dbms.sql` as part of application setup.

## Test the database connection

Ensure your MySQL server is running, then run:

```sh
python -m flask --app app check-db
```

This performs the same read-only query as the dashboard and prints the selected
database and actual counts. A failure produces an error message and a nonzero
exit status. No MySQL command-line client is required.

If the database still has exactly the original sample records, expect 8 movies,
15 customers, 15 bookings, and 5 multiplexes. These numbers are a reference for
manual checking only; the application always queries MySQL.

## Run the application

```sh
python -m flask --app app run
```

Open http://127.0.0.1:5000 in your browser. Stop with Ctrl+C.
If port 5000 is occupied, run `python -m flask --app app run --port 5001`
and open http://127.0.0.1:5001 instead. `python app.py` also runs on port 5000.

Refresh the dashboard to re-read the database. Counts include all dates and
all booking statuses. A real zero is displayed as `0`. If configuration or a
database read fails, the page displays an explanation and unavailable markers
instead of fabricated counts, and returns HTTP 503.

## Connection troubleshooting

- **Missing DB_USER:** create `.env` from `.env.example` and fill in your login.
- **Cannot reach MySQL:** check the server, `DB_HOST`, and `DB_PORT`.
- **Login rejected:** verify the existing MySQL username and password.
- **Database/table missing:** verify the connection points to the existing
  `MultiplexDB` containing `Movie`, `Customer`, `Booking`, and `Multiplex`.
  Table name capitalization matters on some MySQL installations.
- **Permission denied:** use an existing account allowed to read these tables.

## How it works

A browser request calls the Flask dashboard route. `db.py` opens a connection,
runs one `SELECT` containing four `COUNT(*)` subqueries, returns a dictionary,
and closes the cursor and connection. Jinja renders the results into HTML.
Bootstrap is stored locally, so styling works without internet access.

The current query is fixed SQL with no input values. When forms are added,
their values will be passed separately using Connector/Python `%s` parameters,
never string concatenation. Existing report queries and booking triggers will
be integrated in later increments; this dashboard does not fire any triggers.
