from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import config
from datetime import date, datetime, timedelta

app = Flask(__name__)
app.secret_key = config.SECRET_KEY


# ------------------ DB CONNECTION ------------------
def get_db():
    return mysql.connector.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
    )


# ------------------ HOME PAGE ------------------
@app.route('/')
def index():
    return render_template('index.html')


# ------------------ REGISTER ------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fname = request.form['fname']
        lname = request.form.get('lname', '')
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        dob = request.form.get('dob') or None
        preferred_payment = request.form.get('preferred_payment') or None

        db = get_db()
        cursor = db.cursor()

        try:
            cursor.execute("""
                INSERT INTO users (fname, lname, email, password, dob, preferred_payment)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (fname, lname, email, password, dob, preferred_payment))
            db.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))

        except mysql.connector.IntegrityError:
            flash('Email already registered!', 'danger')

        finally:
            cursor.close()
            db.close()

    return render_template('register.html')


# ------------------ LOGIN ------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        db.close()

        if not user:
            flash("Email not found. Please register first.", "warning")
            return redirect(url_for('register'))

        if check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['name'] = user['fname']
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Incorrect password.", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')


# ------------------ LOGOUT ------------------
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for('index'))


# ------------------ DASHBOARD ------------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Generate daily suggestion
    generate_daily_suggestion(user_id)

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # ---------- TOTAL EXPENSE ----------
    cursor.execute("""
        SELECT SUM(amount) AS total_exp
        FROM expense
        WHERE user_id=%s
    """, (user_id,))
    total_expense = cursor.fetchone()['total_exp'] or 0

    # ---------- TOTAL INVESTMENT ----------
    cursor.execute("""
        SELECT SUM(amount_invested) AS total_inv
        FROM investment
        WHERE user_id=%s
    """, (user_id,))
    total_invest = cursor.fetchone()['total_inv'] or 0

    # ---------- GENERATE MONTHLY SUGGESTIONS FOR ALL MONTHS WITH EXPENSES ----------
    # First, get all months where user has expenses
    cursor.execute("""
        SELECT DISTINCT DATE_FORMAT(expense_date, '%Y-%m') AS month_year,
               DATE_FORMAT(expense_date, '%M %Y') AS month_name,
               MONTH(expense_date) AS month_num,
               YEAR(expense_date) AS year_num
        FROM expense
        WHERE user_id = %s
        ORDER BY month_year DESC
        LIMIT 12
    """, (user_id,))
    expense_months = cursor.fetchall()
    
    # Generate monthly suggestions for each month with expenses
    for em in expense_months:
        generate_monthly_suggestion_for_month(user_id, em['year_num'], em['month_num'])
    
    # Now get all monthly suggestions grouped by month
    cursor.execute("""
        SELECT DATE_FORMAT(suggested_date, '%Y-%m') AS month_year,
               DATE_FORMAT(suggested_date, '%M %Y') AS month_name,
               SUM(suggested_amount) AS total_suggested,
               COUNT(*) AS suggestion_count,
               GROUP_CONCAT(DISTINCT suggested_investment_type SEPARATOR ', ') AS investment_types
        FROM micro_investment_suggestion
        WHERE user_id=%s
        GROUP BY DATE_FORMAT(suggested_date, '%Y-%m'), DATE_FORMAT(suggested_date, '%M %Y')
        ORDER BY month_year DESC
        LIMIT 12
    """, (user_id,))
    monthly_suggestions = cursor.fetchall()
    
    # Convert Decimal to float
    for ms in monthly_suggestions:
        ms['total_suggested'] = float(ms['total_suggested']) if ms['total_suggested'] else 0

    # ---------- RECENT DAILY SUGGESTIONS (last 10) ----------
    cursor.execute("""
        SELECT *
        FROM micro_investment_suggestion
        WHERE user_id=%s
        ORDER BY suggested_date DESC
        LIMIT 10
    """, (user_id,))
    recent_suggestions = cursor.fetchall()

    # ---------- MONTHLY SUMMARY (Current Month) ----------
    today = date.today()
    month = today.month
    year = today.year

    # Monthly expense
    cursor.execute("""
        SELECT SUM(amount) AS monthly_expense
        FROM expense
        WHERE user_id=%s
          AND MONTH(expense_date)=%s
          AND YEAR(expense_date)=%s
    """, (user_id, month, year))
    monthly_expense = cursor.fetchone()['monthly_expense'] or 0

    # Monthly micro investment suggested amount (sum of daily suggestions for current month)
    cursor.execute("""
        SELECT SUM(suggested_amount) AS monthly_suggested
        FROM micro_investment_suggestion
        WHERE user_id=%s
          AND MONTH(suggested_date)=%s
          AND YEAR(suggested_date)=%s
    """, (user_id, month, year))
    monthly_suggested = cursor.fetchone()['monthly_suggested'] or 0

    # ---------- BUDGET STATUS & NOTIFICATIONS ----------
    # Get active budgets with spending
    cursor.execute("""
        SELECT b.budget_id, b.category, b.limit_amount, b.start_date, b.end_date,
               COALESCE(SUM(e.amount), 0) AS spent
        FROM budget b
        LEFT JOIN expense e ON b.budget_id = e.budget_id
        WHERE b.user_id = %s
          AND CURDATE() BETWEEN b.start_date AND b.end_date
        GROUP BY b.budget_id, b.category, b.limit_amount, b.start_date, b.end_date
    """, (user_id,))
    active_budgets = cursor.fetchall()
    
    # Convert Decimal values to float for template calculations
    for budget in active_budgets:
        limit = float(budget['limit_amount']) if budget['limit_amount'] else 0
        spent = float(budget['spent']) if budget['spent'] else 0
        budget['limit_amount'] = limit
        budget['spent'] = spent
        budget['remaining'] = limit - spent

    # Get unread notifications
    cursor.execute("""
        SELECT * FROM notifications
        WHERE user_id = %s AND is_read = FALSE
        ORDER BY created_at DESC
        LIMIT 10
    """, (user_id,))
    notifications = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "dashboard.html",
        total_expense=total_expense,
        total_invest=total_invest,
        recent_suggestions=recent_suggestions,
        monthly_suggestions=monthly_suggestions,
        monthly_expense=monthly_expense,
        monthly_suggested=monthly_suggested,
        active_budgets=active_budgets,
        notifications=notifications
    )

@app.route('/add-expense', methods=['GET', 'POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor(dictionary=True)
    user_id = session['user_id']

    if request.method == 'POST':
        amount = request.form['amount']
        category_id = request.form['category_id']
        description = request.form.get('description')
        payment_method = request.form['payment_method']
        budget_id = request.form.get('budget_id') or None
        expense_date = request.form.get('expense_date') or date.today()

        cursor.execute("""
            INSERT INTO expense (user_id, budget_id, amount, category_id,
                                 description, payment_method, expense_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, budget_id, amount, category_id, description, payment_method, expense_date))
        db.commit()
        
        # Generate daily suggestion after expense
        generate_daily_suggestion(user_id)
        
        # Check budget and create notifications
        check_budget_and_notify(user_id, budget_id, float(amount))

        flash("Expense added!", "success")
        return redirect(url_for('view_expenses'))

    # Load categories
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()

    # Load budgets
    cursor.execute("SELECT * FROM budget WHERE user_id=%s", (user_id,))
    budgets = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        'add_expense.html',
        categories=categories,
        budgets=budgets,
        today=date.today().strftime('%Y-%m-%d')
    )

# ------------------ VIEW EXPENSES ------------------
@app.route('/expenses')
def view_expenses():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
    SELECT e.expense_id, e.amount, c.name AS category, e.description, e.payment_method, e.expense_date
    FROM expense e
    LEFT JOIN categories c ON e.category_id = c.category_id
    WHERE e.user_id = %s
    ORDER BY e.expense_date DESC
""", (session['user_id'],))



    expenses = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('view_expenses.html', expenses=expenses)


# ------------------ ADD INVESTMENT ------------------
@app.route('/add-investment', methods=['GET', 'POST'])
def add_investment():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = session['user_id']
        invest_type = request.form['invested_type']
        amount = request.form['amount']
        invest_date_str = request.form.get('invest_date') or str(date.today())
        risk = request.form.get('risk_level')
        current_value = request.form.get('current_value') or amount

        # Backend validation
        try:
            invest_date_obj = date.fromisoformat(invest_date_str)
        except Exception:
            flash("Invalid date format for investment.", "danger")
            return redirect(url_for('add_investment'))

        if invest_date_obj > date.today():
            flash("Investment date cannot be in the future.", "danger")
            return redirect(url_for('add_investment'))

        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO investment (user_id, invested_type, amount_invested,
                                    investment_date, current_value, risk_level)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, invest_type, amount, invest_date_obj, current_value, risk))
        db.commit()

        cursor.close()
        db.close()

        flash("Investment added!", "success")
        return redirect(url_for('view_investments'))

    # GET
    return render_template('add_investment.html', today=date.today())

# ------------------ VIEW INVESTMENTS ------------------
@app.route('/investments')
def view_investments():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM investment
        WHERE user_id=%s
        ORDER BY investment_date DESC
    """, (session['user_id'],))

    investments = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('view_investments.html', investments=investments)


# ------------------ ADD BUDGET ------------------
@app.route('/add-budget', methods=['GET', 'POST'])
def add_budget():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor(dictionary=True)
    user_id = session['user_id']

    if request.method == 'POST':
        category = request.form['category']        # category name
        limit_amount = request.form['limit_amount']
        start_date = request.form['start_date']
        end_date = request.form['end_date']

        cursor.execute("""
            INSERT INTO budget (user_id, category, limit_amount, start_date, end_date)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, category, limit_amount, start_date, end_date))

        db.commit()
        cursor.close()
        db.close()

        flash("Budget added successfully!", "success")
        return redirect(url_for('view_budgets'))

    # load categories for dropdown
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('add_budget.html', categories=categories)


# ------------------ VIEW BUDGETS ------------------
@app.route('/budgets')
def view_budgets():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor(dictionary=True)
    user_id = session['user_id']

    # Get budgets with spending information
    cursor.execute("""
        SELECT b.budget_id, b.user_id, b.category, b.start_date, b.end_date, b.limit_amount,
               COALESCE(SUM(e.amount), 0) AS spent,
               (b.limit_amount - COALESCE(SUM(e.amount), 0)) AS remaining
        FROM budget b
        LEFT JOIN expense e ON b.budget_id = e.budget_id
        WHERE b.user_id = %s
        GROUP BY b.budget_id, b.user_id, b.category, b.start_date, b.end_date, b.limit_amount
        ORDER BY b.start_date DESC
    """, (user_id,))

    budgets = cursor.fetchall()

    # Calculate percentage spent for each budget and convert Decimal to float
    for budget in budgets:
        limit = float(budget['limit_amount']) if budget['limit_amount'] else 0
        spent = float(budget['spent']) if budget['spent'] else 0
        budget['limit_amount'] = limit
        budget['spent'] = spent
        budget['remaining'] = limit - spent
        if limit > 0:
            budget['percentage'] = min(100, (spent / limit) * 100)
        else:
            budget['percentage'] = 0

    cursor.close()
    db.close()

    return render_template('view_budgets.html', budgets=budgets)



# ------------------ GENERATE MONTHLY SUGGESTION FOR SPECIFIC MONTH ------------------
def generate_monthly_suggestion_for_month(user_id, year, month):
    """Generate a monthly investment suggestion for a specific month based on that month's expenses"""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    # Check if monthly suggestion already exists for this month
    cursor.execute("""
        SELECT 1 FROM micro_investment_suggestion
        WHERE user_id = %s
        AND YEAR(suggested_date) = %s
        AND MONTH(suggested_date) = %s
        AND DAY(suggested_date) = 1
    """, (user_id, year, month))
    
    if cursor.fetchone():
        cursor.close()
        db.close()
        return  # Already created for this month
    
    # Get monthly expenses for this specific month
    cursor.execute("""
        SELECT SUM(amount) AS monthly_expenses
        FROM expense
        WHERE user_id = %s
        AND MONTH(expense_date) = %s
        AND YEAR(expense_date) = %s
    """, (user_id, month, year))
    
    result = cursor.fetchone()
    monthly_expenses = float(result['monthly_expenses']) if result['monthly_expenses'] else 0
    
    # Get budgets active during this month
    cursor.execute("""
        SELECT SUM(limit_amount) AS total_budget
        FROM budget
        WHERE user_id = %s
        AND (YEAR(start_date) < %s OR (YEAR(start_date) = %s AND MONTH(start_date) <= %s))
        AND (YEAR(end_date) > %s OR (YEAR(end_date) = %s AND MONTH(end_date) >= %s))
    """, (user_id, year, year, month, year, year, month))
    
    budget_result = cursor.fetchone()
    total_budget = float(budget_result['total_budget']) if budget_result['total_budget'] else 0
    
    # Calculate monthly suggestion based on expenses and budget
    if total_budget > 0:
        budget_usage = (monthly_expenses / total_budget) * 100 if total_budget > 0 else 0
        if budget_usage < 50:
            suggested_amount = min(5000, monthly_expenses * 0.15) if monthly_expenses > 0 else 500
            suggestion_type = "Low-Risk SIP"
        elif budget_usage < 80:
            suggested_amount = min(3000, monthly_expenses * 0.10) if monthly_expenses > 0 else 300
            suggestion_type = "Index Fund"
        else:
            suggested_amount = min(1500, monthly_expenses * 0.05) if monthly_expenses > 0 else 150
            suggestion_type = "Liquid Fund"
    else:
        # No budget set - base on monthly expenses
        if monthly_expenses < 5000:
            suggested_amount = 500
            suggestion_type = "Low-Risk SIP"
        elif monthly_expenses < 10000:
            suggested_amount = 300
            suggestion_type = "Index Fund"
        else:
            suggested_amount = 150
            suggestion_type = "Liquid Fund"
    
    # Ensure minimum suggestion
    if suggested_amount < 100:
        suggested_amount = 100
    
    # Insert monthly suggestion (on the 1st of the month for that month)
    suggestion_date = date(year, month, 1)
    cursor.execute("""
        INSERT INTO micro_investment_suggestion 
        (user_id, suggested_amount, suggested_investment_type, status, suggested_date)
        VALUES (%s, %s, %s, 'Pending', %s)
    """, (user_id, suggested_amount, suggestion_type, suggestion_date))
    
    db.commit()
    cursor.close()
    db.close()

# ------------------ MICRO INVEST SUGGESTION (DAILY) ------------------
def generate_daily_suggestion(user_id):
    """Generate daily micro investment suggestions based on daily expenses"""
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # 1. Check if suggestion already exists for today
    cursor.execute("""
        SELECT 1 FROM micro_investment_suggestion
        WHERE user_id = %s
        AND suggested_date = CURDATE()
    """, (user_id,))
    
    if cursor.fetchone():
        cursor.close()
        db.close()
        return  # Already created for today

    # 2. Get today's expenses
    cursor.execute("""
        SELECT SUM(amount) AS daily_expenses
        FROM expense
        WHERE user_id = %s
        AND expense_date = CURDATE()
    """, (user_id,))
    
    result = cursor.fetchone()
    daily_expenses = result['daily_expenses'] or 0

    # 3. Get monthly expenses so far
    cursor.execute("""
        SELECT SUM(amount) AS monthly_expenses
        FROM expense
        WHERE user_id = %s
        AND MONTH(expense_date) = MONTH(CURDATE())
        AND YEAR(expense_date) = YEAR(CURDATE())
    """, (user_id,))
    
    monthly_result = cursor.fetchone()
    monthly_expenses = monthly_result['monthly_expenses'] or 0

    # 4. Get active budgets
    cursor.execute("""
        SELECT SUM(limit_amount) AS total_budget
        FROM budget
        WHERE user_id = %s
        AND CURDATE() BETWEEN start_date AND end_date
    """, (user_id,))
    
    budget_result = cursor.fetchone()
    total_budget = budget_result['total_budget'] or 0

    # 5. Calculate daily suggestion based on expenses and budget
    # If spending is low relative to budget, suggest more investment
    if total_budget > 0:
        budget_usage = (monthly_expenses / total_budget) * 100 if total_budget > 0 else 0
        if budget_usage < 50:
            # Low spending - can invest more
            suggested_amount = min(500, daily_expenses * 0.1) if daily_expenses > 0 else 50
            suggestion_type = "Low-Risk SIP"
        elif budget_usage < 80:
            # Moderate spending
            suggested_amount = min(300, daily_expenses * 0.05) if daily_expenses > 0 else 30
            suggestion_type = "Index Fund"
        else:
            # High spending - conservative
            suggested_amount = min(150, daily_expenses * 0.02) if daily_expenses > 0 else 15
            suggestion_type = "Liquid Fund"
    else:
        # No budget set - base on daily expenses
        if daily_expenses < 500:
            suggested_amount = 50
            suggestion_type = "Low-Risk SIP"
        elif daily_expenses < 1000:
            suggested_amount = 30
            suggestion_type = "Index Fund"
        else:
            suggested_amount = 15
            suggestion_type = "Liquid Fund"

    # Ensure minimum suggestion
    if suggested_amount < 10:
        suggested_amount = 10

    # 6. Insert daily suggestion
    cursor.execute("""
        INSERT INTO micro_investment_suggestion 
        (user_id, suggested_amount, suggested_investment_type, status, suggested_date)
        VALUES (%s, %s, %s, 'Pending', CURDATE())
    """, (user_id, suggested_amount, suggestion_type))

    db.commit()
    cursor.close()
    db.close()

# ------------------ BUDGET TRACKING & NOTIFICATIONS ------------------
def check_budget_and_notify(user_id, budget_id, expense_amount):
    """Check budget status and create notifications"""
    if not budget_id:
        return
    
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Get budget details
    cursor.execute("""
        SELECT * FROM budget
        WHERE budget_id = %s AND user_id = %s
    """, (budget_id, user_id))
    
    budget = cursor.fetchone()
    if not budget:
        cursor.close()
        db.close()
        return

    # Calculate total spent for this budget
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total_spent
        FROM expense
        WHERE budget_id = %s
    """, (budget_id,))
    
    result = cursor.fetchone()
    total_spent = float(result['total_spent']) if result['total_spent'] else 0
    limit_amount = float(budget['limit_amount'])
    remaining = limit_amount - total_spent
    percentage = (total_spent / limit_amount * 100) if limit_amount > 0 else 0

    # Create notifications based on budget status
    if total_spent >= limit_amount:
        # Budget exceeded
        message = f"⚠️ Budget EXCEEDED! You've spent ₹{total_spent:.2f} out of ₹{limit_amount:.2f} for {budget['category']}. Please stop spending in this category."
        cursor.execute("""
            INSERT INTO notifications (user_id, notification_type, message, budget_id)
            VALUES (%s, 'budget_exceeded', %s, %s)
        """, (user_id, message, budget_id))
    elif percentage >= 90:
        # 90% threshold
        message = f"⚠️ Budget Warning: You've spent {percentage:.1f}% (₹{total_spent:.2f}) of your {budget['category']} budget. Only ₹{remaining:.2f} remaining. Consider reducing spending."
        cursor.execute("""
            INSERT INTO notifications (user_id, notification_type, message, budget_id)
            VALUES (%s, 'budget_warning', %s, %s)
        """, (user_id, message, budget_id))
    elif percentage >= 75:
        # 75% threshold
        message = f"📊 Budget Alert: You've spent {percentage:.1f}% (₹{total_spent:.2f}) of your {budget['category']} budget. ₹{remaining:.2f} remaining."
        cursor.execute("""
            INSERT INTO notifications (user_id, notification_type, message, budget_id)
            VALUES (%s, 'spending_alert', %s, %s)
        """, (user_id, message, budget_id))
    elif percentage >= 50:
        # 50% threshold - informational
        message = f"💡 You've spent {percentage:.1f}% (₹{total_spent:.2f}) of your {budget['category']} budget. ₹{remaining:.2f} remaining."
        cursor.execute("""
            INSERT INTO notifications (user_id, notification_type, message, budget_id)
            VALUES (%s, 'spending_alert', %s, %s)
        """, (user_id, message, budget_id))

    db.commit()
    cursor.close()
    db.close()

# ------------------ REPORTS ------------------
@app.route('/reports')
def reports():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor(dictionary=True)
    user_id = session['user_id']

    # Get monthly expense summary with category breakdown
    cursor.execute("""
        SELECT DATE_FORMAT(expense_date, '%Y-%m') AS month_year,
               DATE_FORMAT(expense_date, '%M %Y') AS month_name,
               SUM(amount) AS total_expense,
               COUNT(*) AS expense_count
        FROM expense
        WHERE user_id=%s
        GROUP BY DATE_FORMAT(expense_date, '%Y-%m'), DATE_FORMAT(expense_date, '%M %Y')
        ORDER BY month_year DESC
        LIMIT 12
    """, (user_id,))

    monthly_summary = cursor.fetchall()

    # Get category-wise breakdown for each month
    for month_data in monthly_summary:
        month_year = month_data['month_year']
        cursor.execute("""
            SELECT c.name AS category,
                   SUM(e.amount) AS category_total,
                   COUNT(*) AS category_count
            FROM expense e
            LEFT JOIN categories c ON e.category_id = c.category_id
            WHERE e.user_id = %s
              AND DATE_FORMAT(e.expense_date, '%%Y-%%m') = %s
            GROUP BY c.name
            ORDER BY category_total DESC
        """, (user_id, month_year))
        month_data['categories'] = cursor.fetchall()

    # Get current month detailed breakdown
    today = date.today()
    current_month = today.strftime('%Y-%m')
    cursor.execute("""
        SELECT c.name AS category,
               SUM(e.amount) AS category_total,
               COUNT(*) AS category_count,
               (SUM(e.amount) / (SELECT SUM(amount) FROM expense WHERE user_id = %s AND DATE_FORMAT(expense_date, '%%Y-%%m') = %s) * 100) AS percentage
        FROM expense e
        LEFT JOIN categories c ON e.category_id = c.category_id
        WHERE e.user_id = %s
          AND DATE_FORMAT(e.expense_date, '%%Y-%%m') = %s
        GROUP BY c.name
        ORDER BY category_total DESC
    """, (user_id, current_month, user_id, current_month))
    
    current_month_breakdown = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('reports.html', 
                          monthly_summary=monthly_summary,
                          current_month_breakdown=current_month_breakdown,
                          current_month=current_month)

# ------------------ NOTIFICATIONS ------------------
@app.route('/notifications/read/<int:notification_id>')
def mark_notification_read(notification_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        UPDATE notifications
        SET is_read = TRUE
        WHERE notification_id = %s AND user_id = %s
    """, (notification_id, session['user_id']))
    db.commit()
    cursor.close()
    db.close()
    
    return redirect(url_for('dashboard'))

# ------------------ MARK SUGGESTION AS COMPLETED ------------------
@app.route('/suggestion/complete/<int:suggestion_id>')
def mark_suggestion_complete(suggestion_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        UPDATE micro_investment_suggestion
        SET status = 'Completed'
        WHERE suggestion_id = %s AND user_id = %s
    """, (suggestion_id, session['user_id']))
    db.commit()
    cursor.close()
    db.close()
    
    flash("Suggestion marked as completed!", "success")
    return redirect(url_for('dashboard'))


# ------------------ RUN APP ------------------
if __name__ == '__main__':
    app.run(debug=True)
