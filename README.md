# Finance Tracker - Full Stack Project

A Flask-based web application for tracking expenses, budgets, and investments with MySQL database.

## Prerequisites
- Python 3.7+
- MySQL Server
- pip (Python package manager)

## Installation & Setup

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd DBMS-miniproject-main
```

### 2. Create Database
- Open MySQL and run the initialization script:
```bash
mysql -u root -p < db_init.sql
```
- Then add the missing tables (categories, notifications):
```bash
mysql -u root -p < add_missing_tables.sql
```

### 3. Configure Database Connection
- Copy `config.example.py` to `config.py`:
```bash
cp config.example.py config.py
```
- Edit `config.py` and replace with your actual credentials:
  - `DB_PASSWORD`: Your MySQL password
  - `SECRET_KEY`: A secure random string for sessions

**Important:** Never commit `config.py` to GitHub (it's protected by `.gitignore`)

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the Application
```bash
python app.py
```
- Open your browser and go to: `http://localhost:5000`

## Project Structure
- `app.py` - Main Flask application
- `config.py` - Database credentials (create from config.example.py)
- `templates/` - HTML templates
- `static/` - CSS and JavaScript files
- `*.sql` - Database initialization scripts

## Features

### 🔐 Authentication
- **User Registration**: Create a new account with name, email, date of birth, and preferred payment method
- **User Login**: Secure login with password hashing
- **Session Management**: Automatic logout functionality

### 💰 Expense Management
- **Add Expenses**: Record expenses with category, date, amount, and description
- **View Expenses**: Browse all your expenses in a detailed list
- **Expense Dashboard**: Quick overview of spending patterns

### 🎯 Budget Management
- **Create Budgets**: Set monthly budgets for different categories
- **Track Budget Usage**: Monitor how much you've spent vs. your budget limit
- **Budget Alerts**: Notifications when approaching budget limits

### 📈 Investment Tracking
- **Add Investments**: Record investment details (type, amount, date)
- **View Investments**: Track all your investments in one place
- **Investment Overview**: See your total investment portfolio

### 📊 Reports & Analytics
- **Financial Reports**: Comprehensive analysis of your expenses, budgets, and investments
- **Spending Trends**: Visual representation of where your money goes
- **Category Breakdown**: See expenses by category
- **Monthly Summary**: View monthly financial overview

### 🔔 Smart Features
- **Notifications**: Smart alerts for budget warnings and financial milestones
- **Suggestions**: AI-powered spending suggestions based on your patterns
- **Dashboard**: Real-time overview of all your financial data

## How to Use

1. **Register**: Create a new account with your details
2. **Login**: Access your personal finance dashboard
3. **Add Expenses**: Record daily expenses as they occur
4. **Set Budgets**: Define monthly budgets for better control
5. **Track Investments**: Monitor your investment portfolio
6. **View Reports**: Analyze your financial health with comprehensive reports
7. **Get Insights**: Receive suggestions and alerts to improve spending habits
