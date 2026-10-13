"""
SmartMoney - Personal Finance & Savings Tracker
Main Application & Backend API
"""

import os
import secrets
import csv
import io
import math
from datetime import datetime, timedelta, date
from calendar import monthrange
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, session,
    flash, jsonify, make_response, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection, init_db
from demo_data import seed_demo_data

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'smartmoney-fintech-secure-secret-key-2026')

# Initialize DB if not exists
init_db()

# --- Helper Decorators & Security ---

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    if 'user_id' not in session:
        return None
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    conn.close()
    return user

@app.before_request
def csrf_protect():
    """Generates CSRF token and validates state-changing requests."""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(24)

    if request.method in ('POST', 'PUT', 'DELETE'):
        token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
        if not token or token != session.get('csrf_token'):
            # Allow JSON error response for API calls or abort 403
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Invalid CSRF validation token'}), 403
            flash('Security token invalid or expired. Please try again.', 'danger')
            return redirect(request.referrer or url_for('dashboard'))

@app.context_processor
def inject_global_template_vars():
    user = get_current_user()
    return {
        'current_user': user,
        'csrf_token': session.get('csrf_token'),
        'currency_symbol': user['currency'] if user else '₹',
        'now': datetime.now()
    }

# Allowed Constants
EXPENSE_CATEGORIES = [
    'Food', 'Rent', 'Transport', 'Shopping', 'Education',
    'Bills', 'Healthcare', 'Entertainment', 'Subscriptions', 'Travel', 'Other'
]

PAYMENT_METHODS = ['Cash', 'UPI', 'Debit Card', 'Credit Card']

INCOME_SOURCES = [
    'Salary', 'Freelance', 'Investments', 'Rental', 'Bonus', 'Gifts', 'Other'
]

GOAL_ICONS = {
    'bike': 'bike',
    'laptop': 'laptop',
    'shield-check': 'shield-check',
    'home': 'home',
    'car': 'car',
    'plane': 'plane',
    'target': 'target'
}


# --- Calculation Helper Utilities ---

def get_month_days_info(year, month):
    """Returns total days in month and remaining days from today."""
    today = date.today()
    _, total_days = monthrange(year, month)
    if today.year == year and today.month == month:
        remaining_days = total_days - today.day + 1
    elif (today.year, today.month) > (year, month):
        remaining_days = 0
    else:
        remaining_days = total_days
    return total_days, max(0, remaining_days)

def calculate_goal_metrics(goal):
    """Calculates progress %, remaining, months remaining, and suggested monthly contribution."""
    target = float(goal['target_amount'])
    current = float(goal['current_amount'])
    remaining = max(0.0, target - current)
    progress_pct = min(100.0, round((current / target * 100) if target > 0 else 0, 1))

    # Deadline & months calculation
    today = date.today()
    try:
        deadline_date = datetime.strptime(goal['deadline'], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        deadline_date = today + timedelta(days=180)

    days_left = (deadline_date - today).days
    # Compute months remaining (at least 1 if deadline is in the future)
    months_left = max(1, math.ceil(days_left / 30.44)) if days_left > 0 else 1

    suggested_monthly = round(remaining / months_left, 2) if remaining > 0 else 0.0

    return {
        'remaining': remaining,
        'progress_pct': progress_pct,
        'days_left': max(0, days_left),
        'months_left': months_left,
        'suggested_monthly': suggested_monthly,
        'is_overdue': days_left < 0 and remaining > 0
    }


# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        login_input = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '')

        if not login_input or not password:
            flash('Please enter both username/email and password.', 'danger')
            return render_template('auth/login.html')

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (login_input, login_input.lower())
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f"Welcome back, {user['username']}!", 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username/email or password.', 'danger')

    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        currency = request.form.get('currency', '₹').strip()

        if not username or len(username) < 3:
            flash('Username must be at least 3 characters.', 'danger')
            return render_template('auth/register.html')

        if not email or '@' not in email:
            flash('Please enter a valid email address.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')

        conn = get_db_connection()
        try:
            password_hash = generate_password_hash(password)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, currency)
                VALUES (?, ?, ?, ?)
            """, (username, email, password_hash, currency))
            conn.commit()
            new_user_id = cursor.lastrowid
            session['user_id'] = new_user_id
            session['username'] = username

            # Initialize a default monthly budget for new user
            current_month_str = date.today().strftime('%Y-%m')
            cursor.execute("""
                INSERT INTO budgets (user_id, month_year, total_budget)
                VALUES (?, ?, 50000.0)
            """, (new_user_id, current_month_str))
            conn.commit()
            conn.close()

            flash('Registration successful! Welcome to SmartMoney.', 'success')
            return redirect(url_for('dashboard'))
        except sqlite3.IntegrityError:
            conn.close()
            flash('Username or email is already registered.', 'danger')

    return render_template('auth/register.html')

@app.route('/demo-login')
def demo_login():
    """1-Click instant login with rich seeded data for evaluation."""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = 'alex'").fetchone()
    conn.close()

    if not user:
        seed_demo_data()
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = 'alex'").fetchone()
        conn.close()

    session['user_id'] = user['id']
    session['username'] = user['username']
    flash('Logged in with Demo Account (Alex). Explore all features!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('login'))


# ==========================================
# DASHBOARD (OVERVIEW)
# ==========================================

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    user = get_current_user()
    today = date.today()
    current_month_str = today.strftime('%Y-%m')

    # Date filter parsing: 'today', 'this_week', 'this_month', 'custom'
    filter_type = request.args.get('period', 'this_month')
    custom_start = request.args.get('start_date')
    custom_end = request.args.get('end_date')

    if filter_type == 'today':
        start_date = today.strftime('%Y-%m-%d')
        end_date = start_date
    elif filter_type == 'this_week':
        start_of_week = today - timedelta(days=today.weekday())
        start_date = start_of_week.strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
    elif filter_type == 'custom' and custom_start and custom_end:
        start_date = custom_start
        end_date = custom_end
    else:  # default 'this_month'
        filter_type = 'this_month'
        start_date = f"{current_month_str}-01"
        _, last_day = monthrange(today.year, today.month)
        end_date = f"{current_month_str}-{last_day:02d}"

    conn = get_db_connection()

    # 1. Monthly Income (Current Month full month view for high level stats)
    income_curr_month = conn.execute("""
        SELECT 
            SUM(CASE WHEN status = 'received' THEN amount ELSE 0 END) as total_received,
            SUM(CASE WHEN status = 'expected' THEN amount ELSE 0 END) as total_expected
        FROM incomes
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
    """, (user_id, current_month_str)).fetchone()

    total_monthly_income = float(income_curr_month['total_received'] or 0.0)
    total_expected_income = float(income_curr_month['total_expected'] or 0.0)

    # 2. Monthly Expenses (Current Month full)
    expenses_curr_month = conn.execute("""
        SELECT SUM(amount) as total_expenses
        FROM expenses
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
    """, (user_id, current_month_str)).fetchone()
    total_monthly_expenses = float(expenses_curr_month['total_expenses'] or 0.0)

    # 3. Filtered Expenses for Selected Period
    expenses_filtered = conn.execute("""
        SELECT SUM(amount) as total
        FROM expenses
        WHERE user_id = ? AND date BETWEEN ? AND ?
    """, (user_id, start_date, end_date)).fetchone()
    period_expenses = float(expenses_filtered['total'] or 0.0)

    # 4. Filtered Incomes for Selected Period
    incomes_filtered = conn.execute("""
        SELECT SUM(amount) as total
        FROM incomes
        WHERE user_id = ? AND status = 'received' AND date BETWEEN ? AND ?
    """, (user_id, start_date, end_date)).fetchone()
    period_income = float(incomes_filtered['total'] or 0.0)

    # 5. Total Savings across all Active Savings Goals
    savings_query = conn.execute("""
        SELECT SUM(current_amount) as total_savings
        FROM savings_goals
        WHERE user_id = ?
    """, (user_id,)).fetchone()
    total_savings = float(savings_query['total_savings'] or 0.0)

    # 6. Current Month Contributions to Savings Goals (to avoid double-counting)
    curr_month_contributions = conn.execute("""
        SELECT SUM(amount) as total
        FROM savings_contributions
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
    """, (user_id, current_month_str)).fetchone()
    monthly_savings_contributed = float(curr_month_contributions['total'] or 0.0)

    # Available Balance = Total Received Income (this month) - Total Expenses (this month) - Savings Contributed (this month)
    available_balance = total_monthly_income - total_monthly_expenses - monthly_savings_contributed

    # Monthly Savings Rate (%)
    savings_rate = round((monthly_savings_contributed / total_monthly_income * 100), 1) if total_monthly_income > 0 else 0.0
    net_surplus_rate = round(((total_monthly_income - total_monthly_expenses) / total_monthly_income * 100), 1) if total_monthly_income > 0 else 0.0

    # 7. Budget & Daily Spending Limit Calculation
    budget_row = conn.execute("""
        SELECT total_budget FROM budgets
        WHERE user_id = ? AND month_year = ?
    """, (user_id, current_month_str)).fetchone()

    monthly_budget = float(budget_row['total_budget']) if budget_row else 0.0
    remaining_budget = max(0.0, monthly_budget - total_monthly_expenses) if monthly_budget > 0 else max(0.0, available_balance)

    _, remaining_days = get_month_days_info(today.year, today.month)
    daily_spending_limit = round(remaining_budget / remaining_days, 2) if remaining_days > 0 else 0.0

    # 8. All Three Active Savings Goals
    goals_rows = conn.execute("""
        SELECT * FROM savings_goals
        WHERE user_id = ? AND is_completed = 0
        ORDER BY deadline ASC
        LIMIT 3
    """, (user_id,)).fetchall()

    processed_goals = []
    for g in goals_rows:
        metrics = calculate_goal_metrics(g)
        goal_dict = dict(g)
        goal_dict.update(metrics)
        processed_goals.append(goal_dict)

    # 9. Recent Transactions (combined latest 8 incomes & expenses)
    recent_expenses = conn.execute("""
        SELECT id, amount, category, date, description, payment_method, 'expense' as type
        FROM expenses
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        LIMIT 6
    """, (user_id,)).fetchall()

    recent_incomes = conn.execute("""
        SELECT id, amount, source as category, date, notes as description, status as payment_method, 'income' as type
        FROM incomes
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        LIMIT 4
    """, (user_id,)).fetchall()

    # Combine & sort recent transactions
    recent_transactions = sorted(
        [dict(r) for r in recent_expenses] + [dict(r) for r in recent_incomes],
        key=lambda x: x['date'],
        reverse=True
    )[:8]

    # 10. Category Breakdown for selected period (Chart Data)
    cat_breakdown = conn.execute("""
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE user_id = ? AND date BETWEEN ? AND ?
        GROUP BY category
        ORDER BY total DESC
    """, (user_id, start_date, end_date)).fetchall()

    chart_categories = [row['category'] for row in cat_breakdown]
    chart_category_totals = [float(row['total']) for row in cat_breakdown]

    # 11. Last 6 Months Income vs Expense (Chart Data)
    months_labels = []
    incomes_trend = []
    expenses_trend = []

    for i in range(5, -1, -1):
        # Calculate target month
        calc_date = today.replace(day=1) - timedelta(days=i * 28)
        target_month = calc_date.strftime('%Y-%m')
        month_label = calc_date.strftime('%b %Y')
        months_labels.append(month_label)

        m_inc = conn.execute("""
            SELECT SUM(amount) as total FROM incomes
            WHERE user_id = ? AND status = 'received' AND strftime('%Y-%m', date) = ?
        """, (user_id, target_month)).fetchone()
        incomes_trend.append(float(m_inc['total'] or 0.0))

        m_exp = conn.execute("""
            SELECT SUM(amount) as total FROM expenses
            WHERE user_id = ? AND strftime('%Y-%m', date) = ?
        """, (user_id, target_month)).fetchone()
        expenses_trend.append(float(m_exp['total'] or 0.0))

    conn.close()

    return render_template(
        'dashboard.html',
        total_monthly_income=total_monthly_income,
        total_expected_income=total_expected_income,
        total_monthly_expenses=total_monthly_expenses,
        available_balance=available_balance,
        total_savings=total_savings,
        monthly_savings_contributed=monthly_savings_contributed,
        savings_rate=savings_rate,
        net_surplus_rate=net_surplus_rate,
        daily_spending_limit=daily_spending_limit,
        monthly_budget=monthly_budget,
        remaining_budget=remaining_budget,
        remaining_days=remaining_days,
        goals=processed_goals,
        recent_transactions=recent_transactions,
        filter_type=filter_type,
        start_date=start_date,
        end_date=end_date,
        period_expenses=period_expenses,
        period_income=period_income,
        chart_categories=chart_categories,
        chart_category_totals=chart_category_totals,
        months_labels=months_labels,
        incomes_trend=incomes_trend,
        expenses_trend=expenses_trend
    )


# ==========================================
# INCOME MANAGEMENT
# ==========================================

@app.route('/incomes')
@login_required
def incomes_page():
    user_id = session['user_id']
    today = date.today()
    selected_month = request.args.get('month', today.strftime('%Y-%m'))
    status_filter = request.args.get('status', 'all')

    conn = get_db_connection()

    # Query incomes with optional status filter
    query = """
        SELECT * FROM incomes
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
    """
    params = [user_id, selected_month]

    if status_filter in ('received', 'expected'):
        query += " AND status = ?"
        params.append(status_filter)

    query += " ORDER BY date DESC, id DESC"
    incomes = conn.execute(query, params).fetchall()

    # Month Summary Stats
    summary = conn.execute("""
        SELECT 
            SUM(CASE WHEN status = 'received' THEN amount ELSE 0 END) as total_received,
            SUM(CASE WHEN status = 'expected' THEN amount ELSE 0 END) as total_expected,
            COUNT(*) as total_count,
            AVG(CASE WHEN status = 'received' THEN amount ELSE NULL END) as avg_income
        FROM incomes
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
    """, (user_id, selected_month)).fetchone()

    # List of all available distinct months for user's incomes
    month_options = conn.execute("""
        SELECT DISTINCT strftime('%Y-%m', date) as m
        FROM incomes
        WHERE user_id = ?
        ORDER BY m DESC
    """, (user_id,)).fetchall()
    month_options = [r['m'] for r in month_options if r['m']]
    if selected_month not in month_options:
        month_options.insert(0, selected_month)

    conn.close()

    return render_template(
        'incomes.html',
        incomes=incomes,
        selected_month=selected_month,
        status_filter=status_filter,
        summary=summary,
        month_options=month_options,
        income_sources=INCOME_SOURCES
    )

@app.route('/api/incomes/add', methods=['POST'])
@login_required
def add_income():
    user_id = session['user_id']
    try:
        amount = float(request.form.get('amount', 0))
        source = request.form.get('source', '').strip()
        date_val = request.form.get('date', '').strip()
        status = request.form.get('status', 'received').strip()
        notes = request.form.get('notes', '').strip()

        if amount <= 0:
            return jsonify({'success': False, 'message': 'Amount must be greater than zero.'}), 400
        if not source:
            return jsonify({'success': False, 'message': 'Source is required.'}), 400
        if not date_val:
            return jsonify({'success': False, 'message': 'Date is required.'}), 400
        if status not in ('received', 'expected'):
            status = 'received'

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO incomes (user_id, amount, source, date, status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, amount, source, date_val, status, notes))
        conn.commit()
        conn.close()

        flash('Income record added successfully.', 'success')
        return jsonify({'success': True, 'message': 'Income added successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/incomes/edit/<int:income_id>', methods=['POST'])
@login_required
def edit_income(income_id):
    user_id = session['user_id']
    try:
        amount = float(request.form.get('amount', 0))
        source = request.form.get('source', '').strip()
        date_val = request.form.get('date', '').strip()
        status = request.form.get('status', 'received').strip()
        notes = request.form.get('notes', '').strip()

        if amount <= 0 or not source or not date_val:
            return jsonify({'success': False, 'message': 'Invalid input fields.'}), 400

        conn = get_db_connection()
        result = conn.execute("""
            UPDATE incomes
            SET amount = ?, source = ?, date = ?, status = ?, notes = ?
            WHERE id = ? AND user_id = ?
        """, (amount, source, date_val, status, notes, income_id, user_id))
        conn.commit()
        conn.close()

        if result.rowcount == 0:
            return jsonify({'success': False, 'message': 'Income not found or unauthorized.'}), 404

        flash('Income record updated successfully.', 'success')
        return jsonify({'success': True, 'message': 'Income updated successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/incomes/delete/<int:income_id>', methods=['POST'])
@login_required
def delete_income(income_id):
    user_id = session['user_id']
    conn = get_db_connection()
    result = conn.execute("DELETE FROM incomes WHERE id = ? AND user_id = ?", (income_id, user_id))
    conn.commit()
    conn.close()

    if result.rowcount == 0:
        return jsonify({'success': False, 'message': 'Income not found or unauthorized.'}), 404

    flash('Income record deleted successfully.', 'success')
    return jsonify({'success': True, 'message': 'Income deleted successfully.'})

@app.route('/api/incomes/toggle-status/<int:income_id>', methods=['POST'])
@login_required
def toggle_income_status(income_id):
    user_id = session['user_id']
    conn = get_db_connection()
    inc = conn.execute("SELECT status FROM incomes WHERE id = ? AND user_id = ?", (income_id, user_id)).fetchone()
    if not inc:
        conn.close()
        return jsonify({'success': False, 'message': 'Income not found.'}), 404

    new_status = 'expected' if inc['status'] == 'received' else 'received'
    conn.execute("UPDATE incomes SET status = ? WHERE id = ? AND user_id = ?", (new_status, income_id, user_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'new_status': new_status, 'message': f'Status switched to {new_status}.'})


# ==========================================
# EXPENSE MANAGEMENT
# ==========================================

@app.route('/expenses')
@login_required
def expenses_page():
    user_id = session['user_id']
    today = date.today()
    current_month_str = today.strftime('%Y-%m')

    conn = get_db_connection()

    # Summary metrics for current month
    summary = conn.execute("""
        SELECT 
            SUM(amount) as total_month,
            COUNT(*) as count_month,
            AVG(amount) as avg_expense
        FROM expenses
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
    """, (user_id, current_month_str)).fetchone()

    # Category breakdown for the month
    cat_summary = conn.execute("""
        SELECT category, SUM(amount) as total, COUNT(*) as count
        FROM expenses
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
        GROUP BY category
        ORDER BY total DESC
    """, (user_id, current_month_str)).fetchall()

    conn.close()

    return render_template(
        'expenses.html',
        summary=summary,
        cat_summary=cat_summary,
        categories=EXPENSE_CATEGORIES,
        payment_methods=PAYMENT_METHODS,
        current_date=today.strftime('%Y-%m-%d')
    )

@app.route('/api/expenses', methods=['GET'])
@login_required
def get_expenses_api():
    user_id = session['user_id']
    search = request.args.get('search', '').strip()
    category = request.args.get('category', 'all')
    payment_method = request.args.get('payment_method', 'all')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    sort_by = request.args.get('sort_by', 'date_desc')

    query = "SELECT * FROM expenses WHERE user_id = ?"
    params = [user_id]

    if search:
        query += " AND (description LIKE ? OR category LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if category and category != 'all':
        query += " AND category = ?"
        params.append(category)

    if payment_method and payment_method != 'all':
        query += " AND payment_method = ?"
        params.append(payment_method)

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    # Sorting options
    if sort_by == 'date_asc':
        query += " ORDER BY date ASC, id ASC"
    elif sort_by == 'amount_desc':
        query += " ORDER BY amount DESC"
    elif sort_by == 'amount_asc':
        query += " ORDER BY amount ASC"
    else:  # default date_desc
        query += " ORDER BY date DESC, id DESC"

    conn = get_db_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()

    expenses = [dict(r) for r in rows]
    total_amount = sum(e['amount'] for e in expenses)

    return jsonify({
        'success': True,
        'expenses': expenses,
        'count': len(expenses),
        'total_amount': total_amount
    })

@app.route('/api/expenses/add', methods=['POST'])
@login_required
def add_expense():
    user_id = session['user_id']
    try:
        amount = float(request.form.get('amount', 0))
        category = request.form.get('category', '').strip()
        date_val = request.form.get('date', '').strip()
        payment_method = request.form.get('payment_method', 'UPI').strip()
        description = request.form.get('description', '').strip()

        if amount <= 0:
            return jsonify({'success': False, 'message': 'Amount must be greater than zero.'}), 400
        if category not in EXPENSE_CATEGORIES:
            category = 'Other'
        if payment_method not in PAYMENT_METHODS:
            payment_method = 'UPI'
        if not date_val:
            date_val = date.today().strftime('%Y-%m-%d')
        if not description:
            description = f"{category} expense"

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO expenses (user_id, amount, category, date, payment_method, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, amount, category, date_val, payment_method, description))
        conn.commit()
        conn.close()

        flash('Expense recorded successfully.', 'success')
        return jsonify({'success': True, 'message': 'Expense recorded successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/expenses/edit/<int:expense_id>', methods=['POST'])
@login_required
def edit_expense(expense_id):
    user_id = session['user_id']
    try:
        amount = float(request.form.get('amount', 0))
        category = request.form.get('category', '').strip()
        date_val = request.form.get('date', '').strip()
        payment_method = request.form.get('payment_method', 'UPI').strip()
        description = request.form.get('description', '').strip()

        if amount <= 0 or not category or not date_val or not description:
            return jsonify({'success': False, 'message': 'All fields are required and amount must be positive.'}), 400

        conn = get_db_connection()
        result = conn.execute("""
            UPDATE expenses
            SET amount = ?, category = ?, date = ?, payment_method = ?, description = ?
            WHERE id = ? AND user_id = ?
        """, (amount, category, date_val, payment_method, description, expense_id, user_id))
        conn.commit()
        conn.close()

        if result.rowcount == 0:
            return jsonify({'success': False, 'message': 'Expense record not found.'}), 404

        flash('Expense record updated successfully.', 'success')
        return jsonify({'success': True, 'message': 'Expense updated successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/expenses/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    user_id = session['user_id']
    conn = get_db_connection()
    result = conn.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id))
    conn.commit()
    conn.close()

    if result.rowcount == 0:
        return jsonify({'success': False, 'message': 'Expense record not found.'}), 404

    flash('Expense record deleted successfully.', 'success')
    return jsonify({'success': True, 'message': 'Expense deleted successfully.'})


# ==========================================
# THE THREE SAVINGS GOALS
# ==========================================

@app.route('/goals')
@login_required
def goals_page():
    user_id = session['user_id']
    conn = get_db_connection()

    # Active goals (enforce exactly max 3 active goals)
    active_goals_rows = conn.execute("""
        SELECT * FROM savings_goals
        WHERE user_id = ? AND is_completed = 0
        ORDER BY deadline ASC
    """, (user_id,)).fetchall()

    active_goals = []
    total_savings_accumulated = 0.0
    total_target_needed = 0.0

    for g in active_goals_rows:
        metrics = calculate_goal_metrics(g)
        goal_dict = dict(g)
        goal_dict.update(metrics)
        active_goals.append(goal_dict)
        total_savings_accumulated += float(g['current_amount'])
        total_target_needed += float(g['target_amount'])

    # Completed goals archive
    completed_goals_rows = conn.execute("""
        SELECT * FROM savings_goals
        WHERE user_id = ? AND is_completed = 1
        ORDER BY created_at DESC
    """, (user_id,)).fetchall()

    completed_goals = [dict(g) for g in completed_goals_rows]

    # Recent contributions history
    contributions = conn.execute("""
        SELECT sc.*, sg.name as goal_name
        FROM savings_contributions sc
        JOIN savings_goals sg ON sc.goal_id = sg.id
        WHERE sc.user_id = ?
        ORDER BY sc.date DESC, sc.id DESC
        LIMIT 10
    """, (user_id,)).fetchall()

    conn.close()

    # Calculate overall savings progress
    overall_progress = round((total_savings_accumulated / total_target_needed * 100), 1) if total_target_needed > 0 else 0.0

    return render_template(
        'goals.html',
        active_goals=active_goals,
        active_count=len(active_goals),
        completed_goals=completed_goals,
        contributions=contributions,
        total_savings_accumulated=total_savings_accumulated,
        total_target_needed=total_target_needed,
        overall_progress=overall_progress,
        goal_icons=GOAL_ICONS,
        today_date=date.today().strftime('%Y-%m-%d')
    )

@app.route('/api/goals/add', methods=['POST'])
@login_required
def add_goal():
    user_id = session['user_id']
    conn = get_db_connection()

    # Strictly check that user has LESS than 3 active goals
    count_row = conn.execute("""
        SELECT COUNT(*) as count FROM savings_goals
        WHERE user_id = ? AND is_completed = 0
    """, (user_id,)).fetchone()

    if count_row['count'] >= 3:
        conn.close()
        return jsonify({
            'success': False,
            'message': 'Limit reached: SmartMoney allows up to 3 active savings goals for focused discipline. Complete or delete an existing goal to create a new one.'
        }), 400

    try:
        name = request.form.get('name', '').strip()
        target_amount = float(request.form.get('target_amount', 0))
        initial_savings = float(request.form.get('initial_savings', 0))
        deadline = request.form.get('deadline', '').strip()
        category_icon = request.form.get('category_icon', 'target').strip()

        if not name:
            conn.close()
            return jsonify({'success': False, 'message': 'Goal name is required.'}), 400
        if target_amount <= 0:
            conn.close()
            return jsonify({'success': False, 'message': 'Target amount must be greater than zero.'}), 400
        if not deadline:
            conn.close()
            return jsonify({'success': False, 'message': 'Target deadline is required.'}), 400

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO savings_goals (user_id, name, target_amount, current_amount, deadline, category_icon, is_completed)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (user_id, name, target_amount, initial_savings, deadline, category_icon))
        goal_id = cursor.lastrowid

        if initial_savings > 0:
            cursor.execute("""
                INSERT INTO savings_contributions (goal_id, user_id, amount, date, notes)
                VALUES (?, ?, ?, ?, 'Initial seed deposit')
            """, (goal_id, user_id, initial_savings, date.today().strftime('%Y-%m-%d')))

        conn.commit()
        conn.close()

        flash(f"Goal '{name}' created successfully!", 'success')
        return jsonify({'success': True, 'message': 'Savings goal created successfully.'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/goals/edit/<int:goal_id>', methods=['POST'])
@login_required
def edit_goal(goal_id):
    user_id = session['user_id']
    try:
        name = request.form.get('name', '').strip()
        target_amount = float(request.form.get('target_amount', 0))
        deadline = request.form.get('deadline', '').strip()
        category_icon = request.form.get('category_icon', 'target').strip()

        if not name or target_amount <= 0 or not deadline:
            return jsonify({'success': False, 'message': 'Please provide valid goal details.'}), 400

        conn = get_db_connection()
        result = conn.execute("""
            UPDATE savings_goals
            SET name = ?, target_amount = ?, deadline = ?, category_icon = ?
            WHERE id = ? AND user_id = ?
        """, (name, target_amount, deadline, category_icon, goal_id, user_id))
        conn.commit()
        conn.close()

        if result.rowcount == 0:
            return jsonify({'success': False, 'message': 'Goal not found or unauthorized.'}), 404

        flash(f"Goal '{name}' updated successfully.", 'success')
        return jsonify({'success': True, 'message': 'Savings goal updated successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/goals/contribute/<int:goal_id>', methods=['POST'])
@login_required
def contribute_to_goal(goal_id):
    """
    Adds savings deposit to a goal.
    Does NOT count as an expense, keeping tracked money accurate and avoiding double-counting!
    """
    user_id = session['user_id']
    try:
        amount = float(request.form.get('amount', 0))
        date_val = request.form.get('date', date.today().strftime('%Y-%m-%d')).strip()
        notes = request.form.get('notes', 'Savings deposit').strip()

        if amount <= 0:
            return jsonify({'success': False, 'message': 'Contribution amount must be greater than zero.'}), 400

        conn = get_db_connection()
        goal = conn.execute("SELECT * FROM savings_goals WHERE id = ? AND user_id = ?", (goal_id, user_id)).fetchone()
        if not goal:
            conn.close()
            return jsonify({'success': False, 'message': 'Goal not found.'}), 404

        cursor = conn.cursor()
        # 1. Record contribution in savings_contributions
        cursor.execute("""
            INSERT INTO savings_contributions (goal_id, user_id, amount, date, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (goal_id, user_id, amount, date_val, notes))

        # 2. Update goal's current amount
        new_amount = float(goal['current_amount']) + amount
        is_completed = 1 if new_amount >= float(goal['target_amount']) else 0

        cursor.execute("""
            UPDATE savings_goals
            SET current_amount = ?, is_completed = ?
            WHERE id = ?
        """, (new_amount, is_completed, goal_id))

        conn.commit()
        conn.close()

        status_msg = f"Contributed {amount} to '{goal['name']}'!"
        if is_completed:
            status_msg += " Congratulations, you achieved this goal!"
        flash(status_msg, 'success')
        return jsonify({'success': True, 'message': status_msg, 'new_amount': new_amount, 'is_completed': bool(is_completed)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/goals/delete/<int:goal_id>', methods=['POST'])
@login_required
def delete_goal(goal_id):
    user_id = session['user_id']
    conn = get_db_connection()
    result = conn.execute("DELETE FROM savings_goals WHERE id = ? AND user_id = ?", (goal_id, user_id))
    conn.commit()
    conn.close()

    if result.rowcount == 0:
        return jsonify({'success': False, 'message': 'Goal not found.'}), 404

    flash('Savings goal deleted successfully.', 'success')
    return jsonify({'success': True, 'message': 'Goal deleted successfully.'})

@app.route('/api/goals/toggle-complete/<int:goal_id>', methods=['POST'])
@login_required
def toggle_goal_complete(goal_id):
    user_id = session['user_id']
    conn = get_db_connection()
    goal = conn.execute("SELECT * FROM savings_goals WHERE id = ? AND user_id = ?", (goal_id, user_id)).fetchone()
    if not goal:
        conn.close()
        return jsonify({'success': False, 'message': 'Goal not found.'}), 404

    new_state = 0 if goal['is_completed'] else 1
    conn.execute("UPDATE savings_goals SET is_completed = ? WHERE id = ? AND user_id = ?", (new_state, goal_id, user_id))
    conn.commit()
    conn.close()

    status_str = "completed and archived" if new_state else "reactivated"
    flash(f"Goal '{goal['name']}' marked as {status_str}.", 'success')
    return jsonify({'success': True, 'is_completed': bool(new_state), 'message': f'Goal {status_str}.'})


# ==========================================
# BUDGET MANAGEMENT
# ==========================================

@app.route('/budgets')
@login_required
def budgets_page():
    user_id = session['user_id']
    today = date.today()
    selected_month = request.args.get('month', today.strftime('%Y-%m'))

    conn = get_db_connection()

    # 1. Total monthly budget
    budget_row = conn.execute("""
        SELECT total_budget FROM budgets
        WHERE user_id = ? AND month_year = ?
    """, (user_id, selected_month)).fetchone()
    total_budget = float(budget_row['total_budget']) if budget_row else 0.0

    # 2. Total spending for the month
    spent_row = conn.execute("""
        SELECT SUM(amount) as total FROM expenses
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
    """, (user_id, selected_month)).fetchone()
    total_spent = float(spent_row['total'] or 0.0)

    # 3. Overall budget calculations
    budget_remaining = max(0.0, total_budget - total_spent)
    overall_progress = round((total_spent / total_budget * 100), 1) if total_budget > 0 else 0.0
    is_overall_over = total_spent > total_budget if total_budget > 0 else False

    # Suggested daily spending limit
    year, month = map(int, selected_month.split('-'))
    total_days, remaining_days = get_month_days_info(year, month)
    suggested_daily_limit = round(budget_remaining / remaining_days, 2) if remaining_days > 0 else 0.0

    # 4. Category-specific budgets vs actual spending
    cat_budgets_rows = conn.execute("""
        SELECT * FROM category_budgets
        WHERE user_id = ? AND month_year = ?
    """, (user_id, selected_month)).fetchall()
    cat_budgets_map = {r['category']: float(r['amount']) for r in cat_budgets_rows}

    # Category actual expenses
    cat_spent_rows = conn.execute("""
        SELECT category, SUM(amount) as total FROM expenses
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
        GROUP BY category
    """, (user_id, selected_month)).fetchall()
    cat_spent_map = {r['category']: float(r['total']) for r in cat_spent_rows}

    category_reports = []
    for cat in EXPENSE_CATEGORIES:
        budgeted = cat_budgets_map.get(cat, 0.0)
        spent = cat_spent_map.get(cat, 0.0)
        rem = max(0.0, budgeted - spent) if budgeted > 0 else 0.0
        pct = round((spent / budgeted * 100), 1) if budgeted > 0 else 0.0
        status = 'danger' if (budgeted > 0 and spent > budgeted) else ('warning' if pct >= 80 else 'success')

        category_reports.append({
            'category': cat,
            'budgeted': budgeted,
            'spent': spent,
            'remaining': rem,
            'percentage': pct,
            'status': status,
            'has_budget': budgeted > 0,
            'is_over': budgeted > 0 and spent > budgeted
        })

    # Available months for selector
    months_query = conn.execute("""
        SELECT DISTINCT strftime('%Y-%m', date) as m FROM expenses WHERE user_id = ?
        UNION
        SELECT DISTINCT month_year as m FROM budgets WHERE user_id = ?
        ORDER BY m DESC
    """, (user_id, user_id)).fetchall()
    available_months = [r['m'] for r in months_query if r['m']]
    if selected_month not in available_months:
        available_months.insert(0, selected_month)

    conn.close()

    return render_template(
        'budgets.html',
        selected_month=selected_month,
        available_months=available_months,
        total_budget=total_budget,
        total_spent=total_spent,
        budget_remaining=budget_remaining,
        overall_progress=overall_progress,
        is_overall_over=is_overall_over,
        remaining_days=remaining_days,
        total_days=total_days,
        suggested_daily_limit=suggested_daily_limit,
        category_reports=category_reports,
        expense_categories=EXPENSE_CATEGORIES
    )

@app.route('/api/budgets/set-monthly', methods=['POST'])
@login_required
def set_monthly_budget():
    user_id = session['user_id']
    try:
        month_year = request.form.get('month_year', date.today().strftime('%Y-%m')).strip()
        total_budget = float(request.form.get('total_budget', 0))

        if total_budget < 0:
            return jsonify({'success': False, 'message': 'Budget must be zero or positive.'}), 400

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO budgets (user_id, month_year, total_budget, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, month_year) DO UPDATE SET
                total_budget = excluded.total_budget,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, month_year, total_budget))
        conn.commit()
        conn.close()

        flash(f"Monthly budget for {month_year} updated to {total_budget}.", 'success')
        return jsonify({'success': True, 'message': 'Monthly budget updated successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/budgets/set-category', methods=['POST'])
@login_required
def set_category_budget():
    user_id = session['user_id']
    try:
        month_year = request.form.get('month_year', date.today().strftime('%Y-%m')).strip()
        category = request.form.get('category', '').strip()
        amount = float(request.form.get('amount', 0))

        if category not in EXPENSE_CATEGORIES:
            return jsonify({'success': False, 'message': 'Invalid expense category.'}), 400
        if amount < 0:
            return jsonify({'success': False, 'message': 'Category budget cannot be negative.'}), 400

        conn = get_db_connection()
        if amount == 0:
            conn.execute("""
                DELETE FROM category_budgets
                WHERE user_id = ? AND month_year = ? AND category = ?
            """, (user_id, month_year, category))
        else:
            conn.execute("""
                INSERT INTO category_budgets (user_id, month_year, category, amount)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, month_year, category) DO UPDATE SET
                    amount = excluded.amount
            """, (user_id, month_year, category, amount))
        conn.commit()
        conn.close()

        flash(f"Budget for '{category}' updated.", 'success')
        return jsonify({'success': True, 'message': 'Category budget saved successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==========================================
# SMART INSIGHTS ENGINE
# ==========================================

def generate_user_insights(user_id):
    """
    Computes algorithmic, data-grounded financial insights:
    - Top spending category
    - Month-to-month category comparisons
    - Budget runway & daily burn rate
    - Savings goal feasibility & required contributions
    - Projected month-end spending
    - Never invents data; clearly separates estimates.
    """
    today = date.today()
    curr_month = today.strftime('%Y-%m')
    first_of_month = today.replace(day=1)
    prev_month_date = first_of_month - timedelta(days=1)
    prev_month = prev_month_date.strftime('%Y-%m')

    conn = get_db_connection()
    user = conn.execute("SELECT currency FROM users WHERE id = ?", (user_id,)).fetchone()
    currency = user['currency'] if user else '₹'

    insights = []

    # 1. Current Month Expenses by Category
    curr_cat_rows = conn.execute("""
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
        GROUP BY category
        ORDER BY total DESC
    """, (user_id, curr_month)).fetchall()
    curr_cat_map = {r['category']: float(r['total']) for r in curr_cat_rows}
    total_curr_expenses = sum(curr_cat_map.values())

    # Previous Month Expenses by Category
    prev_cat_rows = conn.execute("""
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
        GROUP BY category
    """, (user_id, prev_month)).fetchall()
    prev_cat_map = {r['category']: float(r['total']) for r in prev_cat_rows}
    total_prev_expenses = sum(prev_cat_map.values())

    # Insight A: Highest Spending Category
    if curr_cat_rows and total_curr_expenses > 0:
        top_cat = curr_cat_rows[0]['category']
        top_amt = float(curr_cat_rows[0]['total'])
        pct_of_total = round((top_amt / total_curr_expenses) * 100, 1)

        insights.append({
            'type': 'highlight',
            'category': 'Spending Focus',
            'icon': 'pie-chart',
            'title': f"{top_cat} is your highest spending category this month",
            'text': f"You have spent {currency}{top_amt:,.0f} on {top_cat}, representing {pct_of_total}% of your total monthly expenditures.",
            'badge': 'Top Category',
            'severity': 'info'
        })

    # Insight B: Month-over-Month Category Variance
    for cat, curr_amt in curr_cat_map.items():
        if cat in prev_cat_map:
            prev_amt = prev_cat_map[cat]
            diff = curr_amt - prev_amt
            if abs(diff) >= 500:  # significant change threshold
                if diff > 0:
                    insights.append({
                        'type': 'variance',
                        'category': 'Monthly Comparison',
                        'icon': 'trending-up',
                        'title': f"Higher spending in {cat}",
                        'text': f"You spent {currency}{abs(diff):,.0f} more on {cat} this month compared to last month ({currency}{curr_amt:,.0f} vs {currency}{prev_amt:,.0f}).",
                        'badge': f"+{currency}{abs(diff):,.0f}",
                        'severity': 'warning'
                    })
                else:
                    insights.append({
                        'type': 'variance',
                        'category': 'Savings Win',
                        'icon': 'trending-down',
                        'title': f"Reduced spending in {cat}",
                        'text': f"Great job! You cut spending on {cat} by {currency}{abs(diff):,.0f} compared to last month.",
                        'badge': f"-{currency}{abs(diff):,.0f}",
                        'severity': 'success'
                    })
                break  # keep most notable variance

    # Insight C: Budget Runway & Suggested Daily Limit
    budget_row = conn.execute("SELECT total_budget FROM budgets WHERE user_id = ? AND month_year = ?", (user_id, curr_month)).fetchone()
    total_budget = float(budget_row['total_budget']) if budget_row else 0.0

    total_days, remaining_days = get_month_days_info(today.year, today.month)
    days_elapsed = max(1, today.day)

    if total_budget > 0:
        remaining_budget = total_budget - total_curr_expenses
        if remaining_budget > 0 and remaining_days > 0:
            suggested_daily = remaining_budget / remaining_days
            insights.append({
                'type': 'budget',
                'category': 'Budget Control',
                'icon': 'wallet',
                'title': f"You have {currency}{remaining_budget:,.0f} left in your monthly budget",
                'text': f"With {remaining_days} days left this month, your suggested daily spending limit is {currency}{suggested_daily:,.0f}/day to stay on track.",
                'badge': f"{remaining_days} days left",
                'severity': 'success' if suggested_daily > 500 else 'warning'
            })
        elif remaining_budget <= 0:
            over_by = abs(remaining_budget)
            insights.append({
                'type': 'budget',
                'category': 'Budget Alert',
                'icon': 'alert-triangle',
                'title': f"Monthly budget exceeded by {currency}{over_by:,.0f}",
                'text': f"You have reached 100% of your {currency}{total_budget:,.0f} budget. Consider curbing non-essential spending for the remaining {remaining_days} days.",
                'badge': 'Over Budget',
                'severity': 'danger'
            })

    # Insight D: Projected Month-End Spending (Explicitly flagged as estimate)
    if total_curr_expenses > 0 and days_elapsed > 3:
        avg_daily_spent = total_curr_expenses / days_elapsed
        projected_total = avg_daily_spent * total_days

        insights.append({
            'type': 'projection',
            'category': 'Pacing & Forecast',
            'icon': 'activity',
            'title': f"Projected month-end spend: ~{currency}{projected_total:,.0f}",
            'text': f"Based on your daily average burn rate of {currency}{avg_daily_spent:,.0f}/day over the first {days_elapsed} days, estimated total month-end expenditure is {currency}{projected_total:,.0f} (Estimate).",
            'badge': 'Estimate',
            'severity': 'info'
        })

    # Insight E: Savings Goals Feasibility & Recommendations
    goals_rows = conn.execute("""
        SELECT * FROM savings_goals
        WHERE user_id = ? AND is_completed = 0
        ORDER BY deadline ASC
    """, (user_id,)).fetchall()

    for g in goals_rows:
        metrics = calculate_goal_metrics(g)
        if metrics['remaining'] > 0:
            req_monthly = metrics['suggested_monthly']
            insights.append({
                'type': 'goal',
                'category': 'Goal Roadmap',
                'icon': 'target',
                'title': f"Save {currency}{req_monthly:,.0f} monthly for '{g['name']}'",
                'text': f"To reach your target of {currency}{g['target_amount']:,.0f} by {g['deadline']} ({metrics['months_left']} months remaining), maintain a steady contribution of {currency}{req_monthly:,.0f}/month.",
                'badge': f"{metrics['progress_pct']}% achieved",
                'severity': 'info'
            })

    # Insight F: Savings Rate Health
    inc_row = conn.execute("""
        SELECT SUM(amount) as total FROM incomes
        WHERE user_id = ? AND status = 'received' AND strftime('%Y-%m', date) = ?
    """, (user_id, curr_month)).fetchone()
    total_inc = float(inc_row['total'] or 0.0)

    if total_inc > 0:
        surplus = total_inc - total_curr_expenses
        rate = (surplus / total_inc) * 100
        if rate >= 20:
            insights.append({
                'type': 'health',
                'category': 'Financial Health',
                'icon': 'award',
                'title': f"Excellent {rate:.1f}% monthly savings rate",
                'text': f"You are retaining {currency}{surplus:,.0f} of your {currency}{total_inc:,.0f} received income this month. Keep up this fintech discipline!",
                'badge': 'Health: Excellent',
                'severity': 'success'
            })
        elif rate > 0:
            insights.append({
                'type': 'health',
                'category': 'Financial Health',
                'icon': 'info',
                'title': f"Positive cashflow: {currency}{surplus:,.0f} net surplus",
                'text': f"You are currently saving {rate:.1f}% of your monthly income. Increasing this above 20% will accelerate your goal completions.",
                'badge': 'Health: Moderate',
                'severity': 'info'
            })
        else:
            insights.append({
                'type': 'health',
                'category': 'Cashflow Alert',
                'icon': 'alert-circle',
                'title': f"Monthly cashflow deficit of {currency}{abs(surplus):,.0f}",
                'text': f"Your expenses ({currency}{total_curr_expenses:,.0f}) have exceeded received income ({currency}{total_inc:,.0f}) for this month.",
                'badge': 'Deficit',
                'severity': 'danger'
            })

    conn.close()
    return insights

@app.route('/insights')
@login_required
def insights_page():
    user_id = session['user_id']
    insights = generate_user_insights(user_id)
    return render_template('insights.html', insights=insights)

@app.route('/api/insights')
@login_required
def get_insights_api():
    user_id = session['user_id']
    insights = generate_user_insights(user_id)
    return jsonify({'success': True, 'insights': insights})


# ==========================================
# REPORTS & ANALYTICS
# ==========================================

@app.route('/reports')
@login_required
def reports_page():
    user_id = session['user_id']
    today = date.today()
    curr_month = today.strftime('%Y-%m')
    first_of_month = today.replace(day=1)
    prev_month = (first_of_month - timedelta(days=1)).strftime('%Y-%m')

    conn = get_db_connection()

    # 1. Last 12 months Income vs Expense vs Savings trend
    trend_labels = []
    income_data = []
    expense_data = []
    savings_data = []

    for i in range(11, -1, -1):
        target_dt = today.replace(day=1) - timedelta(days=i * 29)
        m_str = target_dt.strftime('%Y-%m')
        trend_labels.append(target_dt.strftime('%b %Y'))

        inc = conn.execute("SELECT SUM(amount) as t FROM incomes WHERE user_id = ? AND status = 'received' AND strftime('%Y-%m', date) = ?", (user_id, m_str)).fetchone()
        exp = conn.execute("SELECT SUM(amount) as t FROM expenses WHERE user_id = ? AND strftime('%Y-%m', date) = ?", (user_id, m_str)).fetchone()
        sav = conn.execute("SELECT SUM(amount) as t FROM savings_contributions WHERE user_id = ? AND strftime('%Y-%m', date) = ?", (user_id, m_str)).fetchone()

        income_data.append(float(inc['t'] or 0.0))
        expense_data.append(float(exp['t'] or 0.0))
        savings_data.append(float(sav['t'] or 0.0))

    # 2. Month-over-Month Category Comparisons (Current vs Previous)
    curr_cat = conn.execute("SELECT category, SUM(amount) as t FROM expenses WHERE user_id = ? AND strftime('%Y-%m', date) = ? GROUP BY category", (user_id, curr_month)).fetchall()
    prev_cat = conn.execute("SELECT category, SUM(amount) as t FROM expenses WHERE user_id = ? AND strftime('%Y-%m', date) = ? GROUP BY category", (user_id, prev_month)).fetchall()

    curr_cat_map = {r['category']: float(r['t']) for r in curr_cat}
    prev_cat_map = {r['category']: float(r['t']) for r in prev_cat}

    all_cats = sorted(list(set(curr_cat_map.keys()) | set(prev_cat_map.keys())))
    mom_comparison = []

    for c in all_cats:
        c_amt = curr_cat_map.get(c, 0.0)
        p_amt = prev_cat_map.get(c, 0.0)
        diff = c_amt - p_amt
        pct_change = round((diff / p_amt * 100), 1) if p_amt > 0 else (100.0 if c_amt > 0 else 0.0)

        mom_comparison.append({
            'category': c,
            'current_month': c_amt,
            'prev_month': p_amt,
            'difference': diff,
            'pct_change': pct_change
        })

    # Sort by current month spend descending
    mom_comparison.sort(key=lambda x: x['current_month'], reverse=True)

    # 3. Payment Methods Breakdown
    pm_rows = conn.execute("""
        SELECT payment_method, SUM(amount) as total, COUNT(*) as count
        FROM expenses
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
        GROUP BY payment_method
        ORDER BY total DESC
    """, (user_id, curr_month)).fetchall()

    conn.close()

    return render_template(
        'reports.html',
        trend_labels=trend_labels,
        income_data=income_data,
        expense_data=expense_data,
        savings_data=savings_data,
        mom_comparison=mom_comparison,
        payment_methods_summary=pm_rows,
        current_month=curr_month,
        prev_month=prev_month
    )

@app.route('/reports/export/expenses')
@login_required
def export_expenses_csv():
    user_id = session['user_id']
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = "SELECT date, category, amount, payment_method, description FROM expenses WHERE user_id = ?"
    params = [user_id]
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    query += " ORDER BY date DESC"

    conn = get_db_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Date', 'Category', 'Amount', 'Payment Method', 'Description'])
    for r in rows:
        cw.writerow([r['date'], r['category'], r['amount'], r['payment_method'], r['description']])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=smartmoney_expenses_{date.today().strftime('%Y%m%d')}.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/reports/export/incomes')
@login_required
def export_incomes_csv():
    user_id = session['user_id']
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT date, source, amount, status, notes
        FROM incomes
        WHERE user_id = ?
        ORDER BY date DESC
    """, (user_id,)).fetchall()
    conn.close()

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Date', 'Source', 'Amount', 'Status', 'Notes'])
    for r in rows:
        cw.writerow([r['date'], r['source'], r['amount'], r['status'], r['notes'] or ''])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=smartmoney_incomes_{date.today().strftime('%Y%m%d')}.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/reports/export/all')
@login_required
def export_all_csv():
    user_id = session['user_id']
    conn = get_db_connection()

    expenses = conn.execute("SELECT date, 'Expense' as type, category, amount, payment_method as method_or_status, description as notes FROM expenses WHERE user_id = ?", (user_id,)).fetchall()
    incomes = conn.execute("SELECT date, 'Income' as type, source as category, amount, status as method_or_status, notes FROM incomes WHERE user_id = ?", (user_id,)).fetchall()
    contributions = conn.execute("""
        SELECT sc.date, 'Savings Transfer' as type, sg.name as category, sc.amount, 'Transfer' as method_or_status, sc.notes
        FROM savings_contributions sc
        JOIN savings_goals sg ON sc.goal_id = sg.id
        WHERE sc.user_id = ?
    """, (user_id,)).fetchall()
    conn.close()

    all_records = sorted(
        [dict(r) for r in expenses] + [dict(r) for r in incomes] + [dict(r) for r in contributions],
        key=lambda x: x['date'],
        reverse=True
    )

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Date', 'Record Type', 'Category/Goal/Source', 'Amount', 'Status/Method', 'Description/Notes'])
    for r in all_records:
        cw.writerow([r['date'], r['type'], r['category'], r['amount'], r['method_or_status'], r['notes'] or ''])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=smartmoney_complete_ledger_{date.today().strftime('%Y%m%d')}.csv"
    output.headers["Content-type"] = "text/csv"
    return output


# ==========================================
# SETTINGS & DATA TOOLS
# ==========================================

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings_page():
    user = get_current_user()
    if request.method == 'POST':
        action = request.form.get('action')
        conn = get_db_connection()

        if action == 'update_profile':
            currency = request.form.get('currency', '₹').strip()
            conn.execute("UPDATE users SET currency = ? WHERE id = ?", (currency, user['id']))
            conn.commit()
            flash('Settings updated successfully.', 'success')

        elif action == 'change_password':
            old_password = request.form.get('old_password', '')
            new_password = request.form.get('new_password', '')
            if not check_password_hash(user['password_hash'], old_password):
                flash('Incorrect current password.', 'danger')
            elif len(new_password) < 6:
                flash('New password must be at least 6 characters.', 'danger')
            else:
                new_hash = generate_password_hash(new_password)
                conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user['id']))
                conn.commit()
                flash('Password changed successfully.', 'success')

        elif action == 'reset_demo_data':
            seed_demo_data(username=user['username'], email=user['email'])
            flash('Demo data refreshed with realistic transactions!', 'success')

        conn.close()
        return redirect(url_for('settings_page'))

    return render_template('settings.html', user=user)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting SmartMoney on http://127.0.0.1:{port}")
    app.run(host='127.0.0.1', port=port, debug=True)
