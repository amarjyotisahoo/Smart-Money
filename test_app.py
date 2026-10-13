"""
SmartMoney - Comprehensive Automated Test Suite
Tests authentication, 3 savings goals limit, zero double-counting, budgets, and insights.
"""

import unittest
from datetime import date
from app import app
from database import init_db, get_db_connection
from demo_data import seed_demo_data

class SmartMoneyTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        init_db()
        seed_demo_data(username="test_alex", email="test_alex@smartmoney.io", password="password123")

    def login_test_user(self):
        # Obtain CSRF token
        with self.client.session_transaction() as sess:
            sess['csrf_token'] = 'test-csrf-token'
        
        response = self.client.post('/login', data={
            'username_or_email': 'test_alex',
            'password': 'password123',
            'csrf_token': 'test-csrf-token'
        }, follow_redirects=True)
        return response

    def test_demo_login(self):
        response = self.client.get('/demo-login', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data)
        self.assertIn(b'Three Savings Goals', response.data)

    def test_dashboard_metrics(self):
        self.login_test_user()
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Monthly Income', response.data)
        self.assertIn(b'Monthly Expenses', response.data)
        self.assertIn(b'Daily Spending Limit', response.data)
        self.assertIn(b'Total Savings', response.data)

    def test_three_savings_goals_limit_enforcement(self):
        """Verify that exactly maximum 3 active goals are permitted."""
        self.login_test_user()
        
        # In demo data, user has 3 active goals already ("Buy a bike", "Buy a laptop", "Build an emergency fund")
        response = self.client.post('/api/goals/add', data={
            'name': 'Goal Number Four',
            'target_amount': '50000',
            'initial_savings': '0',
            'deadline': '2027-12-31',
            'csrf_token': 'test-csrf-token'
        })
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('up to 3 active savings goals', data['message'])

    def test_savings_contribution_not_counted_as_expense(self):
        """Verify savings contributions do NOT get counted as expense transactions."""
        self.login_test_user()
        
        # Check initial expense count & sum
        with self.client.session_transaction() as sess:
            user_id = sess['user_id']
            
        conn = get_db_connection()
        initial_expenses_sum = conn.execute("SELECT SUM(amount) as t FROM expenses WHERE user_id = ?", (user_id,)).fetchone()['t']
        goal = conn.execute("SELECT id, current_amount FROM savings_goals WHERE user_id = ? AND is_completed = 0 LIMIT 1", (user_id,)).fetchone()
        conn.close()

        goal_id = goal['id']
        old_goal_amount = goal['current_amount']

        # Add contribution
        resp = self.client.post(f'/api/goals/contribute/{goal_id}', data={
            'amount': '3000',
            'date': date.today().strftime('%Y-%m-%d'),
            'notes': 'Test Isolated Deposit',
            'csrf_token': 'test-csrf-token'
        })
        self.assertEqual(resp.status_code, 200)
        
        # Verify goal increased
        conn = get_db_connection()
        new_goal_amount = conn.execute("SELECT current_amount FROM savings_goals WHERE id = ?", (goal_id,)).fetchone()['current_amount']
        new_expenses_sum = conn.execute("SELECT SUM(amount) as t FROM expenses WHERE user_id = ?", (user_id,)).fetchone()['t']
        conn.close()

        self.assertEqual(new_goal_amount, old_goal_amount + 3000)
        # Expenses MUST remain completely unchanged!
        self.assertEqual(new_expenses_sum, initial_expenses_sum)

    def test_expense_crud(self):
        self.login_test_user()
        
        # Add expense
        resp = self.client.post('/api/expenses/add', data={
            'amount': '450.50',
            'category': 'Food',
            'date': date.today().strftime('%Y-%m-%d'),
            'payment_method': 'UPI',
            'description': 'UniqueSpecialMocha99',
            'csrf_token': 'test-csrf-token'
        })
        self.assertEqual(resp.status_code, 200)

        # Query expenses API
        resp_list = self.client.get('/api/expenses?search=UniqueSpecialMocha99')
        data = resp_list.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['expenses']), 1)
        exp_id = data['expenses'][0]['id']

        # Edit expense
        resp_edit = self.client.post(f'/api/expenses/edit/{exp_id}', data={
            'amount': '500.00',
            'category': 'Food',
            'date': date.today().strftime('%Y-%m-%d'),
            'payment_method': 'Cash',
            'description': 'UniqueSpecialMocha99 Updated',
            'csrf_token': 'test-csrf-token'
        })
        self.assertEqual(resp_edit.status_code, 200)

        # Delete expense
        resp_del = self.client.post(f'/api/expenses/delete/{exp_id}', data={
            'csrf_token': 'test-csrf-token'
        })
        self.assertEqual(resp_del.status_code, 200)

    def test_insights_generation(self):
        self.login_test_user()
        resp = self.client.get('/api/insights')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertGreater(len(data['insights']), 0)
        
        # Check that top category or budget insight exists
        has_top_cat = any('highest spending category' in i['title'] for i in data['insights'])
        self.assertTrue(has_top_cat)

    def test_csv_exports(self):
        self.login_test_user()
        
        # Expenses CSV
        resp_exp = self.client.get('/reports/export/expenses')
        self.assertEqual(resp_exp.status_code, 200)
        self.assertIn(b'Category,Amount,Payment Method', resp_exp.data)

        # Incomes CSV
        resp_inc = self.client.get('/reports/export/incomes')
        self.assertEqual(resp_inc.status_code, 200)
        self.assertIn(b'Date,Source,Amount,Status', resp_inc.data)

        # Ledger CSV
        resp_all = self.client.get('/reports/export/all')
        self.assertEqual(resp_all.status_code, 200)
        self.assertIn(b'Record Type', resp_all.data)

if __name__ == '__main__':
    unittest.main()
