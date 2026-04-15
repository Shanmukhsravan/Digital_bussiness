import mysql.connector
from werkzeug.security import generate_password_hash
import os

# Database configs with fallbacks to local
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '123456789')
DB_NAME = os.environ.get('DB_NAME', 'cement_db')
DB_PORT = os.environ.get('DB_PORT', '3306')

def connect(): 
    # Attempt to connect to MySQL
    try:
        # If port is custom (like Aiven), cast to int
        port_int = int(DB_PORT)
        
        return mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=port_int,
            ssl_disabled=False if 'aiven' in DB_HOST.lower() else True # Auto-enable SSL for Aiven
        )
    except mysql.connector.Error as err:
        print(f"Error connecting to DB: {err}")
        # Fallback for local creation if DB doesn't exist yet
        if err.errno == 1049: # Unknown database
             conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=int(DB_PORT))
             cursor = conn.cursor()
             cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
             cursor.close()
             conn.close()
             return mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME, port=int(DB_PORT))
        raise err

def init_db(): 
    conn = connect() 
    c = conn.cursor() 

    # Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(255) UNIQUE,
        password VARCHAR(255),
        role VARCHAR(50)
    )''')

    # Stock Table
    c.execute('''CREATE TABLE IF NOT EXISTS stock ( 
        id INT AUTO_INCREMENT PRIMARY KEY, 
        brand VARCHAR(255), 
        quantity INT, 
        price FLOAT 
    )''') 

    # Sales Table
    c.execute('''CREATE TABLE IF NOT EXISTS sales ( 
        id INT AUTO_INCREMENT PRIMARY KEY, 
        brand VARCHAR(255), 
        quantity INT, 
        price FLOAT, 
        date VARCHAR(255),
        customer_name VARCHAR(255),
        customer_village VARCHAR(255),
        customer_phone VARCHAR(50),
        payment_method VARCHAR(50),
        profit_type VARCHAR(50),
        profit_value FLOAT,
        load_source VARCHAR(255)
    )''') 

    # Margins Table (Settings for profit)
    c.execute('''CREATE TABLE IF NOT EXISTS margins (
        brand VARCHAR(255) PRIMARY KEY,
        profit_type VARCHAR(50),
        profit_value FLOAT
    )''')

    # Loads Table (Batch arrivals)
    c.execute('''CREATE TABLE IF NOT EXISTS loads (
        id INT AUTO_INCREMENT PRIMARY KEY,
        brand VARCHAR(255),
        quantity INT,
        date VARCHAR(255),
        load_name VARCHAR(255)
    )''')

    # Waste Table
    c.execute('''CREATE TABLE IF NOT EXISTS waste (
        id INT AUTO_INCREMENT PRIMARY KEY,
        brand VARCHAR(255),
        quantity INT,
        date VARCHAR(255),
        reason VARCHAR(255)
    )''')

    # --- Smart Kirana Tables ---
    # kirana_products
    c.execute("""
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
    c.execute("""
        CREATE TABLE IF NOT EXISTS kirana_sales (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_id INT,
            quantity INT,
            date_time DATETIME,
            FOREIGN KEY (product_id) REFERENCES kirana_products(id)
        )
    """)

    # kirana_notifications
    c.execute("""
        CREATE TABLE IF NOT EXISTS kirana_notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            message TEXT,
            date_time DATETIME
        )
    """)

    # kirana_palm_wine
    c.execute("""
        CREATE TABLE IF NOT EXISTS kirana_palm_wine (
            id INT AUTO_INCREMENT PRIMARY KEY,
            date DATE,
            money_spent DECIMAL(10, 2),
            glasses_sold INT
        )
    """)

    # Initial Users
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        admin_pass = generate_password_hash("raju1234")
        staff_pass = generate_password_hash("123456789")
        c.execute("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)", ("rajanna", admin_pass, "admin"))
        c.execute("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)", ("staff", staff_pass, "shopkeep"))

    conn.commit() 
    conn.close()

def reset_inventory():
    conn = connect()
    c = conn.cursor()
    
    # 1. Clear old data
    c.execute("DELETE FROM stock")
    c.execute("DELETE FROM sales")
    c.execute("DELETE FROM loads")
    c.execute("DELETE FROM waste")
    c.execute("DELETE FROM margins")

    # 2. Insert Initial Loads
    c.execute("INSERT INTO loads (brand, quantity, date, load_name) VALUES (%s,%s,%s,%s)", ("JK Super", 500, "2026-04-14", "Initial Stock"))
    c.execute("INSERT INTO loads (brand, quantity, date, load_name) VALUES (%s,%s,%s,%s)", ("Nagarjuna", 40, "2026-04-14", "Initial Stock"))

    # 3. Set Current Stock (User requested: 91 JK Super, 20 Nagarjuna)
    c.execute("INSERT INTO stock (brand, quantity, price) VALUES (%s,%s,%s)", ("JK Super", 91, 450.0))
    c.execute("INSERT INTO stock (brand, quantity, price) VALUES (%s,%s,%s)", ("Nagarjuna", 20, 450.0))

    # 4. Set Default Margins
    c.execute("INSERT INTO margins (brand, profit_type, profit_value) VALUES (%s,%s,%s)", ("JK Super", "rupees", 40.0))
    c.execute("INSERT INTO margins (brand, profit_type, profit_value) VALUES (%s,%s,%s)", ("Nagarjuna", "rupees", 35.0))

    conn.commit()
    conn.close()
    print("Database wiped and inventory reset successfully.")