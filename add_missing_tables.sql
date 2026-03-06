-- ============================================================
-- Add Missing Tables to Existing Database
-- Run this in your MySQL client or via command line
-- ============================================================

USE finance_tracker;

-- Create notifications table
CREATE TABLE IF NOT EXISTS notifications (
  notification_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  notification_type VARCHAR(50) NOT NULL,
  message TEXT NOT NULL,
  budget_id INT,
  is_read BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (budget_id) REFERENCES budget(budget_id) ON DELETE SET NULL
);

-- Create categories table if it doesn't exist
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

-- Add category_id column to expense table if it doesn't exist
-- First check if column exists, if not add it
SET @dbname = DATABASE();
SET @tablename = 'expense';
SET @columnname = 'category_id';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' INT')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Add foreign key for category_id if it doesn't exist
-- Note: This might fail if foreign key already exists, that's okay
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (constraint_name LIKE '%category_id%')
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE SET NULL')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

SELECT 'Tables and columns added successfully!' AS status;

