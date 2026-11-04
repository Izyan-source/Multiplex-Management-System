"""Run with: python -m unittest discover -s tests -v

These tests mock database calls; they never connect to or modify MySQL.
"""

import unittest
from decimal import Decimal
from unittest.mock import patch

from mysql.connector import Error

import app as application


class MovieTests(unittest.TestCase):
    def setUp(self):
        self.client = application.app.test_client()
        self.movie = {
            "Movie_ID": "TEST123", "Movie_Name": "A Movie", "Genre": "Drama",
            "Language": "English", "Duration_Min": 120, "Rating": Decimal("8.4"),
        }
        with self.client.session_transaction() as session:
            session["csrf_token"] = "test-form-token"
        self.form = {key: str(value) for key, value in self.movie.items()}
        self.form["csrf_token"] = "test-form-token"

    def test_list_search_and_html_escaping(self):
        record = dict(self.movie, Movie_Name="<script>alert(1)</script>")
        with patch('app.get_movies', return_value=[record]) as query:
            response = self.client.get('/movies', query_string={'q': "O'Brien"})
        self.assertEqual(response.status_code, 200)
        query.assert_called_once_with("O'Brien")
        self.assertIn(b'&lt;script&gt;', response.data)
        self.assertNotIn(b'<script>alert', response.data)
        for heading in (b'Movie ID', b'Movie Name', b'Genre', b'Language', b'Duration', b'Rating'):
            self.assertIn(heading, response.data)

    def test_empty_list_and_database_failure_are_distinct(self):
        with patch('app.get_movies', return_value=[]):
            response = self.client.get('/movies?q=missing')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No movies match', response.data)
        with patch('app.get_movies', side_effect=Error(errno=1045)):
            response = self.client.get('/movies')
        self.assertEqual(response.status_code, 503)
        self.assertIn(b'MySQL rejected', response.data)
        self.assertNotIn(b'No movies yet', response.data)

    def test_add_form_and_success(self):
        self.assertEqual(self.client.get('/movies/add').status_code, 200)
        with patch('app.add_movie') as insert:
            response = self.client.post('/movies/add', data=self.form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/movies')
        self.assertEqual(insert.call_args.args[0]['Duration_Min'], 120)
        self.assertEqual(insert.call_args.args[0]['Rating'], Decimal('8.4'))

    def test_invalid_inputs_do_not_write(self):
        invalid_values = {
            'Movie_ID': ['', 'ID TOO LONG', '../x'],
            'Movie_Name': ['   ', 'x' * 101],
            'Genre': ['', 'x' * 51],
            'Language': ['', 'x' * 31],
            'Duration_Min': ['0', '-1', '1.5', '2147483648', 'x' * 100],
            'Rating': ['', '-1', '10', '8.45', 'NaN', 'Infinity', '1e-9999999'],
        }
        with patch('app.add_movie') as insert:
            for key, values in invalid_values.items():
                for value in values:
                    with self.subTest(field=key, value=value):
                        form = dict(self.form, **{key: value})
                        self.assertEqual(self.client.post('/movies/add', data=form).status_code, 400)
            insert.assert_not_called()

    def test_duplicate_id_preserves_form(self):
        with patch('app.add_movie', side_effect=Error(errno=1062)):
            response = self.client.post('/movies/add', data=self.form)
        self.assertEqual(response.status_code, 409)
        self.assertIn(b'already exists', response.data)
        self.assertIn(b'value="A Movie"', response.data)

    def test_edit_keeps_original_id_and_allows_unchanged_values(self):
        with patch('app.get_movie', return_value=self.movie), patch('app.update_movie', return_value=True) as update:
            response = self.client.get('/movies/TEST123/edit')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'readonly', response.data)
            response = self.client.post('/movies/TEST123/edit', data=dict(self.form, Movie_ID='TAMPERED'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(update.call_args.args[0], 'TEST123')
        self.assertEqual(update.call_args.args[1]['Movie_ID'], 'TEST123')

    def test_delete_requires_confirmation_and_handles_foreign_key(self):
        with patch('app.get_movie', return_value=self.movie), patch('app.delete_movie') as delete:
            self.assertEqual(self.client.get('/movies/TEST123/delete').status_code, 200)
            delete.assert_not_called()
            delete.side_effect = Error(errno=1451)
            response = self.client.post('/movies/TEST123/delete', data=self.form)
        self.assertEqual(response.status_code, 409)
        self.assertIn(b'existing show references it', response.data)

    def test_delete_success(self):
        with patch('app.get_movie', return_value=self.movie), patch('app.delete_movie', return_value=True):
            response = self.client.post('/movies/TEST123/delete', data=self.form)
        self.assertEqual(response.status_code, 302)

    def test_missing_movies_return_404(self):
        with patch('app.get_movie', return_value=None):
            for action in ('edit', 'delete'):
                self.assertEqual(self.client.get(f'/movies/missing/{action}').status_code, 404)

    def test_post_requires_form_token(self):
        with patch('app.add_movie') as insert:
            self.assertEqual(self.client.post('/movies/add', data={}).status_code, 400)
            insert.assert_not_called()

    def test_zero_rating_is_valid(self):
        with patch('app.add_movie') as insert:
            response = self.client.post('/movies/add', data=dict(self.form, Rating='0'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(insert.call_args.args[0]['Rating'], Decimal('0'))

    def test_dashboard_still_renders_counts(self):
        with patch('app.get_dashboard_counts', return_value={'movies': 8, 'customers': 15, 'bookings': 15, 'multiplexes': 5}):
            response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Total movies', response.data)
        self.assertIn(b'href="/movies"', response.data)


if __name__ == '__main__':
    unittest.main()
