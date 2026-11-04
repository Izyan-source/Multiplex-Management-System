"""A small Flask dashboard for the existing Multiplex Management System."""

import click
from flask import Flask, render_template
from mysql.connector import Error

from db import database_error_message, get_dashboard_counts


app = Flask(__name__)


@app.route("/")
def dashboard():
    try:
        counts = get_dashboard_counts()
    except (Error, ValueError) as error:
        return render_template(
            "dashboard.html", counts=None, error=database_error_message(error)
        ), 503
    return render_template("dashboard.html", counts=counts, error=None)


@app.cli.command("check-db")
def check_db():
    """Check the connection and read dashboard totals without changing data."""
    try:
        counts = get_dashboard_counts()
    except (Error, ValueError) as error:
        raise click.ClickException(database_error_message(error)) from None

    click.echo(f"Connected to {counts['database_name']}. Dashboard queries succeeded.")
    for key in ("movies", "customers", "bookings", "multiplexes"):
        click.echo(f"Total {key}: {counts[key]}")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
