-- ============================================================
-- DATABASE : Micro Investment & Personal Finance Tracker
-- ============================================================

CREATE DATABASE IF NOT EXISTS finance_tracker;
USE finance_tracker;

-- ============================================================
-- USERS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  fname VARCHAR(100) NOT NULL,
  lname VARCHAR(100),
  email VARCHAR(150) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  dob DATE,
  preferred_payment VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- BUDGET TABLE
-- Each user can set multiple budgets with category, limit, and date range
-- ============================================================
CREATE TABLE IF NOT EXISTS budget (
  budget_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  category VARCHAR(100) NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  limit_amount DECIMAL(12,2) NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ============================================================
-- EXPENSE TABLE
-- Linked to both user and budget (Conforms to budget)
-- ============================================================
CREATE TABLE IF NOT EXISTS expense (
  expense_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  budget_id INT,
  amount DECIMAL(12,2) NOT NULL,
  category VARCHAR(100),
  category_id INT,
  description VARCHAR(255),
  payment_method VARCHAR(50),
  expense_date DATE NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (budget_id) REFERENCES budget(budget_id) ON DELETE SET NULL,
  FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE SET NULL
);

-- ============================================================
-- INVESTMENT TABLE
-- Each user can make multiple investments
-- ============================================================
CREATE TABLE IF NOT EXISTS investment (
  investment_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  invested_type VARCHAR(100) NOT NULL, -- e.g. Stock, SIP, Mutual Fund
  amount_invested DECIMAL(12,2) NOT NULL,
  investment_date DATE NOT NULL,
  current_value DECIMAL(12,2),
  risk_level VARCHAR(50),
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ============================================================
-- MICRO INVESTMENT SUGGESTION TABLE
-- Stores generated investment advice
-- ============================================================
CREATE TABLE IF NOT EXISTS micro_investment_suggestion (
  suggestion_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  suggested_date DATE DEFAULT (CURRENT_DATE),
  suggested_amount DECIMAL(12,2),
  suggested_investment_type VARCHAR(100),
  status VARCHAR(50) DEFAULT 'Pending',
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ============================================================
-- RELATIONSHIPS / ANALYSIS TABLES
-- To record analysis or performance reviews
-- ============================================================

-- Records Analysis between Expense and Suggestion
CREATE TABLE IF NOT EXISTS analysis (
  analysis_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  expense_id INT,
  suggestion_id INT,
  remark VARCHAR(255),
  analysis_date DATE DEFAULT (CURRENT_DATE),
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (expense_id) REFERENCES expense(expense_id) ON DELETE SET NULL,
  FOREIGN KEY (suggestion_id) REFERENCES micro_investment_suggestion(suggestion_id) ON DELETE SET NULL
);

-- Review table for investment performance
CREATE TABLE IF NOT EXISTS review_performance (
  review_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  investment_id INT NOT NULL,
  performance_note VARCHAR(255),
  review_date DATE DEFAULT (CURRENT_DATE),
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (investment_id) REFERENCES investment(investment_id) ON DELETE CASCADE
);

-- ============================================================
-- NOTIFICATIONS TABLE
-- Stores budget alerts and spending notifications
-- ============================================================
CREATE TABLE IF NOT EXISTS notifications (
  notification_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  notification_type VARCHAR(50) NOT NULL, -- 'budget_warning', 'budget_exceeded', 'daily_suggestion', 'spending_alert'
  message TEXT NOT NULL,
  budget_id INT,
  is_read BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (budget_id) REFERENCES budget(budget_id) ON DELETE SET NULL
);

-- ============================================================
-- CATEGORIES TABLE (if not exists)
-- ============================================================
CREATE TABLE IF NOT EXISTS categories (
  category_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE
);

-- Insert default categories if table is empty
INSERT IGNORE INTO categories (name) VALUES 
  ('Food & Dining'),
  ('Transportation'),
  ('Shopping'),
  ('Bills & Utilities'),
  ('Entertainment'),
  ('Healthcare'),
  ('Education'),
  ('Travel'),
  ('Other');
