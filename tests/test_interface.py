"""Shared interface checks. These tests do not connect to MySQL."""

import unittest
from html.parser import HTMLParser
from unittest.mock import patch

from flask import flash, render_template
import app as application


class Elements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.movie = dict(Movie_ID='M1', Movie_Name='Test Movie', Genre='Drama', Language='Hindi', Duration_Min=120, Rating=8)
        self.customer = dict(Customer_ID='C1', Customer_Name='Test Customer', Phone='9876543210', Email='test@example.com', Gender='Other')
        self.show = dict(Show_ID='S1', Movie_ID='M1', Movie_Name='Test Movie', Screen_ID='SC1', Screen_Name='Screen 1', Show_Date='2026-11-04', Show_Time='10:00:00', Ticket_Price=250)
        self.payment = dict(Payment_ID='P1', Amount=250, Payment_Mode='UPI', Payment_Date='2026-11-04', Payment_Status='Paid', Booking_ID='B1', Customer_Name='Test Customer')
        self.booking = dict(self.show, Booking_ID='B1', Customer_ID='C1', Customer_Name='Test Customer', Seat_ID='E1', Seat_Number='A1', Seat_Type='Regular', Payment_ID='P1', Booking_Date='2026-11-04', Booking_Time='09:00:00', Total_Amount=250, Booking_Status='Pending', Payment_Amount=250, Payment_Mode='UPI', Payment_Status='Paid', Payment_Date='2026-11-04', Phone=None, Email=None, Multiplex_Name=None)
        self.order = dict(self.booking, Order_ID='F1', Item_Name='Test item', Quantity=2, Total_Price=100)
        self.context = dict(movie=self.movie, customer=self.customer, show=self.show, payment=self.payment,
            booking=self.booking, order=self.order, movies=[self.movie], customers=[self.customer], shows=[self.show],
            payments=[self.payment], bookings=[self.booking], orders=[self.order], screens=[dict(Screen_ID='SC1', Screen_Name='Screen 1', Multiplex_Name='Test cinema')],
            seats=[dict(Seat_ID='E1', Seat_Number='A1', Seat_Type='Regular')], selected_show=self.show,
            modes=application.PAYMENT_MODES, statuses=application.PAYMENT_STATUSES, genders=application.CUSTOMER_GENDERS,
            editing=False, errors=[], error=None, search='', counts=dict(movies=1, customers=1, bookings=1, multiplexes=1))
        self.modules = ('movies', 'customers', 'shows', 'bookings', 'payments', 'food_orders')

    def render(self, template, **changes):
        with application.app.test_request_context('/'):
            return render_template(template, **dict(self.context, **changes))

    def test_required_controls_have_labels_and_cancel_links(self):
        for module in self.modules:
            with self.subTest(module=module):
                html = self.render(module + '/form.html')
                tags = Elements(html).tags
                labels = {attrs.get('for') for tag, attrs in tags if tag == 'label'}
                for tag, attrs in tags:
                    if tag in ('input', 'select') and 'required' in attrs:
                        self.assertIn(attrs['id'], labels)
                self.assertIn('Fields marked * are required', html)
                self.assertIn('required-indicator', html)
                self.assertIn('>Cancel</a>', html)
                self.assertIn('Back to ', html)
                self.assertNotIn('onchange=', html)

    def test_tables_are_named_keyboard_regions(self):
        for template in [m + '/list.html' for m in self.modules] + ['payments/detail.html']:
            with self.subTest(template=template):
                tags = Elements(self.render(template)).tags
                regions = [attrs for tag, attrs in tags if 'table-responsive' in attrs.get('class', '')]
                self.assertEqual(len(regions), 1)
                self.assertEqual(regions[0]['tabindex'], '0')
                self.assertEqual(regions[0]['role'], 'region')
                self.assertTrue(regions[0]['aria-label'])
                self.assertEqual(regions[0]['aria-describedby'], 'table-help')
                self.assertTrue(any(attrs.get('id') == 'table-help' for _, attrs in tags))

    def test_server_validation_summary_is_consistent_and_escaped(self):
        for module in self.modules:
            html = self.render(module + '/form.html', errors=['Correct this <item>.'])
            self.assertIn('data-error-summary', html)
            self.assertIn('tabindex="-1"', html)
            self.assertIn('Your changes have not been saved', html)
            self.assertIn('Correct this &lt;item&gt;.', html)
            self.assertNotIn('Correct this <item>.', html)

    def test_success_closure_is_visible_on_all_destinations(self):
        templates = [m + '/list.html' for m in self.modules] + [m + '/detail.html' for m in ('bookings', 'payments', 'food_orders')]
        for template in templates:
            with application.app.test_request_context('/'):
                flash('Record saved successfully.', 'success')
                html = render_template(template, **self.context)
            self.assertIn('role="status"', html)
            self.assertIn('Completed.', html)
            self.assertIn('Record saved successfully.', html)

    def test_delete_pages_keep_explicit_submit_cancel_and_back(self):
        for module in ('movies', 'customers', 'shows', 'payments', 'food_orders'):
            html = self.render(module + '/delete.html')
            self.assertIn('Deletion cannot be undone.', html)
            self.assertIn('>Cancel</a>', html)
            self.assertIn('Back to ', html)
            self.assertIn('method="post"', html)
            self.assertIn('name="csrf_token"', html)
            tags = Elements(html).tags
            self.assertTrue(any(tag == 'button' and attrs.get('type') == 'submit' and 'btn-danger' in attrs.get('class', '') for tag, attrs in tags))
            self.assertFalse(any(tag == 'button' and attrs.get('type') == 'submit' and 'Cancel' in attrs.get('value', '') for tag, attrs in tags))

    def test_all_pages_have_skip_target_and_deferred_shared_script(self):
        for template in ['dashboard.html'] + [m + '/list.html' for m in self.modules]:
            tags = Elements(self.render(template)).tags
            self.assertTrue(any(tag == 'main' and attrs.get('id') == 'main-content' and attrs.get('tabindex') == '-1' for tag, attrs in tags))
            self.assertTrue(any(tag == 'script' and attrs.get('src') == '/static/interface.js' and 'defer' in attrs for tag, attrs in tags))
            self.assertFalse(any(tag == 'script' and 'src' not in attrs for tag, attrs in tags))

    def test_booking_status_remains_explicit_with_context_and_cancel(self):
        html = self.render('bookings/detail.html')
        self.assertIn('Select a status before choosing Update Status', html)
        self.assertIn('Cancelled bookings cannot be reopened', html)
        self.assertIn('aria-describedby="status-help"', html)
        self.assertIn('>Cancel</a>', html)
        self.assertIn('action="/bookings/B1/status"', html)
        self.assertIn('method="post"', html)

    def test_actual_invalid_post_and_success_redirect_feedback(self):
        client = application.app.test_client()
        with client.session_transaction() as session:
            session['csrf_token'] = 'ui-test'
        with patch('app.add_movie') as insert:
            response = client.post('/movies/add', data={'csrf_token':'ui-test'})
            self.assertEqual(response.status_code, 400)
            self.assertIn(b'Your changes have not been saved', response.data)
            insert.assert_not_called()
        with patch('app.add_movie'), patch('app.get_movies', return_value=[self.movie]):
            response = client.post('/movies/add', data=dict(self.movie, csrf_token='ui-test'), follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Completed.', response.data)
            self.assertIn(b'Movie added successfully.', response.data)


if __name__ == '__main__':
    unittest.main()
