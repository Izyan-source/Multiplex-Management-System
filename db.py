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
