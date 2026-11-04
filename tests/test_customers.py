"""Customer route tests; database functions are mocked, so no MySQL data changes."""

import unittest
from unittest.mock import patch

from mysql.connector import Error

import app as application


class CustomerTests(unittest.TestCase):
    def setUp(self):
        self.client = application.app.test_client()
        self.customer = {
            'Customer_ID': 'TEST123', 'Customer_Name': "Test O'Brien",
            'Phone': '0123456789', 'Email': 'test+customer@example.com', 'Gender': 'Other',
        }
        with self.client.session_transaction() as session:
            session['csrf_token'] = 'test-form-token'
        self.form = dict(self.customer, csrf_token='test-form-token')

    def test_list_search_and_escaping(self):
        customer = dict(self.customer, Customer_Name='<script>alert(1)</script>')
        with patch('app.get_customers', return_value=[customer]) as query:
            response = self.client.get('/customers', query_string={'q': " O'Brien "})
        self.assertEqual(response.status_code, 200)
        query.assert_called_once_with("O'Brien")
        for heading in (b'Customer ID', b'Customer Name', b'Phone', b'Email', b'Gender'):
            self.assertIn(heading, response.data)
        self.assertIn(b'&lt;script&gt;', response.data)
        self.assertNotIn(b'<script>alert', response.data)

    def test_no_matches_and_unavailable_database(self):
        with patch('app.get_customers', return_value=[]):
            response = self.client.get('/customers?q=missing')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No customers match', response.data)
        with patch('app.get_customers', side_effect=Error(msg='private details', errno=1045)):
            response = self.client.get('/customers')
        self.assertEqual(response.status_code, 503)
        self.assertIn(b'MySQL rejected', response.data)
        self.assertNotIn(b'private details', response.data)
        self.assertNotIn(b'No customers yet', response.data)

    def test_add_form_and_registration(self):
        self.assertEqual(self.client.get('/customers/add').status_code, 200)
        with patch('app.add_customer') as insert:
            response = self.client.post('/customers/add', data=self.form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/customers')
        self.assertEqual(insert.call_args.args[0], self.customer)

    def test_invalid_inputs_never_write(self):
        invalid = {
            'Customer_ID': ['', 'A' * 11, '../x', 'with space'],
            'Customer_Name': ['', ' ', 'A' * 101, '123', 'Test\x00Name'],
            'Phone': ['', '123456', '1' * 16, '+123456789012345', '123-456789', '1234abc890', '1e12345678'],
            'Email': ['', 'missing-at', 'a@@example.com', 'a@localhost', 'a b@example.com',
                      '.a@example.com', 'a..b@example.com', 'a@-example.com', 'a@example..com',
                      'a' * 65 + '@example.com', 'a@' + 'b' * 64 + '.com', 'a@' + 'b.' * 48 + 'com'],
            'Gender': ['', 'Unsupported', '<script>'],
        }
        with patch('app.add_customer') as insert:
            for field, values in invalid.items():
                for value in values:
                    with self.subTest(field=field, value=value):
                        response = self.client.post('/customers/add', data=dict(self.form, **{field: value}))
                        self.assertEqual(response.status_code, 400)
            insert.assert_not_called()

    def test_valid_names_phone_and_email_variations(self):
        cases = [
            {'Customer_Name': 'अनन्या जोशी', 'Phone': '+919876543210', 'Gender': 'Not stated'},
            {'Customer_Name': 'Anne-Marie O’Brien', 'Email': 'anne.marie+tag@sub.example.com'},
            {'Customer_ID': 'A' * 10, 'Customer_Name': 'A' * 100, 'Phone': '1' * 15},
        ]
        with patch('app.add_customer') as insert:
            for values in cases:
                self.assertEqual(self.client.post('/customers/add', data=dict(self.form, **values)).status_code, 302)
            self.assertEqual(insert.call_count, len(cases))

    def test_duplicate_id_keeps_entered_values(self):
        with patch('app.add_customer', side_effect=Error(errno=1062)):
            response = self.client.post('/customers/add', data=self.form)
        self.assertEqual(response.status_code, 409)
        self.assertIn(b'already exists', response.data)
        self.assertIn(b'value="0123456789"', response.data)

    def test_edit_keeps_original_id(self):
        with patch('app.get_customer', return_value=self.customer), patch('app.update_customer', return_value=True) as update:
            self.assertEqual(self.client.get('/customers/TEST123/edit').status_code, 200)
            response = self.client.post('/customers/TEST123/edit', data=dict(self.form, Customer_ID='OTHER'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(update.call_args.args[0], 'TEST123')
        self.assertEqual(update.call_args.args[1]['Customer_ID'], 'TEST123')

    def test_invalid_edit_keeps_values_and_does_not_write(self):
        with patch('app.get_customer', return_value=self.customer), patch('app.update_customer') as update:
            response = self.client.post('/customers/TEST123/edit', data=dict(self.form, Email='bad'))
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'value="bad"', response.data)
        update.assert_not_called()

    def test_delete_get_is_safe_and_post_deletes(self):
        with patch('app.get_customer', return_value=self.customer), patch('app.delete_customer', return_value=True) as delete:
            self.assertEqual(self.client.get('/customers/TEST123/delete').status_code, 200)
            delete.assert_not_called()
            response = self.client.post('/customers/TEST123/delete', data=self.form)
        self.assertEqual(response.status_code, 302)
        delete.assert_called_once_with('TEST123')

    def test_booking_blocks_deletion(self):
        with patch('app.get_customer', return_value=self.customer), patch('app.delete_customer', side_effect=Error(errno=1451)):
            response = self.client.post('/customers/TEST123/delete', data=self.form)
        self.assertEqual(response.status_code, 409)
        self.assertIn(b'existing bookings', response.data)

    def test_missing_customers_return_404(self):
        with patch('app.get_customer', return_value=None):
            for action in ('edit', 'delete'):
                self.assertEqual(self.client.get(f'/customers/missing/{action}').status_code, 404)

    def test_expired_forms_do_not_reach_database(self):
        with patch('app.add_customer') as insert, patch('app.get_customer') as select:
            for path in ('/customers/add', '/customers/TEST123/edit', '/customers/TEST123/delete'):
                self.assertEqual(self.client.post(path, data={}).status_code, 400)
            insert.assert_not_called()
            select.assert_not_called()

    def test_database_write_failures_have_safe_messages(self):
        with patch('app.add_customer', side_effect=Error(msg='private details', errno=9999)):
            response = self.client.post('/customers/add', data=self.form)
        self.assertEqual(response.status_code, 503)
        self.assertIn(b'could not be completed', response.data)
        self.assertNotIn(b'private details', response.data)

    def test_missing_customer_during_edit_or_delete(self):
        with patch('app.get_customer', return_value=self.customer):
            with patch('app.update_customer', return_value=False):
                self.assertEqual(self.client.post('/customers/TEST123/edit', data=self.form).status_code, 404)
            with patch('app.delete_customer', return_value=False):
                self.assertEqual(self.client.post('/customers/TEST123/delete', data=self.form).status_code, 404)


if __name__ == '__main__':
    unittest.main()
