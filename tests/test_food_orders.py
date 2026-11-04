"""Food order page and query tests; database access is mocked."""

import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from mysql.connector import Error

import app as application
import db


class FoodOrderTests(unittest.TestCase):
    def setUp(self):
        self.client = application.app.test_client()
        self.bookings = [dict(Booking_ID='B1', Customer_Name='Test Customer', Movie_Name='Test Movie', Booking_Status='Confirmed'),
                         dict(Booking_ID='B2', Customer_Name='Another Customer', Movie_Name='Another Movie', Booking_Status='Pending')]
        self.form = dict(Order_ID='FO1', Booking_ID='B1', Item_Name='Test item', Quantity='2', Total_Price='250.50', csrf_token='test-token')
        self.order = dict(self.form, Quantity=2, Total_Price=Decimal('250.50'), Customer_Name='Test Customer',
                          Movie_Name='Test Movie', Booking_Status='Confirmed', Show_Date='2026-11-04', Show_Time='10:00:00')
        with self.client.session_transaction() as session:
            session['csrf_token'] = 'test-token'
        for name, result in [('get_bookings', self.bookings), ('get_food_order', self.order)]:
            mock = patch('app.' + name, return_value=result)
            mock.start()
            self.addCleanup(mock.stop)

    def test_list_joined_fields_and_navigation(self):
        with patch('app.get_food_orders', return_value=[self.order]):
            response = self.client.get('/food-orders')
        self.assertEqual(response.status_code, 200)
        for value in (b'Order ID', b'Booking ID', b'Customer Name', b'Movie Name', b'Item Name', b'Quantity',
                      b'Total Price', b'Test Customer', b'Test Movie', b'Test item', b'250.50'):
            self.assertIn(value, response.data)
        self.assertIn(b'href="/food-orders" aria-current="page"', response.data)

    def test_search_all_fields_and_empty_results(self):
        for term in ('FO1', 'B1', 'Test Customer', 'Test item', "' OR 1=1 --", '%_!'):
            with patch('app.get_food_orders', return_value=[]) as select:
                response = self.client.get('/food-orders', query_string={'q': ' ' + term + ' '})
                select.assert_called_once_with(term)
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'No food orders match', response.data)
        with patch('app.get_food_orders', return_value=[]):
            self.assertIn(b'No food orders yet', self.client.get('/food-orders').data)

    def test_form_uses_existing_bookings_and_free_text_item(self):
        response = self.client.get('/food-orders/add')
        self.assertEqual(response.status_code, 200)
        for value in (b'value="B1"', b'value="B2"', b'Test Customer', b'Test Movie', b'id="Item_Name"'):
            self.assertIn(value, response.data)
        self.assertNotIn(b'<select class="form-select" id="Item_Name"', response.data)

    def test_add_order(self):
        with patch('app.add_food_order') as insert:
            response = self.client.post('/food-orders/add', data=self.form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/food-orders/FO1')
        self.assertEqual(insert.call_args.args[0]['Quantity'], 2)
        self.assertEqual(insert.call_args.args[0]['Total_Price'], Decimal('250.50'))

    def test_duplicate_id_preserves_form(self):
        with patch('app.add_food_order', side_effect=Error(errno=1062)):
            response = self.client.post('/food-orders/add', data=self.form)
        self.assertEqual(response.status_code, 409)
        self.assertIn(b'Order ID already exists', response.data)
        self.assertIn(b'value="Test item"', response.data)
        self.assertIn(b'value="B1" selected', response.data)

    def test_invalid_inputs_never_write(self):
        invalid = {
            'Order_ID': ['', 'X' * 11, '../x', 'with space'],
            'Booking_ID': ['', 'missing', "' OR 1=1 --"],
            'Item_Name': ['', '   ', 'X' * 101, 'Item\x00name', 'Item\nname'],
            'Quantity': ['', '0', '-1', '1.5', '1e2', '2147483648', '9' * 100, 'abc'],
            'Total_Price': ['', '0', '-1', '1000000', '1.001', 'NaN', 'Infinity', '1e2', 'abc'],
        }
        with patch('app.add_food_order') as insert:
            for field, values in invalid.items():
                for value in values:
                    with self.subTest(field=field, value=value):
                        self.assertEqual(self.client.post('/food-orders/add', data=dict(self.form, **{field: value})).status_code, 400)
            insert.assert_not_called()

    def test_valid_boundaries_and_unicode_item(self):
        with patch('app.add_food_order'):
            for quantity, price in [('1', '0.01'), ('2147483647', '999999.99')]:
                self.assertEqual(self.client.post('/food-orders/add', data=dict(self.form,
                    Quantity=quantity, Total_Price=price, Item_Name="Chef's चाय & snack")).status_code, 302)
            self.assertEqual(self.client.post('/food-orders/add', data=dict(self.form, Item_Name='X' * 100)).status_code, 302)

    def test_no_bookings_disables_form_and_rejects_post(self):
        with patch('app.get_bookings', return_value=[]), patch('app.add_food_order') as insert:
            response = self.client.get('/food-orders/add')
            self.assertIn(b'requires an existing booking', response.data)
            self.assertIn(b'type="submit" disabled', response.data)
            self.assertEqual(self.client.post('/food-orders/add', data=self.form).status_code, 400)
            insert.assert_not_called()

    def test_reference_removed_after_validation(self):
        for operation, path in [('add_food_order', '/food-orders/add'), ('update_food_order', '/food-orders/FO1/edit')]:
            with patch('app.' + operation, side_effect=Error(errno=1452)):
                response = self.client.post(path, data=self.form)
                self.assertEqual(response.status_code, 409)
                self.assertIn(b'booking no longer exists', response.data)

    def test_edit_all_fields_preserves_id(self):
        with patch('app.update_food_order', return_value=True) as update:
            response = self.client.get('/food-orders/FO1/edit')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'readonly', response.data)
            self.assertIn(b'value="B1" selected', response.data)
            response = self.client.post('/food-orders/FO1/edit', data=dict(self.form, Order_ID='OTHER',
                Booking_ID='B2', Item_Name='Changed item', Quantity='3', Total_Price='400'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(update.call_args.args, ('FO1', dict(Order_ID='FO1', Booking_ID='B2',
            Item_Name='Changed item', Quantity=3, Total_Price=Decimal('400'))))

    def test_invalid_edit_never_writes(self):
        with patch('app.update_food_order') as update:
            for field, value in [('Booking_ID', ''), ('Booking_ID', 'missing'), ('Quantity', '0'), ('Total_Price', '-1')]:
                self.assertEqual(self.client.post('/food-orders/FO1/edit', data=dict(self.form, **{field: value})).status_code, 400)
            update.assert_not_called()

    def test_details_and_escaping(self):
        with patch('app.get_food_order', return_value=dict(self.order, Item_Name='<script>bad</script>')):
            response = self.client.get('/food-orders/FO1')
        self.assertEqual(response.status_code, 200)
        for value in (b'Test Customer', b'Test Movie', b'250.50', b'Booking Status', b'href="/bookings/B1"', b'&lt;script&gt;'):
            self.assertIn(value, response.data)
        self.assertNotIn(b'<script>bad', response.data)

    def test_null_legacy_fields_remain_visible(self):
        legacy = dict(self.order, Booking_ID=None, Customer_Name=None, Movie_Name=None, Item_Name=None,
                      Quantity=None, Total_Price=None, Booking_Status=None, Show_Date=None, Show_Time=None)
        with patch('app.get_food_orders', return_value=[legacy]), patch('app.get_food_order', return_value=legacy):
            for path in ('/food-orders', '/food-orders/FO1', '/food-orders/FO1/delete'):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_delete_confirmation_does_not_write_until_post(self):
        with patch('app.delete_food_order', return_value=True) as delete:
            response = self.client.get('/food-orders/FO1/delete')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Test item', response.data)
            delete.assert_not_called()
            response = self.client.post('/food-orders/FO1/delete', data=self.form)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/food-orders')
            delete.assert_called_once_with('FO1')

    def test_delete_constraint_error_is_friendly(self):
        for errno, message in [(1451, b'another record references it'), (3819, b'database constraint'), (1644, b'database constraint')]:
            with patch('app.delete_food_order', side_effect=Error(errno=errno, msg='private')):
                response = self.client.post('/food-orders/FO1/delete', data=self.form)
                self.assertEqual(response.status_code, 409)
                self.assertIn(message, response.data)
                self.assertNotIn(b'private', response.data)

    def test_missing_and_concurrently_deleted_order(self):
        with patch('app.get_food_order', return_value=None):
            for suffix in ('', '/edit', '/delete'):
                self.assertEqual(self.client.get('/food-orders/missing' + suffix).status_code, 404)
        for operation, suffix in [('update_food_order', '/edit'), ('delete_food_order', '/delete')]:
            with patch('app.' + operation, return_value=False):
                self.assertEqual(self.client.post('/food-orders/FO1' + suffix, data=self.form).status_code, 404)

    def test_csrf_blocks_all_writes(self):
        with patch('app.get_food_order') as select, patch('app.add_food_order') as insert:
            for path in ('/food-orders/add', '/food-orders/FO1/edit', '/food-orders/FO1/delete'):
                self.assertEqual(self.client.post(path, data={}).status_code, 400)
            select.assert_not_called()
            insert.assert_not_called()

    def test_database_errors_are_safe(self):
        for operation, path in [('get_food_orders', '/food-orders'), ('get_bookings', '/food-orders/add'), ('get_food_order', '/food-orders/FO1')]:
            with patch('app.' + operation, side_effect=Error(errno=1045, msg='private')):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 503)
                self.assertNotIn(b'private', response.data)
        for operation, path in [('add_food_order', '/food-orders/add'), ('update_food_order', '/food-orders/FO1/edit'), ('delete_food_order', '/food-orders/FO1/delete')]:
            with patch('app.' + operation, side_effect=Error(errno=9999, msg='private')):
                response = self.client.post(path, data=self.form)
                self.assertEqual(response.status_code, 503)
                self.assertNotIn(b'private', response.data)


class FoodOrderQueryTests(unittest.TestCase):
    def setUp(self):
        self.connection = MagicMock()
        self.connection.__enter__.return_value = self.connection
        self.cursor = MagicMock()
        self.connection.cursor.return_value.__enter__.return_value = self.cursor
        mock = patch('db.get_connection', return_value=self.connection)
        mock.start()
        self.addCleanup(mock.stop)
        self.order = dict(Order_ID='F1', Booking_ID='B1', Item_Name="Chef's item", Quantity=2, Total_Price=Decimal('250'))

    def test_search_parameterization_and_joins(self):
        db.get_food_orders("x'_%!")
        sql, params = self.cursor.execute.call_args.args
        for join in ('LEFT JOIN Booking', 'LEFT JOIN Customer', 'LEFT JOIN `Show`', 'LEFT JOIN Movie'):
            self.assertIn(join, sql)
        self.assertNotIn("x'", sql)
        self.assertEqual(params, ("x'_%!",) + ("%x'!_!%!!%",) * 4)

    def test_detail_uses_bound_id(self):
        db.get_food_order("x' OR 1=1 --")
        sql, params = self.cursor.execute.call_args.args
        self.assertNotIn("x'", sql)
        self.assertEqual(params, ("x' OR 1=1 --",))

    def test_insert_commits_with_bound_values(self):
        db.add_food_order(self.order)
        sql, params = self.cursor.execute.call_args.args
        self.assertNotIn("Chef's", sql)
        self.assertEqual(params, ('F1', 'B1', "Chef's item", 2, Decimal('250')))
        self.connection.commit.assert_called_once()

    def test_update_accepts_unchanged_and_detects_missing(self):
        self.cursor.rowcount = 0
        self.cursor.fetchone.return_value = ('F1',)
        self.assertTrue(db.update_food_order('F1', self.order))
        sql, params = self.cursor.execute.call_args_list[0].args
        self.assertNotIn('SET Order_ID', sql)
        self.assertEqual(params, ('B1', "Chef's item", 2, Decimal('250'), 'F1'))
        self.connection.commit.assert_called_once()
        self.cursor.fetchone.return_value = None
        self.assertFalse(db.update_food_order('missing', self.order))

    def test_delete_commits_and_reports_missing(self):
        self.cursor.rowcount = 1
        self.assertTrue(db.delete_food_order('F1'))
        self.cursor.execute.assert_called_once_with('DELETE FROM Food_Order WHERE Order_ID = %s', ('F1',))
        self.connection.commit.assert_called_once()
        self.cursor.rowcount = 0
        self.assertFalse(db.delete_food_order('missing'))

    def test_constraint_failures_roll_back_every_write(self):
        for operation, errno in [(lambda: db.add_food_order(self.order), 1062),
                                 (lambda: db.update_food_order('F1', self.order), 1452),
                                 (lambda: db.delete_food_order('F1'), 1451)]:
            self.connection.reset_mock()
            self.cursor.execute.side_effect = Error(errno=errno)
            with self.assertRaises(Error):
                operation()
            self.connection.rollback.assert_called_once()
            self.connection.commit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
