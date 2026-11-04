# Multiplex Management System

A simple Flask interface for the existing MySQL `MultiplexDB` database.
The application contains the dashboard, four live record counts, Movies,
Customers and Shows management, and a read-only connection check. Other navigation sections remain
disabled until their pages are built.

## Files

- `app.py`: dashboard, Movies, Customers and Shows routes, validation, and `check-db` command.
- `db.py`: environment configuration, connection, counts, and movie/customer/show queries.
- `templates/`: shared layout, dashboard, and movie/customer/show list/add/edit/delete pages.
- `tests/test_movies.py`, `tests/test_customers.py`, `tests/test_shows.py`: automated checks that do not connect to MySQL.
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
import, reset, seed, or change the schema. Movie, customer and show records change only when you
submit an add, edit, or delete form. Do not rerun `dbms.sql` during setup.

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

## Movies management

Open http://127.0.0.1:5000/movies or choose Movies in the sidebar.

- View all six Movie fields and search by a partial movie name.
- Add Movie opens a form; Edit opens the existing movie's details.
- Movie IDs are unique, 1–10 letters/numbers/hyphens/underscores, and cannot
  be changed when editing. Name, genre, and language are required and respect
  their existing column lengths.
- Duration must be a positive integer. Rating must be 0–9.9 with at most
  one decimal place, because the existing column is `DECIMAL(2,1)`.
- Delete opens a confirmation page. Only submitting that form deletes a row.
  If an existing show references the movie, MySQL blocks deletion and the page
  explains why. No show or booking is deleted automatically.
- Database failures and duplicate IDs display messages without exposing credentials.

Movie, customer and show forms include a session token to prevent unwanted cross-site submissions.
The app generates a secret key for each run. An optional `SECRET_KEY` environment
variable can keep sessions stable across restarts. If a form expires after a
restart, reload it before submitting again.

Run the automated checks (no database changes):

```sh
python -m unittest discover -s tests -v
```

## Customers management

Open http://127.0.0.1:5000/customers or choose Customers in the sidebar.

- View Customer ID, name, phone, email, and gender. Search matches part of a
  customer name; apostrophes, `%`, and `_` are treated as literal search text.
- Register Customer opens a form. Edit uses the same form with existing values.
  Customer IDs must be unique and contain 1–10 letters, numbers, hyphens, or
  underscores. IDs cannot be changed when editing.
- Name is required, must contain a letter, and allows up to 100 characters.
  Unicode names, apostrophes, and hyphens are supported.
- Phone is stored as text to preserve leading zeros. Enter 7–15 digits with
  an optional leading `+`, within the existing 15-character column limit.
  Thus a number with `+` can have at most 14 digits. Spaces and dashes are not
  accepted; no country-specific validation or phone verification is performed.
- Email is required, limited to 100 characters, and checked for common email
  syntax. This checks formatting, not whether a mailbox exists.
- Gender choices are Male, Female, Other, and Not stated. All fit the existing
  `VARCHAR(10)` column. Existing records are displayed as stored.
- Delete opens a confirmation page. MySQL rejects deletion if any booking,
  including a cancelled booking, references the customer. The page explains
  the restriction; bookings are never deleted automatically.
- Duplicate IDs and validation failures keep submitted form values so they
  can be corrected. Database errors do not display passwords or raw SQL errors.

The initial implementation passed 14 customer tests and all 12 existing movie
tests. Live checks exercised registration, search, editing, duplicate IDs,
invalid input, deletion, and a real booking foreign-key rejection through the
Flask route. The temporary customer was removed and the temporary booking was
rolled back; original customer, movie, and booking records were unchanged.

## Shows management

Open http://127.0.0.1:5000/shows or choose Shows in the sidebar.

- View Show ID, movie name, screen name, date, time, and ticket price.
  SQL `LEFT JOIN`s connect `Show` to `Movie` and `Screen`, keeping older rows
  visible even when a nullable relationship is empty. Search by movie name.
- Schedule Show opens a form with movies and screens read from MySQL. Screen
  options include the multiplex name and screen ID to distinguish repeated names.
  No movies or screens are generated or hardcoded.
- Show IDs must be unique, 1–10 letters/numbers/hyphens/underscores, and remain
  unchanged during editing. Movie and screen selections are validated on every
  submission; MySQL foreign keys also protect against references removed concurrently.
- Dates must be valid calendar dates in MySQL's 1000–9999 year range. Historical
  dates remain allowed so existing sample shows can be edited. Times must be
  between 00:00:00 and 23:59:59; seconds are preserved when editing.
- Ticket price must be 0.01–999999.99 with up to two decimal places, matching
  the existing `DECIMAL(8,2)` column. Python uses `Decimal` for submitted prices.
- Delete requires confirmation. Any existing booking, including a cancelled
  booking, prevents deletion and produces an explanatory message.
- This increment provides basic CRUD and input validation. It does not add
  screen-overlap detection or a booking management workflow.

All 44 automated tests passed: 18 Shows tests plus the existing 26 Movie and
Customer tests. Live MySQL checks covered listing, joined names, search, add,
edit, duplicate IDs, invalid references/prices/dates/times, unreferenced deletion,
and booking-blocked deletion through the Flask route. The temporary show was
deleted and a temporary booking was rolled back. Original records were unchanged.

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

The dashboard query is fixed SQL with no input values. Movie/customer/show form and search
values are passed separately using Connector/Python `%s` parameters, never
inserted into the SQL text. Each movie/customer/show write commits on success and rolls back
on a database error. Cursors and connections are closed after use. Existing
report queries and booking workflows remain for later increments.
