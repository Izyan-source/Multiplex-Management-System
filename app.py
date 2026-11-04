"""A small Flask dashboard for the existing Multiplex Management System."""

import os
import re
import secrets
from decimal import Decimal

import click
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from mysql.connector import Error

from db import (
    add_movie, database_error_message, delete_movie, get_dashboard_counts,
    get_movie, get_movies, update_movie,
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
    if request.method == "POST" and request.endpoint in {"movie_add", "movie_edit", "movie_delete"}:
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
