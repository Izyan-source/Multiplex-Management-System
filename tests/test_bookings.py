"""Booking UI and transaction checks. All database access is mocked here."""

import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from mysql.connector import Error

import app as application
import db


class BookingTests(unittest.TestCase):
    def setUp(self):
        self.client = application.app.test_client()
        self.customers = [{'Customer_ID': 'C1', 'Customer_Name': 'Test Customer'}]
        self.shows = [{'Show_ID': 'S1', 'Movie_Name': 'Test Movie', 'Screen_Name': 'Screen 1',
                       'Show_Date': '2026-08-15', 'Show_Time': '10:00:00', 'Ticket_Price': Decimal('250')}]
        self.payments = [{'Payment_ID': 'P1', 'Amount': Decimal('250'), 'Payment_Status': 'Paid', 'Payment_Mode': 'Cash'}]
        self.seats = [{'Seat_ID': 'E1', 'Seat_Number': 'A1', 'Seat_Type': 'Regular'}]
        self.form = {'Booking_ID': 'B1', 'Customer_ID': 'C1', 'Show_ID': 'S1', 'Seat_ID': 'E1',
                     'Payment_ID': 'P1', 'Booking_Date': '2026-08-12', 'Booking_Time': '09:30',
                     'Total_Amount': '250.00', 'Booking_Status': 'Pending', 'csrf_token': 'test-token'}
        self.booking = {key: None for key in (
            'Phone', 'Email', 'Movie_ID', 'Screen_ID', 'Multiplex_Name', 'Payment_Date'
        )}
        self.booking.update(self.form)
        self.booking.update(Customer_Name='Test Customer', Movie_Name='Test Movie',
                            Show_Date='2026-08-15', Show_Time='10:00:00', Screen_Name='Screen 1',
                            Seat_Number='A1', Seat_Type='Regular', Total_Amount=Decimal('250'),
                            Ticket_Price=Decimal('250'), Payment_Amount=Decimal('250'),
                            Payment_Mode='Cash', Payment_Status='Paid')
        with self.client.session_transaction() as session:
            session['csrf_token'] = 'test-token'
        for name, result in [('get_customers', self.customers), ('get_shows', self.shows),
                             ('get_booking_payments', self.payments), ('get_available_seats', self.seats),
                             ('get_booking', self.booking)]:
            mock = patch('app.' + name, return_value=result)
            mock.start()
            self.addCleanup(mock.stop)

    def test_list_and_search(self):
        with patch('app.get_bookings', return_value=[self.booking]) as query:
            response = self.client.get('/bookings', query_string={'q': ' Test '})
        self.assertEqual(response.status_code, 200)
        query.assert_called_once_with('Test')
        for text in (b'Booking ID', b'Customer Name', b'Movie Name', b'Show Date', b'Show Time',
                     b'Seat Number', b'Payment ID', b'Booking Date', b'Total Amount', b'Booking Status',
                     b'Test Customer', b'Test Movie', b'A1', b'250.00'):
            self.assertIn(text, response.data)

    def test_empty_and_unavailable_list(self):
        with patch('app.get_bookings', return_value=[]):
            self.assertIn(b'No bookings match', self.client.get('/bookings?q=missing').data)
        with patch('app.get_bookings', side_effect=Error(errno=1045, msg='private')):
            response = self.client.get('/bookings')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b'private', response.data)

    def test_show_selection_and_live_seat_choices(self):
        initial = self.client.get('/bookings/add')
        self.assertEqual(initial.status_code, 200)
        self.assertIn(b'Load seats', initial.data)
        self.assertNotIn(b'id="Seat_ID"', initial.data)
        with patch('app.get_available_seats', return_value=self.seats) as query:
            response = self.client.get('/bookings/add?Show_ID=S1')
        query.assert_called_once_with('S1')
        self.assertIn(b'value="E1"', response.data)
        self.assertIn(b'value="P1"', response.data)

    def test_no_seats_disables_creation(self):
        with patch('app.get_available_seats', return_value=[]):
            response = self.client.get('/bookings/add?Show_ID=S1')
        self.assertIn(b'No available seats', response.data)
        self.assertIn(b'type="submit" disabled', response.data)

    def test_create_pending_and_confirmed(self):
        with patch('app.add_booking') as insert:
            for status in ('Pending', 'Confirmed'):
                response = self.client.post('/bookings/add', data=dict(self.form, Booking_Status=status))
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, '/bookings/B1')
                self.assertEqual(insert.call_args.args[0]['Booking_Time'], '09:30:00')
                self.assertEqual(insert.call_args.args[0]['Total_Amount'], Decimal('250'))

    def test_invalid_form_does_not_write(self):
        invalid = {
            'Booking_ID': ['', 'X' * 11, '../x'], 'Customer_ID': ['', 'missing'],
            'Show_ID': ['', 'missing'], 'Seat_ID': ['', 'X' * 11], 'Payment_ID': ['', 'missing'],
            'Booking_Date': ['', '2026-02-29', '0999-01-01'], 'Booking_Time': ['', '24:00', '1:30'],
            'Total_Amount': ['', '0', '-1', '1000000', '1.001', 'NaN', '1e2'],
            'Booking_Status': ['', 'Cancelled', 'invalid'],
        }
        with patch('app.add_booking') as insert:
            for key, values in invalid.items():
                for value in values:
                    with self.subTest(field=key, value=value):
                        self.assertEqual(self.client.post('/bookings/add', data=dict(self.form, **{key: value})).status_code, 400)
            insert.assert_not_called()

    def test_reservation_and_unpaid_errors_preserve_form(self):
        for message in ('This seat is already reserved for this show.', 'Payment must be Paid.'):
            with patch('app.add_booking', side_effect=db.BookingRuleError(message)):
                response = self.client.post('/bookings/add', data=self.form)
            self.assertEqual(response.status_code, 409)
            self.assertIn(message.encode(), response.data)
            self.assertIn(b'value="B1"', response.data)

    def test_trigger_and_duplicate_id_messages(self):
        for error, text in [(Error(errno=1062), b'Booking ID already exists'),
                            (Error(errno=1644, msg='payment incomplete'), b'linked payment is Paid'),
                            (Error(errno=1644, msg='seat reserved'), b'already reserved'),
                            (Error(errno=1452), b'no longer exists'),
                            (Error(errno=1213), b'Nothing was saved')]:
            with patch('app.add_booking', side_effect=error):
                response = self.client.post('/bookings/add', data=self.form)
            self.assertEqual(response.status_code, 409)
            self.assertIn(text, response.data)

    def test_complete_detail_and_escaping(self):
        with patch('app.get_booking', return_value=dict(self.booking, Customer_Name='<script>alert(1)</script>')):
            response = self.client.get('/bookings/B1')
        self.assertEqual(response.status_code, 200)
        for label in (b'Booking Time', b'Payment Amount', b'Payment Status', b'Seat ID', b'Show ID'):
            self.assertIn(label, response.data)
        self.assertIn(b'&lt;script&gt;', response.data)
        self.assertNotIn(b'<script>alert', response.data)

    def test_status_updates(self):
        with patch('app.update_booking_status', return_value=True) as update:
            for status in ('Confirmed', 'Cancelled'):
                response = self.client.post('/bookings/B1/status', data={'Booking_Status':status, 'csrf_token':'test-token'})
                self.assertEqual(response.status_code, 302)
                update.assert_called_with('B1', status)

    def test_status_rule_failure(self):
        with patch('app.update_booking_status', side_effect=db.BookingRuleError('Payment must be Paid.')):
            response = self.client.post('/bookings/B1/status', data={'Booking_Status':'Confirmed', 'csrf_token':'test-token'})
        self.assertEqual(response.status_code, 409)
        self.assertIn(b'Payment must be Paid', response.data)

    def test_history_has_no_delete_or_reopen_action(self):
        with patch('app.get_booking', return_value=dict(self.booking, Booking_Status='Cancelled')):
            response = self.client.get('/bookings/B1')
        self.assertIn(b'retained for reference', response.data)
        self.assertNotIn(b'Update Status', response.data)
        self.assertEqual(self.client.post('/bookings/B1/delete', data=self.form).status_code, 404)
        self.assertEqual(self.client.get('/bookings/B1/status').status_code, 405)
        with patch('app.update_booking_status') as update:
            response = self.client.post('/bookings/B1/status', data={'Booking_Status':'Pending', 'csrf_token':'test-token'})
            self.assertEqual(response.status_code, 400)
            update.assert_not_called()

    def test_missing_booking(self):
        with patch('app.get_booking', return_value=None):
            self.assertEqual(self.client.get('/bookings/missing').status_code, 404)
        with patch('app.update_booking_status', return_value=False):
            response = self.client.post('/bookings/missing/status', data={'Booking_Status':'Cancelled', 'csrf_token':'test-token'})
            self.assertEqual(response.status_code, 404)

    def test_csrf_blocks_writes(self):
        with patch('app.add_booking') as insert, patch('app.update_booking_status') as update:
            self.assertEqual(self.client.post('/bookings/add', data={}).status_code, 400)
            self.assertEqual(self.client.post('/bookings/B1/status', data={}).status_code, 400)
            insert.assert_not_called()
            update.assert_not_called()


class BookingTransactionTests(unittest.TestCase):
    def setUp(self):
        self.connection = MagicMock()
        self.connection.__enter__.return_value = self.connection
        self.cursor = MagicMock()
        self.connection.cursor.return_value.__enter__.return_value = self.cursor
        mock = patch('db.get_connection', return_value=self.connection)
        mock.start()
        self.addCleanup(mock.stop)
        self.booking = dict(Booking_ID='B1', Customer_ID='C1', Show_ID='S1', Seat_ID='E1',
                            Payment_ID='P1', Booking_Date='2026-08-12', Booking_Time='09:00',
                            Total_Amount=Decimal('250'), Booking_Status='Confirmed')

    def test_confirmed_creation_inserts_pending_then_updates(self):
        self.cursor.fetchone.side_effect = [{'Screen_ID':'SC1'}, {'Screen_ID':'SC1'}, None,
                                           {'Payment_Status':'Paid'}, {'Customer_ID':'C1'}]
        db.add_booking(self.booking)
        statements = [call.args[0] for call in self.cursor.execute.call_args_list]
        self.assertTrue(any('INSERT INTO Booking' in sql and "'Pending'" in sql for sql in statements))
        self.assertTrue(any("UPDATE Booking SET Booking_Status = 'Confirmed'" in sql for sql in statements))
        self.connection.start_transaction.assert_called_once_with(isolation_level='READ COMMITTED')
        self.connection.commit.assert_called_once()

    def test_wrong_screen_rolls_back_before_insert(self):
        self.cursor.fetchone.side_effect = [{'Screen_ID':'SC1'}, {'Screen_ID':'SC2'}]
        with self.assertRaisesRegex(db.BookingRuleError, 'screen'):
            db.add_booking(self.booking)
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()
        self.assertFalse(any('INSERT INTO Booking' in call.args[0] for call in self.cursor.execute.call_args_list))

    def test_null_or_pending_payment_cannot_confirm(self):
        for status in (None, 'Pending'):
            self.cursor.fetchone.side_effect = [{'Screen_ID':'SC1'}, {'Screen_ID':'SC1'}, None, {'Payment_Status':status}]
            with self.assertRaisesRegex(db.BookingRuleError, 'Paid'):
                db.add_booking(self.booking)
        self.connection.commit.assert_not_called()

    def test_update_trigger_failure_rolls_back_insert(self):
        self.cursor.fetchone.side_effect = [{'Screen_ID':'SC1'}, {'Screen_ID':'SC1'}, None,
                                           {'Payment_Status':'Paid'}, {'Customer_ID':'C1'}]
        def fail_update(sql, params=()):
            if 'UPDATE Booking' in sql:
                raise Error(errno=1644, msg='payment incomplete')
        self.cursor.execute.side_effect = fail_update
        with self.assertRaises(Error):
            db.add_booking(self.booking)
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()

    def test_duplicate_reservation_rolls_back(self):
        self.cursor.fetchone.side_effect = [{'Screen_ID':'SC1'}, {'Screen_ID':'SC1'}, {'Booking_ID':'OTHER'}]
        with self.assertRaisesRegex(db.BookingRuleError, 'reserved'):
            db.add_booking(self.booking)
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
