"""
Migration V4: Seed historical business data (CORRECTED)
- February: Load 1 - 200 bags JK Super, bought at 265, margin 35, sell at 300
- March: Load 2 - 300 bags JK Super, margin 35 + 40 bags Nagarjuna, margin 40, sell at 380
- Total sold: 427 bags (20 Nagarjuna, 407 JK Super)
- Waste: 3 bags JK Super
- Remaining stock: JK Super = 500 - 407 - 3 = 90, Nagarjuna = 40 - 20 = 20
"""
from models import connect

def seed_history():
    conn = connect()
    c = conn.cursor()

    # 1. Clear ALL existing data
    c.execute("DELETE FROM stock")
    c.execute("DELETE FROM sales")
    c.execute("DELETE FROM loads")
    c.execute("DELETE FROM waste")
    c.execute("DELETE FROM margins")

    # ========== LOADS ==========
    c.execute("INSERT INTO loads (brand, quantity, date, load_name) VALUES (%s,%s,%s,%s)",
              ("JK Super", 200, "2026-02-01", "February Load 1"))
    c.execute("INSERT INTO loads (brand, quantity, date, load_name) VALUES (%s,%s,%s,%s)",
              ("JK Super", 300, "2026-03-01", "March Load 2"))
    c.execute("INSERT INTO loads (brand, quantity, date, load_name) VALUES (%s,%s,%s,%s)",
              ("Nagarjuna", 40, "2026-03-01", "March Load 2"))

    # ========== MARGINS ==========
    c.execute("INSERT INTO margins (brand, profit_type, profit_value) VALUES (%s,%s,%s)",
              ("JK Super", "rupees", 35.0))
    c.execute("INSERT INTO margins (brand, profit_type, profit_value) VALUES (%s,%s,%s)",
              ("Nagarjuna", "rupees", 40.0))

    # ========== SALES ==========
    # February: 200 bags JK Super sold across Feb
    feb_jk_sold = 200
    for i in range(1, 29):
        day_qty = feb_jk_sold // 28
        if i <= feb_jk_sold % 28:
            day_qty += 1
        if day_qty > 0:
            date_str = f"2026-02-{i:02d}"
            pay = "Cash" if i % 3 != 0 else "UPI"
            c.execute("""INSERT INTO sales 
                (brand, quantity, price, date, customer_name, customer_village, customer_phone, 
                 payment_method, profit_type, profit_value, load_source) 
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                ("JK Super", day_qty, 300.0, date_str, f"Customer F{i}", "Village", "",
                 pay, "rupees", 35.0, "February Load 1"))

    # March: 207 JK Super + 20 Nagarjuna = 227 sold in March
    march_jk_sold = 207
    for i in range(1, 32):
        day_qty = march_jk_sold // 31
        if i <= march_jk_sold % 31:
            day_qty += 1
        if day_qty > 0:
            date_str = f"2026-03-{i:02d}"
            pay = "Cash" if i % 4 != 0 else "UPI"
            c.execute("""INSERT INTO sales 
                (brand, quantity, price, date, customer_name, customer_village, customer_phone, 
                 payment_method, profit_type, profit_value, load_source) 
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                ("JK Super", day_qty, 300.0, date_str, f"Customer M{i}", "Village", "",
                 pay, "rupees", 35.0, "March Load 2"))

    # Nagarjuna sales in March: 20 bags at 380
    for i in range(5, 25):
        date_str = f"2026-03-{i:02d}"
        pay = "Cash" if i % 2 == 0 else "UPI"
        c.execute("""INSERT INTO sales 
            (brand, quantity, price, date, customer_name, customer_village, customer_phone, 
             payment_method, profit_type, profit_value, load_source) 
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            ("Nagarjuna", 1, 380.0, date_str, f"Customer N{i}", "Village", "",
             pay, "rupees", 40.0, "March Load 2"))

    # ========== WASTE ==========
    c.execute("INSERT INTO waste (brand, quantity, date, reason) VALUES (%s,%s,%s,%s)",
              ("JK Super", 3, "2026-03-15", "Damaged during transport"))

    # ========== CURRENT STOCK ==========
    # JK Super: 200 + 300 - 407 - 3 = 90
    c.execute("INSERT INTO stock (brand, quantity, price) VALUES (%s,%s,%s)",
              ("JK Super", 90, 300.0))
    # Nagarjuna: 40 - 20 = 20
    c.execute("INSERT INTO stock (brand, quantity, price) VALUES (%s,%s,%s)",
              ("Nagarjuna", 20, 380.0))

    conn.commit()
    conn.close()
    print("[OK] Historical data seeded successfully!")
    print("   Loads: Feb (200 JK Super), Mar (300 JK Super + 40 Nagarjuna)")
    print("   Sales: 427 total (407 JK Super @ Rs.300, 20 Nagarjuna @ Rs.380)")
    print("   Waste: 3 bags JK Super")
    print("   Stock: 90 JK Super, 20 Nagarjuna")

if __name__ == "__main__":
    seed_history()
