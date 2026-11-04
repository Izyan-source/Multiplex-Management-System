"""Queries for the existing MySQL database. No schema or seed operations."""

import os
from pathlib import Path

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv


# Read .env next to this file; existing environment variables take priority.
load_dotenv(Path(__file__).parent / ".env")


def get_connection():
    """Open one connection using environment variables."""
    if not os.getenv("DB_USER"):
        raise ValueError("Set DB_USER and your connection details in .env first.")

    try:
        port = int(os.getenv("DB_PORT", "3306"))
    except ValueError:
        raise ValueError("DB_PORT must be a number between 1 and 65535.") from None
    if not 1 <= port <= 65535:
        raise ValueError("DB_PORT must be a number between 1 and 65535.")

    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=port,
        user=os.environ["DB_USER"],
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "MultiplexDB"),
        connection_timeout=5,
    )


def get_dashboard_counts():
    """Fetch all four totals in one read-only statement."""
    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        # These are fixed identifiers, with no user input to interpolate.
        # Future queries with form values must bind them with %s parameters.
        cursor.execute("""
            SELECT
                DATABASE() AS database_name,
                (SELECT COUNT(*) FROM Movie) AS movies,
                (SELECT COUNT(*) FROM Customer) AS customers,
                (SELECT COUNT(*) FROM Booking) AS bookings,
                (SELECT COUNT(*) FROM Multiplex) AS multiplexes
        """)
        return cursor.fetchone()
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            connection.close()


def database_error_message(error):
    """Give useful setup advice without exposing credentials or raw SQL."""
    if isinstance(error, ValueError):
        return str(error)
    if error.errno in (1045, 1698):
        return "MySQL rejected the login. Check DB_USER and DB_PASSWORD in .env."
    if error.errno == 1049:
        return "Database not found. Point DB_NAME to your existing MultiplexDB database."
    if error.errno in (1044, 1142):
        return "This MySQL user does not have permission to read the required tables."
    if error.errno == 1146:
        return "A dashboard table is missing. Check that you selected your existing MultiplexDB database."
    if error.errno in (2002, 2003, 2005):
        return "Cannot reach MySQL. Check that the server is running and DB_HOST and DB_PORT are correct."
    return "Could not read the dashboard. Check your MySQL connection and database settings."


def get_movies(search=""):
    """Search names literally, including names containing % or _."""
    pattern = "%" + search.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"
    with get_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT Movie_ID, Movie_Name, Genre, Language, Duration_Min, Rating
                FROM Movie
                WHERE %s = '' OR Movie_Name LIKE %s ESCAPE '!'
                ORDER BY Movie_Name, Movie_ID
            """, (search, pattern))
            return cursor.fetchall()


def get_movie(movie_id):
    with get_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT Movie_ID, Movie_Name, Genre, Language, Duration_Min, Rating
                FROM Movie WHERE Movie_ID = %s
            """, (movie_id,))
            return cursor.fetchone()


def add_movie(movie):
    with get_connection() as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO Movie
                        (Movie_ID, Movie_Name, Genre, Language, Duration_Min, Rating)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (movie["Movie_ID"], movie["Movie_Name"], movie["Genre"],
                      movie["Language"], movie["Duration_Min"], movie["Rating"]))
            connection.commit()
        except Error:
            connection.rollback()
            raise


def update_movie(movie_id, movie):
    """Return False if the movie was removed, but allow unchanged submissions."""
    with get_connection() as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE Movie SET Movie_Name = %s, Genre = %s, Language = %s,
                        Duration_Min = %s, Rating = %s
                    WHERE Movie_ID = %s
                """, (movie["Movie_Name"], movie["Genre"], movie["Language"],
                      movie["Duration_Min"], movie["Rating"], movie_id))
                cursor.execute("SELECT Movie_ID FROM Movie WHERE Movie_ID = %s", (movie_id,))
                exists = cursor.fetchone() is not None
            connection.commit()
            return exists
        except Error:
            connection.rollback()
            raise


def delete_movie(movie_id):
    """MySQL rejects deletion if a Show still references this movie."""
    with get_connection() as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM Movie WHERE Movie_ID = %s", (movie_id,))
                deleted = cursor.rowcount > 0
            connection.commit()
            return deleted
        except Error:
            connection.rollback()
            raise


def get_customers(search=""):
    """Search names literally, including names containing % or _."""
    pattern = "%" + search.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"
    with get_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT Customer_ID, Customer_Name, Phone, Email, Gender
                FROM Customer
                WHERE %s = '' OR Customer_Name LIKE %s ESCAPE '!'
                ORDER BY Customer_Name, Customer_ID
            """, (search, pattern))
            return cursor.fetchall()


def get_customer(customer_id):
    with get_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT Customer_ID, Customer_Name, Phone, Email, Gender
                FROM Customer WHERE Customer_ID = %s
            """, (customer_id,))
            return cursor.fetchone()


def add_customer(customer):
    with get_connection() as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO Customer
                        (Customer_ID, Customer_Name, Phone, Email, Gender)
                    VALUES (%s, %s, %s, %s, %s)
                """, (customer["Customer_ID"], customer["Customer_Name"], customer["Phone"],
                      customer["Email"], customer["Gender"]))
            connection.commit()
        except Error:
            connection.rollback()
            raise


def update_customer(customer_id, customer):
    """Return False if the customer was removed, but allow unchanged submissions."""
    with get_connection() as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE Customer SET Customer_Name = %s, Phone = %s, Email = %s, Gender = %s
                    WHERE Customer_ID = %s
                """, (customer["Customer_Name"], customer["Phone"], customer["Email"],
                      customer["Gender"], customer_id))
                cursor.execute("SELECT Customer_ID FROM Customer WHERE Customer_ID = %s", (customer_id,))
                exists = cursor.fetchone() is not None
            connection.commit()
            return exists
        except Error:
            connection.rollback()
            raise


def delete_customer(customer_id):
    """MySQL rejects deletion if a Booking still references this customer."""
    with get_connection() as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM Customer WHERE Customer_ID = %s", (customer_id,))
                deleted = cursor.rowcount > 0
            connection.commit()
            return deleted
        except Error:
            connection.rollback()
            raise


def get_shows(search=""):
    """LEFT JOIN keeps older shows visible even if a nullable reference is empty."""
    pattern = "%" + search.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"
    with get_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT s.Show_ID, m.Movie_Name, sc.Screen_Name,
                       s.Show_Date, CAST(s.Show_Time AS CHAR) AS Show_Time, s.Ticket_Price
                FROM `Show` AS s
                LEFT JOIN Movie AS m ON s.Movie_ID = m.Movie_ID
                LEFT JOIN Screen AS sc ON s.Screen_ID = sc.Screen_ID
                WHERE %s = '' OR m.Movie_Name LIKE %s ESCAPE '!'
                ORDER BY s.Show_Date DESC, s.Show_Time, s.Show_ID
            """, (search, pattern))
            return cursor.fetchall()


def get_show(show_id):
    with get_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT s.Show_ID, s.Movie_ID, s.Screen_ID, m.Movie_Name, sc.Screen_Name,
                       s.Show_Date, CAST(s.Show_Time AS CHAR) AS Show_Time, s.Ticket_Price
                FROM `Show` AS s
                LEFT JOIN Movie AS m ON s.Movie_ID = m.Movie_ID
                LEFT JOIN Screen AS sc ON s.Screen_ID = sc.Screen_ID
                WHERE s.Show_ID = %s
            """, (show_id,))
            return cursor.fetchone()


def get_screens():
    """Multiplex name and screen ID distinguish screens with the same name."""
    with get_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT s.Screen_ID, s.Screen_Name, m.Multiplex_Name
                FROM Screen AS s
                LEFT JOIN Multiplex AS m ON s.Multiplex_ID = m.Multiplex_ID
                ORDER BY m.Multiplex_Name, s.Screen_Name, s.Screen_ID
            """)
            return cursor.fetchall()


def add_show(show):
    with get_connection() as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO `Show`
                        (Show_ID, Movie_ID, Screen_ID, Show_Date, Show_Time, Ticket_Price)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (show["Show_ID"], show["Movie_ID"], show["Screen_ID"],
                      show["Show_Date"], show["Show_Time"], show["Ticket_Price"]))
            connection.commit()
        except Error:
            connection.rollback()
            raise


def update_show(show_id, show):
    """Return False for a removed show; unchanged submissions are successful."""
    with get_connection() as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE `Show` SET Movie_ID = %s, Screen_ID = %s, Show_Date = %s,
                        Show_Time = %s, Ticket_Price = %s
                    WHERE Show_ID = %s
                """, (show["Movie_ID"], show["Screen_ID"], show["Show_Date"],
                      show["Show_Time"], show["Ticket_Price"], show_id))
                cursor.execute("SELECT Show_ID FROM `Show` WHERE Show_ID = %s", (show_id,))
                exists = cursor.fetchone() is not None
            connection.commit()
            return exists
        except Error:
            connection.rollback()
            raise


def delete_show(show_id):
    """An existing Booking foreign key blocks deletion in MySQL."""
    with get_connection() as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM `Show` WHERE Show_ID = %s", (show_id,))
                deleted = cursor.rowcount > 0
            connection.commit()
            return deleted
        except Error:
            connection.rollback()
            raise


class BookingRuleError(ValueError):
    """A booking rule failed; its message can be shown to the user."""


# Shared SELECT for the booking list and its complete details page.
BOOKING_SELECT = """
    SELECT b.Booking_ID, b.Customer_ID, b.Show_ID, b.Seat_ID, b.Payment_ID,
           b.Booking_Date, CAST(b.Booking_Time AS CHAR) AS Booking_Time,
           b.Total_Amount, b.Booking_Status,
           c.Customer_Name, c.Phone, c.Email,
           m.Movie_ID, m.Movie_Name, s.Show_Date,
           CAST(s.Show_Time AS CHAR) AS Show_Time, s.Ticket_Price,
           sc.Screen_ID, sc.Screen_Name, mx.Multiplex_Name,
           st.Seat_Number, st.Seat_Type,
           p.Amount AS Payment_Amount, p.Payment_Mode, p.Payment_Date, p.Payment_Status
    FROM Booking AS b
    LEFT JOIN Customer AS c ON b.Customer_ID = c.Customer_ID
    LEFT JOIN `Show` AS s ON b.Show_ID = s.Show_ID
    LEFT JOIN Movie AS m ON s.Movie_ID = m.Movie_ID
    LEFT JOIN Seat AS st ON b.Seat_ID = st.Seat_ID
    LEFT JOIN Payment AS p ON b.Payment_ID = p.Payment_ID
    LEFT JOIN Screen AS sc ON s.Screen_ID = sc.Screen_ID
    LEFT JOIN Multiplex AS mx ON sc.Multiplex_ID = mx.Multiplex_ID
"""


def get_bookings(search=""):
    pattern = "%" + search.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"
    with get_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(BOOKING_SELECT + """
                WHERE %s = '' OR c.Customer_Name LIKE %s ESCAPE '!'
                    OR m.Movie_Name LIKE %s ESCAPE '!'
                ORDER BY b.Booking_Date DESC, b.Booking_Time DESC, b.Booking_ID
            """, (search, pattern, pattern))
            return cursor.fetchall()


def get_booking(booking_id):
    with get_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(BOOKING_SELECT + " WHERE b.Booking_ID = %s", (booking_id,))
            return cursor.fetchone()


def get_booking_payments():
    """Read existing payment choices; this module never creates or edits payments."""
    with get_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT Payment_ID, Amount, Payment_Mode, Payment_Status
                FROM Payment ORDER BY Payment_ID
            """)
            return cursor.fetchall()


def get_available_seats(show_id):
    """Availability belongs to a show/seat pair, never Seat.Seat_Status."""
    with get_connection() as connection:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT st.Seat_ID, st.Seat_Number, st.Seat_Type
                FROM Seat AS st
                JOIN `Show` AS s ON st.Screen_ID = s.Screen_ID
                WHERE s.Show_ID = %s AND NOT EXISTS (
                    SELECT 1 FROM Booking AS b
                    WHERE b.Show_ID = s.Show_ID AND b.Seat_ID = st.Seat_ID
                        AND b.Booking_Status IN ('Pending', 'Confirmed')
                )
                ORDER BY st.Seat_Number, st.Seat_ID
            """, (show_id,))
            return cursor.fetchall()


def lock_booking_seat(cursor, show_id, seat_id):
    """All booking writes lock show then seat in the same order.

    The existing show row serializes reservations for that show, including when
    no booking yet exists. The seat lock also coordinates the legacy seat trigger
    across different shows using the same physical seat.
    """
    cursor.execute("SELECT Screen_ID FROM `Show` WHERE Show_ID = %s FOR UPDATE", (show_id,))
    show = cursor.fetchone()
    if show is None:
        raise BookingRuleError("The selected show no longer exists.")
    cursor.execute("SELECT Screen_ID FROM Seat WHERE Seat_ID = %s FOR UPDATE", (seat_id,))
    seat = cursor.fetchone()
    if seat is None or not show['Screen_ID'] or seat['Screen_ID'] != show['Screen_ID']:
        raise BookingRuleError("Select a seat belonging to this show's screen.")


def check_booking_availability(cursor, show_id, seat_id, exclude_booking_id=None):
    cursor.execute("""
        SELECT Booking_ID FROM Booking
        WHERE Show_ID = %s AND Seat_ID = %s
            AND Booking_Status IN ('Pending', 'Confirmed')
            AND (%s IS NULL OR Booking_ID <> %s)
        LIMIT 1
    """, (show_id, seat_id, exclude_booking_id, exclude_booking_id))
    if cursor.fetchone() is not None:
        raise BookingRuleError("This seat is already reserved for this show. Please select another seat.")


def check_booking_payment(cursor, payment_id, require_paid):
    cursor.execute("SELECT Payment_Status FROM Payment WHERE Payment_ID = %s FOR UPDATE", (payment_id,))
    payment = cursor.fetchone()
    if payment is None:
        raise BookingRuleError("Select an existing payment record.")
    if require_paid and payment['Payment_Status'] != 'Paid':
        raise BookingRuleError("Booking cannot be confirmed until its linked payment is Paid.")


def add_booking(booking):
    """Reserve first, then optionally confirm so all three existing triggers run."""
    with get_connection() as connection:
        try:
            connection.start_transaction(isolation_level='READ COMMITTED')
            with connection.cursor(dictionary=True) as cursor:
                if booking['Booking_Status'] not in ('Pending', 'Confirmed'):
                    raise BookingRuleError("New bookings must be Pending or Confirmed.")
                lock_booking_seat(cursor, booking['Show_ID'], booking['Seat_ID'])
                check_booking_availability(cursor, booking['Show_ID'], booking['Seat_ID'])
                check_booking_payment(cursor, booking['Payment_ID'], booking['Booking_Status'] == 'Confirmed')
                cursor.execute("SELECT Customer_ID FROM Customer WHERE Customer_ID = %s", (booking['Customer_ID'],))
                if cursor.fetchone() is None:
                    raise BookingRuleError("Select an existing customer.")
                # BEFORE INSERT invokes prevent_double_booking.
                cursor.execute("""
                    INSERT INTO Booking (Booking_ID, Customer_ID, Show_ID, Seat_ID,
                        Payment_ID, Booking_Date, Booking_Time, Total_Amount, Booking_Status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Pending')
                """, (booking['Booking_ID'], booking['Customer_ID'], booking['Show_ID'],
                      booking['Seat_ID'], booking['Payment_ID'], booking['Booking_Date'],
                      booking['Booking_Time'], booking['Total_Amount']))
                if booking['Booking_Status'] == 'Confirmed':
                    # Invokes check_payment and update_seat_status before commit.
                    cursor.execute("UPDATE Booking SET Booking_Status = 'Confirmed' WHERE Booking_ID = %s",
                                   (booking['Booking_ID'],))
            connection.commit()
        except (Error, BookingRuleError):
            connection.rollback()
            raise


def update_booking_status(booking_id, new_status):
    """Pending -> Confirmed/Cancelled; Confirmed -> Cancelled. Keep history."""
    with get_connection() as connection:
        try:
            connection.start_transaction(isolation_level='READ COMMITTED')
            with connection.cursor(dictionary=True) as cursor:
                if new_status not in ('Confirmed', 'Cancelled'):
                    raise BookingRuleError("Choose Confirmed or Cancelled.")
                cursor.execute("SELECT Show_ID, Seat_ID FROM Booking WHERE Booking_ID = %s", (booking_id,))
                original = cursor.fetchone()
                if original is None:
                    connection.rollback()
                    return False
                lock_booking_seat(cursor, original['Show_ID'], original['Seat_ID'])
                cursor.execute("SELECT * FROM Booking WHERE Booking_ID = %s FOR UPDATE", (booking_id,))
                booking = cursor.fetchone()
                if booking is None:
                    connection.rollback()
                    return False
                if (booking['Show_ID'], booking['Seat_ID']) != (original['Show_ID'], original['Seat_ID']):
                    raise BookingRuleError("This booking changed while you were editing it. Reload and try again.")
                allowed = {'Pending': ('Confirmed', 'Cancelled'), 'Confirmed': ('Cancelled',)}
                if new_status not in allowed.get(booking['Booking_Status'], ()):
                    raise BookingRuleError("This status change is not allowed. Cancelled bookings cannot be reopened.")
                if new_status == 'Confirmed':
                    check_booking_availability(cursor, booking['Show_ID'], booking['Seat_ID'], booking_id)
                    check_booking_payment(cursor, booking['Payment_ID'], True)
                # Existing BEFORE/AFTER UPDATE triggers remain in control.
                cursor.execute("UPDATE Booking SET Booking_Status = %s WHERE Booking_ID = %s",
                               (new_status, booking_id))
            connection.commit()
            return True
        except (Error, BookingRuleError):
            connection.rollback()
            raise
