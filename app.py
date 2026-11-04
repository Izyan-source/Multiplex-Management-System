"""A small Flask dashboard for the existing Multiplex Management System."""

import os
import re
import secrets
from decimal import Decimal
from datetime import date, time

import click
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from mysql.connector import Error

from db import (
    add_movie, database_error_message, delete_movie, get_dashboard_counts,
    get_movie, get_movies, update_movie,
    add_customer, delete_customer, get_customer, get_customers, update_customer,
    add_show, delete_show, get_show, get_shows, get_screens, update_show,
)


app = Flask(__name__)
# A local development fallback; SECRET_KEY can be set in .env for stable sessions.
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)


def csrf_token():
    """A small form token prevents another website from submitting our forms."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def protect_movie_forms():
    if request.method == "POST" and request.endpoint in {
        "movie_add", "movie_edit", "movie_delete",
        "customer_add", "customer_edit", "customer_delete",
        "show_add", "show_edit", "show_delete",
    }:
        expected = session.get("csrf_token", "")
        submitted = request.form.get("csrf_token", "")
        if not expected or not secrets.compare_digest(expected.encode(), submitted.encode()):
            abort(400, description="This form has expired. Reload the form and try again.")


def validate_movie(form, movie_id=None):
    """Validate against the existing Movie column sizes and numeric types."""
    movie = {key: form.get(key, "").strip() for key in (
        "Movie_ID", "Movie_Name", "Genre", "Language", "Duration_Min", "Rating"
    )}
    errors = []
    if movie_id is not None:
        movie["Movie_ID"] = movie_id  # Primary keys cannot be changed by editing.
    elif not re.fullmatch(r"[A-Za-z0-9_-]{1,10}", movie["Movie_ID"]):
        errors.append("Movie ID must contain 1–10 letters, numbers, hyphens, or underscores.")
    for key, label, maximum in (
        ("Movie_Name", "Movie name", 100), ("Genre", "Genre", 50), ("Language", "Language", 30)
    ):
        if not movie[key] or len(movie[key]) > maximum:
            errors.append(f"{label} is required and must be at most {maximum} characters.")
    duration = movie["Duration_Min"]
    if not re.fullmatch(r"[0-9]{1,10}", duration) or not 1 <= int(duration) <= 2147483647:
        errors.append("Duration must be a positive whole number of minutes (maximum 2147483647).")
    else:
        movie["Duration_Min"] = int(duration)
    # DECIMAL(2,1) permits one digit before and one after the decimal point.
    if not re.fullmatch(r"[0-9](?:\.[0-9])?", movie["Rating"]):
        errors.append("Rating must be between 0 and 9.9, with at most one decimal place.")
    else:
        movie["Rating"] = Decimal(movie["Rating"])
    return movie, errors


def movie_error_message(error):
    if isinstance(error, ValueError):
        return database_error_message(error)
    if error.errno == 1062:
        return "That Movie ID already exists. Please choose a different ID."
    if error.errno == 1451:
        return "This movie cannot be deleted because an existing show references it. No records were changed."
    if error.errno in (1045, 1698, 1049, 1044, 1142, 2002, 2003, 2005):
        return database_error_message(error)
    return "The movie operation could not be completed. Check the database connection and Movie table, then try again."


@app.route("/movies")
def movies():
    search = request.args.get("q", "").strip()
    try:
        records = get_movies(search)
    except (Error, ValueError) as error:
        return render_template("movies/list.html", movies=None, search=search,
                               error=movie_error_message(error)), 503
    return render_template("movies/list.html", movies=records, search=search, error=None)


@app.route("/movies/add", methods=["GET", "POST"])
def movie_add():
    movie, errors = {}, []
    status = 200
    if request.method == "POST":
        movie, errors = validate_movie(request.form)
        status = 400
        if not errors:
            try:
                add_movie(movie)
            except (Error, ValueError) as error:
                errors = [movie_error_message(error)]
                status = 409 if getattr(error, "errno", None) == 1062 else 503
            else:
                flash("Movie added successfully.", "success")
                return redirect(url_for("movies"))
    return render_template("movies/form.html", movie=movie, editing=False, errors=errors), status


@app.route("/movies/<movie_id>/edit", methods=["GET", "POST"])
def movie_edit(movie_id):
    try:
        movie = get_movie(movie_id)
    except (Error, ValueError) as error:
        return render_template("movies/list.html", movies=None, search="",
                               error=movie_error_message(error)), 503
    if movie is None:
        abort(404, description="Movie not found.")
    errors, status = [], 200
    if request.method == "POST":
        movie, errors = validate_movie(request.form, movie_id)
        status = 400
        if not errors:
            try:
                exists = update_movie(movie_id, movie)
            except (Error, ValueError) as error:
                errors, status = [movie_error_message(error)], 503
            else:
                if not exists:
                    abort(404, description="Movie not found.")
                flash("Movie updated successfully.", "success")
                return redirect(url_for("movies"))
    return render_template("movies/form.html", movie=movie, editing=True, errors=errors), status


@app.route("/movies/<movie_id>/delete", methods=["GET", "POST"])
def movie_delete(movie_id):
    try:
        movie = get_movie(movie_id)
    except (Error, ValueError) as error:
        return render_template("movies/list.html", movies=None, search="",
                               error=movie_error_message(error)), 503
    if movie is None:
        abort(404, description="Movie not found.")
    error_message, status = None, 200
    if request.method == "POST":
        try:
            deleted = delete_movie(movie_id)
        except (Error, ValueError) as error:
            error_message = movie_error_message(error)
            status = 409 if getattr(error, "errno", None) == 1451 else 503
        else:
            if not deleted:
                abort(404, description="Movie not found.")
            flash("Movie deleted successfully.", "success")
            return redirect(url_for("movies"))
    return render_template("movies/delete.html", movie=movie, error=error_message), status


CUSTOMER_GENDERS = ("Male", "Female", "Other", "Not stated")


def valid_customer_email(email):
    """Check common email syntax without contacting an email service."""
    if len(email) > 100 or email.count("@") != 1:
        return False
    local, domain = email.split("@")
    if not local or len(local) > 64 or local.startswith(".") or local.endswith(".") or ".." in local:
        return False
    if not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+", local):
        return False
    labels = domain.split(".")
    return len(labels) >= 2 and all(
        len(label) <= 63 and re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", label)
        for label in labels
    )


def validate_customer(form, customer_id=None):
    """Keep input within the existing Customer table's column limits."""
    customer = {key: form.get(key, "").strip() for key in (
        "Customer_ID", "Customer_Name", "Phone", "Email", "Gender"
    )}
    errors = []
    if customer_id is not None:
        customer["Customer_ID"] = customer_id
    elif not re.fullmatch(r"[A-Za-z0-9_-]{1,10}", customer["Customer_ID"]):
        errors.append("Customer ID must contain 1–10 letters, numbers, hyphens, or underscores.")
    name = customer["Customer_Name"]
    if (not name or len(name) > 100 or not any(char.isalpha() for char in name)
            or any(ord(char) < 32 or ord(char) == 127 for char in name)):
        errors.append("Name is required, must contain a letter, and must be at most 100 characters without control characters.")
    phone = customer["Phone"]
    if len(phone) > 15 or not re.fullmatch(r"\+?[0-9]{7,15}", phone):
        errors.append("Phone must contain 7–15 digits, optionally starting with +, and be at most 15 characters in total. Do not include spaces or dashes.")
    if not valid_customer_email(customer["Email"]):
        errors.append("Enter a valid email address, such as name@example.com, with at most 100 characters.")
    if customer["Gender"] not in CUSTOMER_GENDERS:
        errors.append("Choose Male, Female, Other, or Not stated for gender.")
    return customer, errors


def customer_error_message(error):
    if isinstance(error, ValueError):
        return database_error_message(error)
    if error.errno == 1062:
        return "That Customer ID already exists. Please choose a different ID."
    if error.errno == 1451:
        return "This customer cannot be deleted because they have existing bookings. No records were changed."
    if error.errno in (1045, 1698, 1049, 1044, 1142, 2002, 2003, 2005):
        return database_error_message(error)
    return "The customer operation could not be completed. Check the database connection and Customer table, then try again."


@app.route("/customers")
def customers():
    search = request.args.get("q", "").strip()
    try:
        records = get_customers(search)
    except (Error, ValueError) as error:
        return render_template("customers/list.html", customers=None, search=search,
                               error=customer_error_message(error)), 503
    return render_template("customers/list.html", customers=records, search=search, error=None)


@app.route("/customers/add", methods=["GET", "POST"])
def customer_add():
    customer, errors = {}, []
    status = 200
    if request.method == "POST":
        customer, errors = validate_customer(request.form)
        status = 400
        if not errors:
            try:
                add_customer(customer)
            except (Error, ValueError) as error:
                errors = [customer_error_message(error)]
                status = 409 if getattr(error, "errno", None) == 1062 else 503
            else:
                flash("Customer registered successfully.", "success")
                return redirect(url_for("customers"))
    return render_template("customers/form.html", customer=customer, editing=False,
                           errors=errors, genders=CUSTOMER_GENDERS), status


@app.route("/customers/<customer_id>/edit", methods=["GET", "POST"])
def customer_edit(customer_id):
    try:
        customer = get_customer(customer_id)
    except (Error, ValueError) as error:
        return render_template("customers/list.html", customers=None, search="",
                               error=customer_error_message(error)), 503
    if customer is None:
        abort(404, description="Customer not found.")
    errors, status = [], 200
    if request.method == "POST":
        customer, errors = validate_customer(request.form, customer_id)
        status = 400
        if not errors:
            try:
                exists = update_customer(customer_id, customer)
            except (Error, ValueError) as error:
                errors, status = [customer_error_message(error)], 503
            else:
                if not exists:
                    abort(404, description="Customer not found.")
                flash("Customer updated successfully.", "success")
                return redirect(url_for("customers"))
    return render_template("customers/form.html", customer=customer, editing=True,
                           errors=errors, genders=CUSTOMER_GENDERS), status


@app.route("/customers/<customer_id>/delete", methods=["GET", "POST"])
def customer_delete(customer_id):
    try:
        customer = get_customer(customer_id)
    except (Error, ValueError) as error:
        return render_template("customers/list.html", customers=None, search="",
                               error=customer_error_message(error)), 503
    if customer is None:
        abort(404, description="Customer not found.")
    error_message, status = None, 200
    if request.method == "POST":
        try:
            deleted = delete_customer(customer_id)
        except (Error, ValueError) as error:
            error_message = customer_error_message(error)
            status = 409 if getattr(error, "errno", None) == 1451 else 503
        else:
            if not deleted:
                abort(404, description="Customer not found.")
            flash("Customer deleted successfully.", "success")
            return redirect(url_for("customers"))
    return render_template("customers/delete.html", customer=customer, error=error_message), status


def validate_show(form, movies, screens, show_id=None):
    """Validate form values and references using the current database choices."""
    show = {key: form.get(key, "").strip() for key in (
        "Show_ID", "Movie_ID", "Screen_ID", "Show_Date", "Show_Time", "Ticket_Price"
    )}
    errors = []
    if show_id is not None:
        show["Show_ID"] = show_id
    elif not re.fullmatch(r"[A-Za-z0-9_-]{1,10}", show["Show_ID"]):
        errors.append("Show ID must contain 1–10 letters, numbers, hyphens, or underscores.")
    if show["Movie_ID"] not in {movie["Movie_ID"] for movie in movies}:
        errors.append("Select a movie that exists in the database.")
    if show["Screen_ID"] not in {screen["Screen_ID"] for screen in screens}:
        errors.append("Select a screen that exists in the database.")
    try:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", show["Show_Date"]):
            raise ValueError
        parsed_date = date.fromisoformat(show["Show_Date"])
        if parsed_date.year < 1000:
            raise ValueError
    except ValueError:
        errors.append("Enter a valid show date between 1000-01-01 and 9999-12-31.")
    try:
        if not re.fullmatch(r"[0-9]{2}:[0-9]{2}(?::[0-9]{2})?", show["Show_Time"]):
            raise ValueError
        show["Show_Time"] = time.fromisoformat(show["Show_Time"]).isoformat()
    except ValueError:
        errors.append("Enter a valid time from 00:00:00 to 23:59:59.")
    price = show["Ticket_Price"]
    # DECIMAL(8,2) allows up to six digits before the decimal point.
    if not re.fullmatch(r"[0-9]{1,6}(?:\.[0-9]{1,2})?", price) or Decimal(price) <= 0:
        errors.append("Ticket price must be between 0.01 and 999999.99, with at most two decimal places.")
    else:
        show["Ticket_Price"] = Decimal(price)
    return show, errors


def show_error_message(error):
    if isinstance(error, ValueError):
        return database_error_message(error)
    if error.errno == 1062:
        return "That Show ID already exists. Please choose a different ID."
    if error.errno == 1451:
        return "This show cannot be deleted because it has existing bookings. No records were changed."
    if error.errno == 1452:
        return "The selected movie or screen no longer exists. Reload the form and choose an existing record."
    if error.errno in (1045, 1698, 1049, 1044, 1142, 2002, 2003, 2005):
        return database_error_message(error)
    return "The show operation could not be completed. Check the database connection and Show table, then try again."


@app.route("/shows")
def shows():
    search = request.args.get("q", "").strip()
    try:
        records = get_shows(search)
    except (Error, ValueError) as error:
        return render_template("shows/list.html", shows=None, search=search,
                               error=show_error_message(error)), 503
    return render_template("shows/list.html", shows=records, search=search, error=None)


@app.route("/shows/add", methods=["GET", "POST"])
def show_add():
    try:
        movies, screens = get_movies(), get_screens()
    except (Error, ValueError) as error:
        return render_template("shows/list.html", shows=None, search="",
                               error=show_error_message(error)), 503
    show, errors, status = {}, [], 200
    if request.method == "POST":
        show, errors = validate_show(request.form, movies, screens)
        status = 400
        if not errors:
            try:
                add_show(show)
            except (Error, ValueError) as error:
                errors = [show_error_message(error)]
                status = 409 if getattr(error, "errno", None) in (1062, 1452) else 503
            else:
                flash("Show scheduled successfully.", "success")
                return redirect(url_for("shows"))
    return render_template("shows/form.html", show=show, editing=False, errors=errors,
                           movies=movies, screens=screens), status


@app.route("/shows/<show_id>/edit", methods=["GET", "POST"])
def show_edit(show_id):
    try:
        show = get_show(show_id)
        if show is None:
            abort(404, description="Show not found.")
        movies, screens = get_movies(), get_screens()
    except (Error, ValueError) as error:
        return render_template("shows/list.html", shows=None, search="",
                               error=show_error_message(error)), 503
    errors, status = [], 200
    if request.method == "POST":
        show, errors = validate_show(request.form, movies, screens, show_id)
        status = 400
        if not errors:
            try:
                exists = update_show(show_id, show)
            except (Error, ValueError) as error:
                errors = [show_error_message(error)]
                status = 409 if getattr(error, "errno", None) == 1452 else 503
            else:
                if not exists:
                    abort(404, description="Show not found.")
                flash("Show updated successfully.", "success")
                return redirect(url_for("shows"))
    return render_template("shows/form.html", show=show, editing=True, errors=errors,
                           movies=movies, screens=screens), status


@app.route("/shows/<show_id>/delete", methods=["GET", "POST"])
def show_delete(show_id):
    try:
        show = get_show(show_id)
    except (Error, ValueError) as error:
        return render_template("shows/list.html", shows=None, search="",
                               error=show_error_message(error)), 503
    if show is None:
        abort(404, description="Show not found.")
    error_message, status = None, 200
    if request.method == "POST":
        try:
            deleted = delete_show(show_id)
        except (Error, ValueError) as error:
            error_message = show_error_message(error)
            status = 409 if getattr(error, "errno", None) == 1451 else 503
        else:
            if not deleted:
                abort(404, description="Show not found.")
            flash("Show deleted successfully.", "success")
            return redirect(url_for("shows"))
    return render_template("shows/delete.html", show=show, error=error_message), status


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
