# Multiplex Management System

A simple Flask interface for the existing MySQL `MultiplexDB` database.
The application contains the dashboard, four live record counts, Movies,
Customers, Shows, Bookings, Payments and Food Orders management, and a read-only
connection check.

## Files

- `app.py`: dashboard, management routes, validation, and `check-db` command.
- `db.py`: environment configuration, connection, counts, and parameterized management queries.
- `templates/`: shared layout, dashboard, movie/customer/show pages, booking pages, and payment/food order list/form/details/delete pages.
- `tests/test_movies.py`, `tests/test_customers.py`, `tests/test_shows.py`, `tests/test_bookings.py`, `tests/test_payments.py`, `tests/test_food_orders.py`: automated checks that do not connect to MySQL.
- `static/`: custom CSS and local Bootstrap 5.3.8 CSS.
- `static/interface.js`: optional inline validation feedback and accessible table guidance; no requests or automatic submissions.
- `templates/shared/`: reusable success messages, error summaries and table guidance.
- `tests/test_interface.py`: shared UI checks, with no live database writes.
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
submit an add, edit, or delete form. Booking forms create reservations or change
their status; bookings have no delete action. Payment forms maintain records only;
they do not process money. Do not rerun `dbms.sql` during setup.

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

All forms that write records include a session token to prevent unwanted cross-site submissions.
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
- Shows management provides basic CRUD and input validation. It does not add
  screen-overlap detection.

At the Shows increment, all 44 automated tests passed: 18 Shows tests plus the existing 26 Movie and
Customer tests. Live MySQL checks covered listing, joined names, search, add,
edit, duplicate IDs, invalid references/prices/dates/times, unreferenced deletion,
and booking-blocked deletion through the Flask route. The temporary show was
deleted and a temporary booking was rolled back. Original records were unchanged.

## Bookings management

Open http://127.0.0.1:5000/bookings or choose Bookings in the sidebar.

- The list joins bookings to customers, shows, movies, seats and payments.
  Search matches part of a customer or movie name. View opens complete booking,
  customer, show, screen, multiplex, seat and payment details.
- Choose Create Booking, select an existing show, and click Load seats. This
  reloads the form, so choose the show before entering the remaining details.
  Customer, seat and payment choices all come from the existing database.
- Only seats in the show's screen without a Pending or Confirmed booking for
  that same show can be selected. Availability is checked again when saving.
  A seat can be booked for different shows independently.
- Booking IDs must be unique and contain 1–10 letters, numbers, hyphens or
  underscores. Date and time must be valid; historical dates are allowed.
  Total amount must be 0.01–999999.99 with at most two decimal places.
- New bookings may be Pending or Confirmed. Confirmation requires the linked
  payment's status to be Paid. Pending bookings reserve the seat too.
- On the details page, Pending bookings can be confirmed or cancelled, and
  Confirmed bookings can be cancelled. Cancelled bookings remain in history
  and cannot be reopened. Cancellation releases availability for that show.
  There is no booking deletion route or button.

### Transactions and the existing triggers

Each booking write runs in one transaction with commit on success and rollback
on failure. The app locks the existing show and seat rows before checking
availability, so simultaneous booking requests through the app cannot reserve
the same show/seat pair. Payment is also locked while its status is checked.

Creation first inserts Pending, invoking `prevent_double_booking`. If Confirmed
was selected, it then updates the status within the same transaction, invoking
`check_payment` and `update_seat_status`. Later status changes also run the
existing update triggers. The app does not install or change any trigger.

The legacy `update_seat_status` trigger writes a global `Seat_Status`, which
cannot represent reservations for multiple shows. It remains unchanged, but
the interface calculates availability from active bookings for each Show_ID
and Seat_ID instead. Cancellation in one show therefore does not free the
seat in another show that still has an active booking.

Existing schema limitations remain: a payment can be linked to multiple
bookings, and entered totals are not automatically reconciled against payment
amounts or ticket prices. Cancellation does not refund or modify payments.
The concurrency protection assumes booking writes use the app's locking
sequence; arbitrary external SQL still has the original schema's limitations.
Shows management still permits editing a booked show's screen, so keep that
screen consistent with existing reservations; mismatched seats cannot be
confirmed through this module. Payment records can now be edited in Payments;
there is no payment gateway.

### Booking test results

At the Bookings increment, all 63 automated tests passed: 19 booking tests and all 44 existing tests.
Run them with `python -m unittest discover -s tests -v`.

Separate live MySQL checks passed for joined listings/details, both searches,
Pending and paid Confirmed creation, unpaid confirmation rejection, duplicate
IDs/reservations, wrong-screen rejection, status changes, cancellation and
rebooking, and independent availability across shows. Direct SQL checks verified
the existing payment and duplicate triggers; confirmation/cancellation verified
the seat-status trigger. Two simultaneous same-show/seat requests produced
exactly one successful booking. Temporary records were removed, and snapshots
of every row in all ten tables matched before and after the checks.

## Payments management

Open http://127.0.0.1:5000/payments or choose Payments in the sidebar.

- The list uses `LEFT JOIN`s from Payment to Booking and Customer, including
  payments with no booking. Search by part of a Payment ID, Booking ID or
  customer name. Search characters such as `%` and `_` are treated literally.
- The schema permits multiple bookings to share a payment. Each association
  appears as a separate list row, so repeated amounts must not be summed as
  independent payments. View opens payment details and all associated bookings,
  with links to the existing booking details/status workflow.
- Record Payment creates a database record. IDs must be unique and contain
  1–10 letters, numbers, hyphens or underscores. They cannot be changed by editing.
- Amount must be 0.01–999999.99 with at most two decimal places. Modes are UPI,
  Card, Cash and Net Banking. Status is Paid or Pending. Dates must be valid
  calendar dates from 1000-01-01 to 9999-12-31; historical dates are allowed.
- Edit Payment updates its amount, mode, date and status. Marking it Paid does
  not confirm any booking. Open the associated pending booking and confirm it
  using the existing workflow. The existing `check_payment` trigger remains
  installed and unchanged and still rejects unpaid booking confirmation.
- A payment linked to any Confirmed booking cannot be set to Pending. The
  entire edit is rejected, including simultaneous changes to amount or mode.
  The check locks the payment row in a READ COMMITTED transaction, coordinating
  with the existing booking confirmation lock. No changes to booking code are
  needed. A concurrent confirmation and downgrade cannot both succeed through
  these application workflows.
- Delete opens a confirmation page. Only POST deletes a record. MySQL blocks
  deletion if any booking references the payment, including cancelled bookings.
  Errors roll back the operation and show a meaningful message.
- These pages record information only: they do not collect money, charge a
  card, verify a bank payment, transfer funds or issue refunds.

At the Payments increment, all 86 automated tests passed: 23 Payment tests plus the existing 63 tests.
Run `python -m unittest discover -s tests -v` to repeat these mocked checks;
they do not connect to or change MySQL.

Separate live MySQL checks passed for joined listings/details, all three search
fields, creation, edits, status changes, duplicate IDs, invalid values, deleting
unreferenced records, and blocking deletion of referenced records. Checks also
covered shared payments, the confirmed-booking downgrade guard, manual booking
confirmation after marking Paid, the existing `check_payment` trigger directly,
and a simultaneous confirmation/downgrade. All temporary records were removed;
every original row in all ten tables and all trigger definitions matched the
pre-test snapshot. Browser checks verified the list, details and edit form.

Remaining schema limitations: payment amounts are not reconciled automatically
against linked booking totals, shared payments remain permitted, and edits do
not have a separate audit-history table. The downgrade guard protects writes
through this application; direct external SQL still has the original schema's
limitations. No tables or triggers were created or changed.

## Food Orders management

Open http://127.0.0.1:5000/food-orders or choose Food Orders in the sidebar.

- The list displays Order ID, Booking ID, customer, movie, item, quantity and
  total price. SQL joins connect Food_Order to Booking, Customer, Show and Movie.
  LEFT JOINs keep legacy records with nullable relationships visible.
- Search matches part of an Order ID, Booking ID, customer name or item name.
  Apostrophes and wildcard characters such as `%` and `_` are treated literally.
- Add Food Order uses existing bookings in a dropdown with customer, movie and
  booking status for context. Enter the item name yourself; no menu is created.
- Order IDs must be unique and contain 1–10 letters, numbers, hyphens or
  underscores. Item names are required and allow up to 100 characters.
  Quantity must be a whole number from 1 to 2147483647. Total price must be
  0.01–999999.99 with at most two decimal places, matching the existing columns.
- Edit permits changing the booking, item name, quantity and total price.
  Order ID remains fixed. Both add and edit validate inputs on the server;
  the foreign key also rejects bookings removed after validation.
- View displays all order fields and joined booking context. Open Booking
  links to the existing booking details page.
- Delete opens a confirmation page; only submitting its form deletes the row.
  The booking remains unchanged. Constraint failures display a friendly error.
  All writes use bound SQL parameters, commit on success and roll back on error.

All 110 automated tests passed, including 24 Food Orders tests and all 86 prior
tests. Repeat them with `python -m unittest discover -s tests -v`; these tests
mock MySQL and never change database records.

Live MySQL checks passed for joined listings, all four search fields, creation,
duplicate IDs, invalid inputs, editing/reassigning bookings, unchanged edits,
details and deletion. Direct invalid-reference checks verified real foreign-key
rejection and rollback. All temporary orders were removed; snapshots confirmed
every original row in all ten tables, table definitions and triggers unchanged.
Browser checks passed for the list, details, edit form and delete confirmation.

The existing schema has no table referencing Food_Order, so blocked deletion
was tested with mocked constraint errors rather than changing the schema.
Totals are entered manually; there is no unit-price calculation, inventory or
menu. Any existing booking is selectable, including cancelled bookings, and
food-order changes do not update booking totals or payments.

## Eight Golden Rules: interface improvements

The existing sidebar, cards, Bootstrap layout and purple colour palette are
preserved. These changes improve the current interface without changing Python
routes, SQL queries, validation rules, booking/payment logic or the database.

| Rule | Practical implementation |
| --- | --- |
| Strive for consistency | Shared success/error markup, consistent secondary Edit/Cancel actions, purple primary buttons and wrapping action rows. |
| Seek universal usability | Visible keyboard focus, linked input help, a working skip-to-content focus target, named keyboard-scrollable table regions, stronger input borders and 44px mobile buttons/navigation. |
| Offer informative feedback | Existing specific error messages remain visible in consistent alerts; native input errors also appear beside fields. Successful operations show a persistent Completed message. |
| Design dialogs to yield closure | Successful redirects retain clear completion feedback. Existing deletion pages identify the record, explain the consequence and require explicit submission. |
| Prevent errors | Required fields are marked with an asterisk and explained. Existing required/min/max/pattern constraints and all server validation remain intact. Invalid fields expose aria-invalid and descriptive errors. |
| Permit easy reversal | All forms have Cancel/Back links. Delete pages have both Back and Cancel. The booking status form can be reset with Cancel; existing Edit actions remain available. |
| Keep users in control | No automatic submissions, saves, booking confirmations or new popups. Changing selections never writes records; users still press the relevant submit button. |
| Reduce short-term memory load | Helpful placeholders, existing descriptive dropdowns and selected-show details stay visible. Counts/captions appear above tables, and entered values remain available after validation errors. |

Validation feedback is a small progressive enhancement: the shared script uses
the browser's existing constraints to display inline messages, clears them as
fields are corrected, and focuses the server error summary after a failed
request. It does not replace server validation or issue network requests.
Rules that only the server can check, such as duplicate IDs and foreign-key
restrictions, continue to appear in the summary rather than being guessed in
JavaScript. Without JavaScript, native browser validation and server summaries
still work; inline feedback and automatic summary focus are unavailable.

Verification: all 118 automated tests passed (the original 110 plus eight shared
interface tests). All 27 live page variants loaded against MySQL; invalid forms,
error presentation and Cancel/Back destinations passed. Success feedback was
tested with mocked writes so no live records needed to be changed. Browser
checks covered all module lists at 390px and 1280px, and forms at 320px, 390px
and 1280px, plus the full selected-show booking form on mobile. Pages did not
overflow horizontally; wide tables scroll within their regions. Keyboard
scrolling, correction of inline errors, server-error focus and retained inputs
were checked. The checked text colours exceed 4.5:1 contrast and input borders
exceed 3:1 against white. This is not a complete screen-reader or cross-browser
accessibility audit.

Live checks used reads and invalid submissions only. Database snapshots verified
all original records, table definitions and triggers unchanged; no temporary
records required cleanup. Wide tables intentionally retain horizontal scrolling
on small screens instead of changing the existing table layout.

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

The dashboard query is fixed SQL with no input values. Management form and search
values are passed separately using Connector/Python `%s` parameters, never
inserted into the SQL text. Each write commits on success and rolls back
on a database error. Cursors and connections are closed after use. Existing
report queries remain available in the original SQL file.
