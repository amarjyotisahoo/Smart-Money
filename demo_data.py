"""
SmartMoney - Demo Data Generator
Creates a demo user with rich, realistic financial transactions across current and previous months,
including 3 active savings goals, budgets, and categorized spending.
"""

import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from database import get_db_connection

def seed_demo_data(username="alex", email="alex@smartmoney.io", password="password123"):
    """Seeds rich demo data for instant evaluation and testing."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check or create demo user
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    existing = cursor.fetchone()

    if existing:
        user_id = existing['id']
        # Clear existing user data for a clean re-seed
        cursor.execute("DELETE FROM incomes WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM budgets WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM category_budgets WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM savings_goals WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM savings_contributions WHERE user_id = ?", (user_id,))
    else:
        password_hash = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, currency)
            VALUES (?, ?, ?, '₹')
        """, (username, email, password_hash))
        user_id = cursor.lastrowid

    today = datetime.now()
    current_month_str = today.strftime("%Y-%m")
    
    # Calculate previous month
    first_of_month = today.replace(day=1)
    prev_month_last_day = first_of_month - timedelta(days=1)
    prev_month_str = prev_month_last_day.strftime("%Y-%m")

    # 1. Incomes for Previous Month
    prev_incomes = [
        (85000.0, "Salary", f"{prev_month_str}-01", "received", "Monthly tech lead salary"),
        (12000.0, "Freelance Consulting", f"{prev_month_str}-15", "received", "UI/UX client audit project"),
        (3500.0, "Dividends & Interest", f"{prev_month_str}-22", "received", "Quarterly mutual fund return"),
    ]
    for amount, source, date_str, status, notes in prev_incomes:
        cursor.execute("""
            INSERT INTO incomes (user_id, amount, source, date, status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, amount, source, date_str, status, notes))

    # 2. Incomes for Current Month
    curr_incomes = [
        (85000.0, "Salary", f"{current_month_str}-01", "received", "Monthly tech lead salary"),
        (15000.0, "Freelance Consulting", f"{current_month_str}-10", "received", "Full-stack web application build"),
        (5000.0, "Annual Bonus", f"{current_month_str}-25", "expected", "Quarterly milestone performance bonus"),
    ]
    for amount, source, date_str, status, notes in curr_incomes:
        cursor.execute("""
            INSERT INTO incomes (user_id, amount, source, date, status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, amount, source, date_str, status, notes))

    # 3. Expenses for Previous Month
    prev_expenses = [
        (22000.0, "Rent", f"{prev_month_str}-02", "UPI", "Apartment rent"),
        (6500.0, "Food", f"{prev_month_str}-05", "UPI", "Supermarket monthly groceries"),
        (2800.0, "Food", f"{prev_month_str}-12", "Credit Card", "Weekend dining with friends"),
        (3500.0, "Bills", f"{prev_month_str}-07", "Debit Card", "Electricity and fiber broadband"),
        (2200.0, "Transport", f"{prev_month_str}-09", "UPI", "Monthly Metro pass and cab rides"),
        (4500.0, "Shopping", f"{prev_month_str}-16", "Credit Card", "Autumn apparel & shoes"),
        (1499.0, "Subscriptions", f"{prev_month_str}-18", "Credit Card", "Netflix & Spotify family plans"),
        (2000.0, "Healthcare", f"{prev_month_str}-20", "Debit Card", "Dental checkup and vitamins"),
        (1800.0, "Entertainment", f"{prev_month_str}-25", "UPI", "Movie night and snacks"),
        (1200.0, "Other", f"{prev_month_str}-27", "Cash", "Home essentials & stationery"),
    ]
    for amount, cat, date_str, pm, desc in prev_expenses:
        cursor.execute("""
            INSERT INTO expenses (user_id, amount, category, date, payment_method, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, amount, cat, date_str, pm, desc))

    # 4. Expenses for Current Month (spanning various days up to today)
    curr_expenses = [
        (22000.0, "Rent", f"{current_month_str}-02", "UPI", "Apartment rent for current month"),
        (7200.0, "Food", f"{current_month_str}-04", "UPI", "Organic grocery haul & pantry restocking"),
        (3200.0, "Bills", f"{current_month_str}-06", "Debit Card", "High-speed internet & power utility"),
        (1800.0, "Transport", f"{current_month_str}-08", "UPI", "Fuel refills and metro commute card"),
        (5600.0, "Shopping", f"{current_month_str}-09", "Credit Card", "Ergonomic desk chair accessories"),
        (2400.0, "Food", f"{current_month_str}-11", "Credit Card", "Dinner at artisanal Italian restaurant"),
        (1499.0, "Subscriptions", f"{current_month_str}-12", "Credit Card", "Cloud storage & music streaming"),
        (3500.0, "Education", f"{current_month_str}-13", "UPI", "Advanced System Design masterclass"),
        (1600.0, "Entertainment", f"{current_month_str}-14", "UPI", "Concert tickets and museum tour"),
        (950.0, "Healthcare", f"{current_month_str}-15", "Debit Card", "Health supplements & wellness"),
        (750.0, "Food", f"{current_month_str}-16", "Cash", "Weekly fresh farmers market produce"),
    ]
    for amount, cat, date_str, pm, desc in curr_expenses:
        # Avoid future dates if today is earlier in month
        day_num = int(date_str.split('-')[2])
        if day_num > today.day:
            # Shift to earlier date within current month
            adjusted_day = max(1, (day_num % today.day) if today.day > 1 else 1)
            date_str = f"{current_month_str}-{adjusted_day:02d}"
        
        cursor.execute("""
            INSERT INTO expenses (user_id, amount, category, date, payment_method, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, amount, cat, date_str, pm, desc))

    # 5. Budgets for Current Month
    cursor.execute("""
        INSERT INTO budgets (user_id, month_year, total_budget)
        VALUES (?, ?, 65000.0)
    """, (user_id, current_month_str))

    category_budgets_list = [
        ("Food", 15000.0),
        ("Rent", 22000.0),
        ("Transport", 5000.0),
        ("Shopping", 8000.0),
        ("Education", 5000.0),
        ("Bills", 4500.0),
        ("Healthcare", 3000.0),
        ("Entertainment", 3500.0),
        ("Subscriptions", 2000.0),
        ("Travel", 5000.0),
        ("Other", 3000.0)
    ]
    for cat, b_amt in category_budgets_list:
        cursor.execute("""
            INSERT INTO category_budgets (user_id, month_year, category, amount)
            VALUES (?, ?, ?, ?)
        """, (user_id, current_month_str, cat, b_amt))

    # 6. EXACTLY THREE Active Savings Goals as required
    goals = [
        ("Buy a bike", 85000.0, 42500.0, f"{(today.year + 1)}-05-31", "bike"),
        ("Buy a laptop", 95000.0, 68000.0, f"{today.year}-12-31", "laptop"),
        ("Build an emergency fund", 150000.0, 85000.0, f"{(today.year + 1)}-09-30", "shield-check")
    ]

    for name, target, current, deadline, icon in goals:
        cursor.execute("""
            INSERT INTO savings_goals (user_id, name, target_amount, current_amount, deadline, category_icon, is_completed)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        """, (user_id, name, target, current, deadline, icon))
        goal_id = cursor.lastrowid

        # Insert historical contributions for this goal
        cursor.execute("""
            INSERT INTO savings_contributions (goal_id, user_id, amount, date, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (goal_id, user_id, current * 0.6, f"{prev_month_str}-10", "Initial major savings allocation"))
        
        cursor.execute("""
            INSERT INTO savings_contributions (goal_id, user_id, amount, date, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (goal_id, user_id, current * 0.4, f"{current_month_str}-05", "Monthly disciplined contribution"))

    conn.commit()
    conn.close()
    print(f"Successfully seeded demo data for user '{username}' (password: '{password}').")

if __name__ == '__main__':
    seed_demo_data()
