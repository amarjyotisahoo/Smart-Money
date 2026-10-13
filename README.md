# SmartMoney — Personal Finance & Savings Tracker

**SmartMoney** is a modern, high-performance personal finance web application built to help users manage their monthly salary, record daily expenses, analyze spending habits, control category budgets, and save for **exactly three focused financial goals**.

Designed with a fintech aesthetic: clean white and dark navy surfaces, emerald green accents, modern typography, responsive cards, interactive Chart.js visualizations, and Lucide icons.

---

## 🌟 Key Features

### 1. Financial Dashboard
- **Real-time Overview:** Monthly Income, Monthly Expenses, Available Balance, Total Savings, Savings Rate (%), and Suggested Daily Spending Limit.
- **Date Filters:** Quick filters for *Today*, *This Week*, *This Month*, and custom date range picker.
- **Interactive Visualizations:**
  - 6-Month Income vs Expenses grouped bar chart.
  - Expense Category Breakdown donut chart with interactive percentages.
- **Goal Snapshot:** Instant status cards for all 3 active savings goals.
- **Recent Activity Feed:** Combined transaction ledger with category badges and payment methods.

### 2. Income Management
- Record monthly salary, freelance earnings, dividends, and other revenue streams.
- Categorize by amount, source, date, and optional notes.
- **Status Distinction:** Clearly distinguish **Received** cash from **Expected / Pending** receivables with a 1-click status toggle.
- Monthly inflow statistics (Total received, expected, entry count, average inflow).

### 3. Fast Expense Tracker
- Fast modal expense entry form with amount, category, date, payment method, and description.
- **11 Default Categories:** Food, Rent, Transport, Shopping, Education, Bills, Healthcare, Entertainment, Subscriptions, Travel, Other.
- **Payment Methods:** UPI, Debit Card, Credit Card, Cash.
- **Search & Filter:** Real-time search by description, filter by category and payment method, sort by date (newest/oldest) or amount (highest/lowest).

### 4. The Three Savings Goals (Disciplined Focus)
- Enforces **exactly up to three active savings goals** (e.g., *Buy a bike*, *Buy a laptop*, *Build an emergency fund*).
- Displays Goal Name, Target Amount, Current Savings, Remaining Amount, Target Deadline, and Completion Percentage.
- **Formula-Driven Projections:** Dynamically calculates **Suggested Monthly Contribution** based on months remaining to deadline.
- **Zero Double-Counting:** Savings deposits are recorded in dedicated goal contribution ledgers without being treated as day-to-day expenses.
- Achieved goals can be archived or completed, freeing up a slot for a new goal.

### 5. Budget Management & Daily Allowance
- Set total monthly spending ceiling.
- Configure individual category spending budgets.
- **Suggested Daily Spending Limit:** Real-time calculation:
  $$\text{Daily Limit} = \frac{\text{Remaining Budget}}{\text{Days Left in Month}}$$
- **Visual Warning Thresholds:**
  - 🟢 Normal (`< 80%` budget utilized)
  - 🟡 Warning (`80% – 99%` budget utilized)
  - 🔴 Danger / Alert (`≥ 100%` budget exceeded)

### 6. Smart Financial Insights Engine
- Algorithmic, data-grounded insights derived strictly from user transaction history:
  - Highest spending category identification.
  - Month-over-month category variance (e.g. *“You spent ₹800 more on shopping than last month”*).
  - Budget runway alerts and remaining daily allowance.
  - Projected month-end expenditures based on daily burn rate (*explicitly labeled as estimates*).
  - Savings rate health index (50/30/20 guideline).

### 7. Reports & CSV Export
- 12-month multi-series macro trend line (Income vs Expenses vs Goal Contributions).
- Month-over-month category comparison table with percentage differences and trend direction.
- Payment method breakdown.
- **One-Click CSV Exports:**
  - Export Expenses CSV
  - Export Incomes CSV
  - Export Complete Financial Ledger CSV

### 8. Fintech UI/UX & Security
- **Light & Dark Mode:** Persisted in local storage, instant toggle without page reload.
- **Responsive Layout:** Fixed desktop sidebar navigation, responsive top bar, and mobile drawer.
- **Security:**
  - Passwords hashed with `werkzeug.security` (scrypt / pbkdf2).
  - Parameterized SQLite queries everywhere.
  - CSRF protection on all state-changing requests.
  - Strict user data isolation (`user_id` authorization checks on every operation).
  - No connection to real bank APIs or live credit cards.

---

## 🛠️ Technology Stack

- **Backend:** Python 3.10+ / Flask 3.1
- **Database:** SQLite3 with relational foreign keys, constraints, and indexes
- **Frontend:** HTML5, CSS3 (Modern CSS variables, Flexbox & CSS Grid)
- **Charts:** Chart.js 4.4
- **Icons:** Lucide Icons (CDN)
- **Fonts:** Plus Jakarta Sans & JetBrains Mono

---

## 📂 Project Structure

```
Smart Money/
├── app.py                     # Main Flask application & routing API
├── database.py                # Database connection, schema migrations & initialization
├── demo_data.py               # Seed generator with rich, realistic financial data
├── test_app.py                # Automated unit test suite
├── requirements.txt           # Python dependencies
├── README.md                  # Documentation
├── static/
│   ├── css/
│   │   └── style.css          # Fintech design system, dark/light themes, animations
│   └── js/
│       ├── app.js             # Theme toggle, modal helpers, toast alerts, AJAX
│       └── charts.js          # Chart.js configurations & theme hooks
└── templates/
    ├── base.html              # Layout with responsive sidebar, header & toasts
    ├── dashboard.html         # Main dashboard overview & charts
    ├── incomes.html           # Incomes management & received vs expected switcher
    ├── expenses.html          # Fast expense logger, search & filters
    ├── goals.html             # The 3 Savings Goals hub & isolated contributions
    ├── budgets.html           # Monthly budget setup, category limits & daily limit
    ├── insights.html          # Smart financial insights & projections
    ├── reports.html           # 12-month analytics, comparisons & CSV exports
    ├── settings.html          # Currency settings, password & demo data tool
    └── auth/
        ├── login.html         # Login page + 1-Click Demo Account button
        └── register.html      # Registration page
```

---

## 🚀 How to Run Locally on Windows (VS Code)

### Prerequisites
- Python 3.10+ installed on your computer.

### Step 1: Open Folder in VS Code
Open VS Code, press `Ctrl + O` or choose **File > Open Folder...**, and select the `Smart Money` folder.

### Step 2: Open Terminal in VS Code
Press `Ctrl + ~` (or `Terminal > New Terminal` in top menu).

### Step 3: Install Requirements (Optional/Fast)
```powershell
pip install -r requirements.txt
```

### Step 4: Run the Application
```powershell
python app.py
```
You will see output in the terminal:
```
🚀 Starting SmartMoney on http://127.0.0.1:5000
```

### Step 5: Open in Browser
Open your web browser and navigate to:
[http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🔑 Demo Account (Instant 1-Click Evaluation)

On the Login page, simply click **"Explore with Demo Account (Alex)"** or enter:
- **Username / Email:** `alex` (or `alex@smartmoney.io`)
- **Password:** `password123`

The demo account comes pre-seeded with:
- Monthly salary and freelance income.
- Categorized expenses across Food, Rent, Transport, Shopping, Bills, etc.
- Monthly spending budget of ₹65,000.
- **Exactly three active savings goals:**
  1. *Buy a bike* (Target: ₹85,000 | Current: ₹42,500)
  2. *Buy a laptop* (Target: ₹95,000 | Current: ₹68,000)
  3. *Build an emergency fund* (Target: ₹1,50,000 | Current: ₹85,000)
- Historical savings contribution logs without double-counting.

---

## 🧪 Running Automated Tests
To run the automated test suite verifying auth, budget limits, 3-goal limits, and exports:
```powershell
python test_app.py
```
All 7 unit tests will execute and confirm `OK`.

---

## 🔒 Security & Privacy Notice
SmartMoney is an educational and personal tracker. It stores data locally in `smartmoney.db`, hashes all passwords securely, protects against CSRF and SQL injection, and does not transmit financial data to external third parties.
