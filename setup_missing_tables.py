"""
Script to add missing tables to existing database
Run this once to set up the notifications and categories tables
"""
import mysql.connector
import config

def setup_tables():
    try:
        db = mysql.connector.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME
        )
        cursor = db.cursor()
        
        print("Creating notifications table...")
        cursor.execute("""
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
            )
        """)
        
        print("Creating categories table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
              category_id INT AUTO_INCREMENT PRIMARY KEY,
              name VARCHAR(100) NOT NULL UNIQUE
            )
        """)
        
        print("Inserting default categories...")
        categories = [
            'Food & Dining',
            'Transportation',
            'Shopping',
            'Bills & Utilities',
            'Entertainment',
            'Healthcare',
            'Education',
            'Travel',
            'Other'
        ]
        
        for cat in categories:
            cursor.execute("INSERT IGNORE INTO categories (name) VALUES (%s)", (cat,))
        
        print("Checking if category_id column exists in expense table...")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'expense' 
            AND COLUMN_NAME = 'category_id'
        """, (config.DB_NAME,))
        
        if cursor.fetchone()[0] == 0:
            print("Adding category_id column to expense table...")
            cursor.execute("ALTER TABLE expense ADD COLUMN category_id INT")
            cursor.execute("""
                ALTER TABLE expense 
                ADD FOREIGN KEY (category_id) 
                REFERENCES categories(category_id) 
                ON DELETE SET NULL
            """)
        else:
            print("category_id column already exists in expense table.")
        
        db.commit()
        print("\n✅ All tables created successfully!")
        print("You can now run your Flask app.")
        
    except mysql.connector.Error as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()

if __name__ == '__main__':
    setup_tables()

