"""Payment page and transaction tests; MySQL access is mocked."""

import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from mysql.connector import Error

import app as application
import db


class PaymentTests(unittest.TestCase):
    def setUp(self):
        self.client = application.app.test_client()
        self.form = dict(Payment_ID='PAY1', Amount='250.50', Payment_Mode='UPI',
                         Payment_Date='2026-11-04', Payment_Status='Pending', csrf_token='test-token')
        self.payment = dict(self.form, Amount=Decimal('250.50'))
        self.joined = dict(self.payment, Booking_ID='B1', Customer_Name='Test Customer')
        self.booking = dict(Booking_ID='B1', Customer_Name='Test Customer', Movie_Name='Test Movie',
                            Show_Date='2026-11-05', Show_Time='10:00:00', Seat_Number='A1',
                            Booking_Date='2026-11-04', Booking_Time='09:00:00',
                            Total_Amount=Decimal('250.50'), Booking_Status='Pending')
        with self.client.session_transaction() as session:
            session['csrf_token'] = 'test-token'
        for name, result in [('get_payment', self.payment), ('get_payment_bookings', [self.booking])]:
            mock = patch('app.' + name, return_value=result)
            mock.start()
            self.addCleanup(mock.stop)

    def test_list_joined_and_unlinked_payments(self):
        with patch('app.get_payments', return_value=[self.joined, dict(self.joined, Booking_ID=None, Customer_Name=None)]):
            response = self.client.get('/payments')
        self.assertEqual(response.status_code, 200)
        for label in (b'Payment ID', b'Amount', b'Payment Mode', b'Payment Date', b'Payment Status',
                      b'Associated Booking ID', b'Customer Name', b'Test Customer', b'Unlinked', b'250.50'):
            self.assertIn(label, response.data)
        self.assertIn(b'href="/payments" aria-current="page"', response.data)

    def test_search_is_trimmed_and_forwarded(self):
        for query in ('PAY1', 'B1', 'Test Customer', "x' OR 1=1 --", '%_!'):
            with patch('app.get_payments', return_value=[]) as select:
                response = self.client.get('/payments', query_string={'q': ' ' + query + ' '})
                select.assert_called_once_with(query)
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'No payments match', response.data)

    def test_new_form_has_supported_modes_and_no_processing_claim(self):
        response = self.client.get('/payments/add')
        self.assertEqual(response.status_code, 200)
        for mode in application.PAYMENT_MODES:
            self.assertIn(mode.encode(), response.data)
        self.assertIn(b'does not collect, transfer or refund money', response.data)

    def test_add_paid_and_pending(self):
        with patch('app.add_payment') as insert:
            for status in ('Paid', 'Pending'):
                response = self.client.post('/payments/add', data=dict(self.form, Payment_Status=status))
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, '/payments/PAY1')
                self.assertEqual(insert.call_args.args[0]['Amount'], Decimal('250.50'))
                self.assertEqual(insert.call_args.args[0]['Payment_Status'], status)

    def test_duplicate_id_preserves_form(self):
        with patch('app.add_payment', side_effect=Error(errno=1062)):
            response = self.client.post('/payments/add', data=self.form)
        self.assertEqual(response.status_code, 409)
        self.assertIn(b'Payment ID already exists', response.data)
        self.assertIn(b'value="250.50"', response.data)

    def test_invalid_inputs_never_write(self):
        invalid = {
            'Payment_ID': ['', 'X' * 11, '../x', 'with space'],
            'Amount': ['', '0', '0.00', '-1', '1000000', '1.001', 'NaN', 'Infinity', '1e2', 'abc'],
            'Payment_Mode': ['', 'Bitcoin', 'UPI ' + 'x' * 20],
            'Payment_Date': ['', '2026-02-29', '2026-04-31', '0999-01-01', '2026-1-1', '2026-01-01T12:00'],
            'Payment_Status': ['', 'Refunded', 'paid'],
        }
        with patch('app.add_payment') as insert:
            for field, values in invalid.items():
                for value in values:
                    with self.subTest(field=field, value=value):
                        response = self.client.post('/payments/add', data=dict(self.form, **{field: value}))
                        self.assertEqual(response.status_code, 400)
            insert.assert_not_called()

    def test_amount_boundaries_leap_date_and_all_modes(self):
        with patch('app.add_payment'):
            for mode in application.PAYMENT_MODES:
                for amount in ('0.01', '999999.99'):
                    response = self.client.post('/payments/add', data=dict(self.form, Amount=amount,
                        Payment_Mode=mode, Payment_Date='2028-02-29'))
                    self.assertEqual(response.status_code, 302)

    def test_edit_preserves_id_and_never_confirms_booking(self):
        with patch('app.update_payment', return_value=True) as update, patch('app.update_booking_status') as confirm:
            response = self.client.get('/payments/PAY1/edit')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'readonly', response.data)
            response = self.client.post('/payments/PAY1/edit', data=dict(self.form, Payment_ID='OTHER', Payment_Status='Paid'))
            self.assertEqual(response.status_code, 302)
            update.assert_called_once()
            self.assertEqual(update.call_args.args[0], 'PAY1')
            self.assertEqual(update.call_args.args[1]['Payment_ID'], 'PAY1')
            confirm.assert_not_called()

    def test_invalid_edit_and_confirmed_booking_guard(self):
        with patch('app.update_payment') as update:
            self.assertEqual(self.client.post('/payments/PAY1/edit', data=dict(self.form, Amount='-1')).status_code, 400)
            update.assert_not_called()
        with patch('app.update_payment', side_effect=db.PaymentRuleError('Payment must remain Paid for a confirmed booking.')):
            response = self.client.post('/payments/PAY1/edit', data=self.form)
        self.assertEqual(response.status_code, 409)
        self.assertIn(b'must remain Paid', response.data)

    def test_details_show_all_associations_and_booking_links(self):
        with patch('app.get_payment_bookings', return_value=[self.booking, dict(self.booking, Booking_ID='B2')]):
            response = self.client.get('/payments/PAY1')
        self.assertEqual(response.status_code, 200)
        for value in (b'Test Movie', b'A1', b'href="/bookings/B1"', b'href="/bookings/B2"', b'250.50'):
            self.assertIn(value, response.data)
        self.assertIn(b'do not confirm bookings automatically', response.data)

    def test_unlinked_detail_and_html_escaping(self):
        with patch('app.get_payment_bookings', return_value=[]):
            self.assertIn(b'No bookings are linked', self.client.get('/payments/PAY1').data)
        with patch('app.get_payments', return_value=[dict(self.joined, Customer_Name='<script>bad</script>')]):
            response = self.client.get('/payments')
        self.assertIn(b'&lt;script&gt;', response.data)
        self.assertNotIn(b'<script>bad', response.data)

    def test_delete_requires_post_and_allows_unreferenced(self):
        with patch('app.delete_payment', return_value=True) as delete:
            self.assertEqual(self.client.get('/payments/PAY1/delete').status_code, 200)
            delete.assert_not_called()
            self.assertEqual(self.client.post('/payments/PAY1/delete', data=self.form).status_code, 302)
            delete.assert_called_once_with('PAY1')

    def test_referenced_delete_is_blocked(self):
        with patch('app.delete_payment', side_effect=Error(errno=1451)):
            response = self.client.post('/payments/PAY1/delete', data=self.form)
        self.assertEqual(response.status_code, 409)
        self.assertIn(b'including cancelled bookings', response.data)

    def test_missing_or_concurrently_deleted_payment(self):
        with patch('app.get_payment', return_value=None):
            for suffix in ('', '/edit', '/delete'):
                self.assertEqual(self.client.get('/payments/missing' + suffix).status_code, 404)
        with patch('app.update_payment', return_value=False):
            self.assertEqual(self.client.post('/payments/PAY1/edit', data=self.form).status_code, 404)
        with patch('app.delete_payment', return_value=False):
            self.assertEqual(self.client.post('/payments/PAY1/delete', data=self.form).status_code, 404)

    def test_csrf_blocks_every_write(self):
        with patch('app.get_payment') as select, patch('app.add_payment') as insert:
            for path in ('/payments/add', '/payments/PAY1/edit', '/payments/PAY1/delete'):
                self.assertEqual(self.client.post(path, data={}).status_code, 400)
            select.assert_not_called()
            insert.assert_not_called()

    def test_safe_database_errors_and_retry_message(self):
        with patch('app.get_payments', side_effect=Error(errno=1045, msg='private')):
            response = self.client.get('/payments')
            self.assertEqual(response.status_code, 503)
            self.assertNotIn(b'private', response.data)
        for name, path in [('add_payment', '/payments/add'), ('update_payment', '/payments/PAY1/edit'), ('delete_payment', '/payments/PAY1/delete')]:
            with patch('app.' + name, side_effect=Error(errno=9999, msg='private')):
                response = self.client.post(path, data=self.form)
                self.assertEqual(response.status_code, 503)
                self.assertNotIn(b'private', response.data)
        with patch('app.update_payment', side_effect=Error(errno=1213)):
            response = self.client.post('/payments/PAY1/edit', data=self.form)
            self.assertEqual(response.status_code, 409)
            self.assertIn(b'reload and try again', response.data)


class PaymentTransactionTests(unittest.TestCase):
    def setUp(self):
        self.connection = MagicMock()
        self.connection.__enter__.return_value = self.connection
        self.cursor = MagicMock()
        self.connection.cursor.return_value.__enter__.return_value = self.cursor
        mock = patch('db.get_connection', return_value=self.connection)
        mock.start()
        self.addCleanup(mock.stop)
        self.payment = dict(Payment_ID='P1', Amount=Decimal('300'), Payment_Mode='Cash',
                            Payment_Date='2026-11-04', Payment_Status='Pending')

    def test_search_uses_parameters_and_literal_wildcards(self):
        db.get_payments("x'_%!")
        sql, params = self.cursor.execute.call_args.args
        self.assertIn('LEFT JOIN Booking', sql)
        self.assertNotIn("x'", sql)
        self.assertEqual(params, ("x'_%!", "%x'!_!%!!%", "%x'!_!%!!%", "%x'!_!%!!%"))

    def test_pending_downgrade_rejected_atomically(self):
        self.cursor.fetchone.side_effect = [{'Payment_ID': 'P1'}, {'Booking_ID': 'B1'}]
        with self.assertRaisesRegex(db.PaymentRuleError, 'confirmed booking'):
            db.update_payment('P1', self.payment)
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()
        self.assertFalse(any('UPDATE Payment' in call.args[0] for call in self.cursor.execute.call_args_list))

    def test_unconfirmed_downgrade_commits(self):
        self.cursor.fetchone.side_effect = [{'Payment_ID': 'P1'}, None]
        self.assertTrue(db.update_payment('P1', self.payment))
        self.connection.start_transaction.assert_called_once_with(isolation_level='READ COMMITTED')
        self.assertIn('FOR UPDATE', self.cursor.execute.call_args_list[0].args[0])
        self.connection.commit.assert_called_once()

    def test_paid_edit_never_updates_bookings(self):
        self.cursor.fetchone.return_value = {'Payment_ID': 'P1'}
        self.assertTrue(db.update_payment('P1', dict(self.payment, Payment_Status='Paid')))
        self.assertFalse(any('UPDATE Booking' in call.args[0] for call in self.cursor.execute.call_args_list))
        self.connection.commit.assert_called_once()

    def test_missing_payment_rolls_back(self):
        self.cursor.fetchone.return_value = None
        self.assertFalse(db.update_payment('missing', self.payment))
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()

    def test_write_failures_roll_back(self):
        for operation in (lambda: db.add_payment(self.payment), lambda: db.delete_payment('P1'), lambda: db.update_payment('P1', self.payment)):
            self.connection.reset_mock()
            self.cursor.execute.side_effect = Error(errno=1451)
            with self.assertRaises(Error):
                operation()
            self.connection.rollback.assert_called_once()
            self.connection.commit.assert_not_called()

    def test_add_and_delete_commit(self):
        db.add_payment(self.payment)
        self.connection.commit.assert_called_once()
        sql, params = self.cursor.execute.call_args.args
        self.assertNotIn('P1', sql)
        self.assertEqual(params[0], 'P1')
        self.connection.reset_mock()
        self.cursor.rowcount = 1
        self.assertTrue(db.delete_payment('P1'))
        self.connection.commit.assert_called_once()
        self.cursor.rowcount = 0
        self.assertFalse(db.delete_payment('missing'))


if __name__ == '__main__':
    unittest.main()
