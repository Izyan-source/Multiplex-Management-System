"""Shows tests use mocked database calls and never change MySQL records."""

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from mysql.connector import Error

import app as application


class ShowTests(unittest.TestCase):
    def setUp(self):
        self.client = application.app.test_client()
        self.movies = [{'Movie_ID': 'MOV1', 'Movie_Name': 'A Movie'}]
        self.screens = [{'Screen_ID': 'SCR1', 'Screen_Name': 'Screen 1', 'Multiplex_Name': 'A Cinema'}]
        self.show = {
            'Show_ID': 'TEST123', 'Movie_ID': 'MOV1', 'Screen_ID': 'SCR1',
            'Movie_Name': 'A Movie', 'Screen_Name': 'Screen 1',
            'Show_Date': date(2026, 8, 15), 'Show_Time': '00:05:07',
            'Ticket_Price': Decimal('250.50'),
        }
        self.form = {key: str(self.show[key]) for key in (
            'Show_ID', 'Movie_ID', 'Screen_ID', 'Show_Date', 'Show_Time', 'Ticket_Price'
        )}
        with self.client.session_transaction() as session:
            session['csrf_token'] = 'test-token'
        self.form['csrf_token'] = 'test-token'
        for name, result in [('app.get_movies', self.movies), ('app.get_screens', self.screens)]:
            mock = patch(name, return_value=result)
            mock.start()
            self.addCleanup(mock.stop)

    def test_list_shows_joined_names_and_formats(self):
        with patch('app.get_shows', return_value=[self.show]):
            response = self.client.get('/shows')
        self.assertEqual(response.status_code, 200)
        for text in (b'Show ID', b'Movie Name', b'Screen Name', b'Show Date', b'Show Time',
                     b'Ticket Price', b'A Movie', b'Screen 1', b'2026-08-15', b'00:05:07', b'250.50'):
            self.assertIn(text, response.data)

    def test_search_and_empty_results(self):
        with patch('app.get_shows', return_value=[]) as query:
            response = self.client.get('/shows', query_string={'q': " O'Brien "})
        query.assert_called_once_with("O'Brien")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No shows match', response.data)

    def test_null_legacy_fields_and_escaping(self):
        show = dict(self.show, Movie_Name='<script>alert(1)</script>', Screen_Name=None,
                    Show_Date=None, Show_Time=None, Ticket_Price=None)
        with patch('app.get_shows', return_value=[show]):
            response = self.client.get('/shows')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'&lt;script&gt;', response.data)
        self.assertNotIn(b'<script>alert', response.data)

    def test_form_choices_come_from_database(self):
        response = self.client.get('/shows/add')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'value="MOV1"', response.data)
        self.assertIn(b'value="SCR1"', response.data)
        self.assertIn(b'A Cinema', response.data)

    def test_add_show(self):
        with patch('app.add_show') as insert:
            response = self.client.post('/shows/add', data=dict(self.form, Show_Time='09:30'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/shows')
        values = insert.call_args.args[0]
        self.assertEqual(values['Show_Time'], '09:30:00')
        self.assertEqual(values['Ticket_Price'], Decimal('250.50'))

    def test_duplicate_id_preserves_form(self):
        with patch('app.add_show', side_effect=Error(errno=1062)):
            response = self.client.post('/shows/add', data=self.form)
        self.assertEqual(response.status_code, 409)
        self.assertIn(b'already exists', response.data)
        self.assertIn(b'value="250.50"', response.data)
        self.assertIn(b'value="MOV1" selected', response.data)

    def test_invalid_inputs_never_write(self):
        invalid = {
            'Show_ID': ['', 'A' * 11, '../x', 'with space'],
            'Movie_ID': ['', 'missing', "' OR 1=1 --"],
            'Screen_ID': ['', 'missing', "' OR 1=1 --"],
            'Show_Date': ['', '2026-02-29', '2026-04-31', '2026-13-01', '0999-01-01', '2026-8-1', '2026-01-01T12:00'],
            'Show_Time': ['', '24:00', '12:60', '12:30:60', '-01:00', '1:05', '09:00+01:00'],
            'Ticket_Price': ['', '0', '0.00', '-1', '1000000', '1.001', 'NaN', 'Infinity', '1e2', 'abc'],
        }
        with patch('app.add_show') as insert:
            for field, values in invalid.items():
                for value in values:
                    with self.subTest(field=field, value=value):
                        response = self.client.post('/shows/add', data=dict(self.form, **{field: value}))
                        self.assertEqual(response.status_code, 400)
            insert.assert_not_called()

    def test_valid_leap_date_midnight_and_price_boundaries(self):
        with patch('app.add_show') as insert:
            for price in ('0.01', '999999.99'):
                response = self.client.post('/shows/add', data=dict(self.form,
                    Show_Date='2028-02-29', Show_Time='00:00', Ticket_Price=price))
                self.assertEqual(response.status_code, 302)
            self.assertEqual(insert.call_count, 2)

    def test_reference_removed_after_validation(self):
        with patch('app.add_show', side_effect=Error(errno=1452)):
            response = self.client.post('/shows/add', data=self.form)
        self.assertEqual(response.status_code, 409)
        self.assertIn(b'no longer exists', response.data)

    def test_edit_preserves_id_and_seconds(self):
        with patch('app.get_show', return_value=self.show), patch('app.update_show', return_value=True) as update:
            response = self.client.get('/shows/TEST123/edit')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'value="00:05:07"', response.data)
            self.assertIn(b'readonly', response.data)
            response = self.client.post('/shows/TEST123/edit', data=dict(self.form, Show_ID='OTHER'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(update.call_args.args[0], 'TEST123')
        self.assertEqual(update.call_args.args[1]['Show_ID'], 'TEST123')

    def test_invalid_edit_does_not_write(self):
        with patch('app.get_show', return_value=self.show), patch('app.update_show') as update:
            response = self.client.post('/shows/TEST123/edit', data=dict(self.form, Screen_ID='missing'))
        self.assertEqual(response.status_code, 400)
        update.assert_not_called()

    def test_safe_delete_confirmation_and_success(self):
        with patch('app.get_show', return_value=self.show), patch('app.delete_show', return_value=True) as delete:
            self.assertEqual(self.client.get('/shows/TEST123/delete').status_code, 200)
            delete.assert_not_called()
            response = self.client.post('/shows/TEST123/delete', data=self.form)
        self.assertEqual(response.status_code, 302)
        delete.assert_called_once_with('TEST123')

    def test_existing_booking_blocks_delete(self):
        with patch('app.get_show', return_value=self.show), patch('app.delete_show', side_effect=Error(errno=1451)):
            response = self.client.post('/shows/TEST123/delete', data=self.form)
        self.assertEqual(response.status_code, 409)
        self.assertIn(b'existing bookings', response.data)

    def test_missing_show_returns_404(self):
        with patch('app.get_show', return_value=None):
            for action in ('edit', 'delete'):
                self.assertEqual(self.client.get(f'/shows/missing/{action}').status_code, 404)

    def test_expired_forms_do_not_reach_database(self):
        with patch('app.add_show') as insert, patch('app.get_show') as select:
            for path in ('/shows/add', '/shows/TEST123/edit', '/shows/TEST123/delete'):
                self.assertEqual(self.client.post(path, data={}).status_code, 400)
            insert.assert_not_called()
            select.assert_not_called()

    def test_database_errors_do_not_expose_details(self):
        with patch('app.get_shows', side_effect=Error(msg='private details', errno=1045)):
            response = self.client.get('/shows')
        self.assertEqual(response.status_code, 503)
        self.assertIn(b'MySQL rejected', response.data)
        self.assertNotIn(b'private details', response.data)
        with patch('app.add_show', side_effect=Error(msg='private details', errno=9999)):
            response = self.client.post('/shows/add', data=self.form)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b'private details', response.data)

    def test_empty_dropdown_options(self):
        with patch('app.get_screens', return_value=[]), patch('app.add_show') as insert:
            response = self.client.get('/shows/add')
            self.assertIn(b'at least one existing movie and one existing screen', response.data)
            self.assertIn(b'type="submit" disabled', response.data)
            self.assertEqual(self.client.post('/shows/add', data=self.form).status_code, 400)
            insert.assert_not_called()

    def test_concurrent_removal_returns_404(self):
        with patch('app.get_show', return_value=self.show):
            with patch('app.update_show', return_value=False):
                self.assertEqual(self.client.post('/shows/TEST123/edit', data=self.form).status_code, 404)
            with patch('app.delete_show', return_value=False):
                self.assertEqual(self.client.post('/shows/TEST123/delete', data=self.form).status_code, 404)


if __name__ == '__main__':
    unittest.main()
