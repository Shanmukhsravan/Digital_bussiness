import sqlite3
import mysql.connector
import os

# MySQL Details
MYSQL_DB = "cement_db"
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "123456789",
    "database": MYSQL_DB
}

# SQLite Path
SQLITE_PATH = r"D:\smartkirana\database.db"

def migrate():
    if not os.path.exists(SQLITE_PATH):
        print(f"[ERROR] SQLite file not found at {SQLITE_PATH}")
        return

    print("--- Starting Kirana Data Migration ---")
    
    # 1. Connect to SQLite
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_cursor = sqlite_conn.cursor()

    # 2. Connect to MySQL
    try:
        mysql_conn = mysql.connector.connect(**MYSQL_CONFIG)
        mysql_cursor = mysql_conn.cursor()
    except Exception as e:
        print(f"[ERROR] Could not connect to MySQL: {e}")
        return

    # 3. Create Tables in MySQL
    print("Creating tables in MySQL...")
    
    # kirana_products
    mysql_cursor.execute("""
        CREATE TABLE IF NOT EXISTS kirana_products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            variant VARCHAR(255) NOT NULL,
            cost_price DECIMAL(10, 2) NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            stock INT NOT NULL
        )
    """)

    # kirana_sales
    mysql_cursor.execute("""
        CREATE TABLE IF NOT EXISTS kirana_sales (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_id INT,
            quantity INT,
            date_time DATETIME,
            FOREIGN KEY (product_id) REFERENCES kirana_products(id)
        )
    """)

    # kirana_notifications
    mysql_cursor.execute("""
        CREATE TABLE IF NOT EXISTS kirana_notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            message TEXT,
            date_time DATETIME
        )
    """)

    # kirana_palm_wine
    mysql_cursor.execute("""
        CREATE TABLE IF NOT EXISTS kirana_palm_wine (
            id INT AUTO_INCREMENT PRIMARY KEY,
            date DATE,
            money_spent DECIMAL(10, 2),
            glasses_sold INT
        )
    """)

    # 4. Copy Products
    print("Migrating products...")
    sqlite_cursor.execute("SELECT id, name, variant, cost_price, price, stock FROM products")
    products = sqlite_cursor.fetchall()
    
    # We clear existing to avoid duplicates if re-run, or we could use REPLACE INTO
    mysql_cursor.execute("DELETE FROM kirana_sales")
    mysql_cursor.execute("DELETE FROM kirana_products")
    
    for p in products:
        mysql_cursor.execute(
            "INSERT INTO kirana_products (id, name, variant, cost_price, price, stock) VALUES (%s, %s, %s, %s, %s, %s)",
            p
        )

    # 5. Copy Sales
    print("Migrating sales...")
    sqlite_cursor.execute("SELECT product_id, quantity, date_time FROM sales")
    sales = sqlite_cursor.fetchall()
    for s in sales:
        # SQLite store date as string "2026-04-15 13:50:00.123456"
        mysql_cursor.execute(
            "INSERT INTO kirana_sales (product_id, quantity, date_time) VALUES (%s, %s, %s)",
            s
        )

    # 6. Copy Notifications
    print("Migrating notifications...")
    mysql_cursor.execute("DELETE FROM kirana_notifications")
    sqlite_cursor.execute("SELECT message, date_time FROM notifications")
    notes = sqlite_cursor.fetchall()
    for n in notes:
        mysql_cursor.execute(
            "INSERT INTO kirana_notifications (message, date_time) VALUES (%s, %s)",
            n
        )

    # 7. Copy Palm Wine
    print("Migrating palm wine records...")
    mysql_cursor.execute("DELETE FROM kirana_palm_wine")
    sqlite_cursor.execute("SELECT date, money_spent, glasses_sold FROM palm_wine")
    palms = sqlite_cursor.fetchall()
    for mw in palms:
        mysql_cursor.execute(
            "INSERT INTO kirana_palm_wine (date, money_spent, glasses_sold) VALUES (%s, %s, %s)",
            mw
        )

    mysql_conn.commit()
    print("[OK] Migration completed successfully!")

    sqlite_conn.close()
    mysql_conn.close()

if __name__ == "__main__":
    migrate()
