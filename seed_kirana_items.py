import mysql.connector

# MySQL Details
MYSQL_DB = "cement_db"
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "123456789",
    "database": MYSQL_DB
}

items_to_seed = [
    ("Gold black box", "Box", 150.0),
    ("Gold black box", "Single", 15.0),
    ("Total cigarette", "Box", 100.0),
    ("Total cigarette", "Single", 10.0),
    ("Raj niwas (3+3)", "Pack", 20.0),
    ("Vimal (3 packs)", "Pack", 20.0),
    ("Delux (3 packs)", "Pack", 20.0),
    ("Beedi", "Single", 10.0),
    ("Kaini", "Piece", 10.0),
    ("Egg", "1 Piece", 7.0),
    ("Butter day biscuit", "Piece", 20.0),
    ("Butter bake biscuit", "Piece", 5.0),
    ("Parle G", "Piece", 10.0),
    ("Match stick", "Single", 2.0),
    ("Match stick", "Box", 25.0),
    ("Match stick", "10 Box Pack", 200.0),
    ("Lighter", "Piece", 10.0),
    ("Milli maker 150g", "Piece", 20.0),
    ("Glass", "1 Piece", 3.0),
    ("Chegodi", "Piece", 10.0),
    ("Elachi rusk biscuit", "Piece", 10.0),
    ("Washing soap", "Piece", 20.0),
    ("Candle", "1 Piece", 5.0),
    ("Monster drink", "Piece", 100.0),
    ("Monster mini", "Piece", 30.0),
    ("Freedom oil 1/2 Ltr", "Piece", 100.0),
    ("Soyabean oil 1/2 Ltr", "Piece", 80.0),
    ("Dish soap", "Piece", 5.0),
    ("Gillet blade", "Piece", 10.0),
    ("Pampers", "Piece", 10.0),
    ("Mango ice cream", "Piece", 10.0),
    ("Choco bar", "Piece", 20.0),
    ("Milk powder", "Piece", 10.0),
    ("Egg masala", "Piece", 5.0),
    ("Sugar 1kg", "Bag", 50.0),
    ("Batani 1kg", "Bag", 50.0),
    ("Bag", "Piece", 20.0),
    ("Pappu 1kg", "Bag", 100.0),
    ("Pen", "Piece", 5.0),
    ("Coconut oil", "Piece", 10.0),
    ("Vaseline 5/-", "Piece", 5.0),
    ("Vaseline 10/-", "Piece", 10.0),
    ("Petrol", "Half", 60.0),
    ("Petrol", "Full", 120.0),
    ("Brush 16/-", "Piece", 16.0),
    ("Brush 11/-", "Piece", 11.0),
    ("Tongue cleaner", "Piece", 10.0),
    ("Ujala", "Piece", 25.0),
    ("Battery", "Piece", 12.0),
    ("Curry paste non-veg", "Piece", 10.0),
    ("Campa cola drink", "Piece", 25.0),
    ("Pickles", "Piece", 10.0),
    ("Agarabathi", "Piece", 10.0),
    ("Godrej hair colour", "1 Piece", 15.0),
    ("Salt", "Piece", 20.0),
    ("Champa agarabathi set", "Set", 50.0),
    ("Mogra agarabathi box", "Box", 30.0),
    ("Bulb", "Piece", 20.0),
    ("Velluli 1kg", "Bag", 150.0),
    ("Nippi bulb", "Piece", 100.0),
    ("Adrenaline rush drink", "Piece", 50.0),
]

def seed():
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    c = conn.cursor()

    print("Seeding kirana items...")
    for name, variant, price in items_to_seed:
        cost_price = price * 0.9  # Placeholder 10% margin
        stock = 50  # Initial stock placeholder
        
        # Check if exists
        c.execute("SELECT id FROM kirana_products WHERE name=%s AND variant=%s", (name, variant))
        exists = c.fetchone()
        
        if exists:
            c.execute("UPDATE kirana_products SET price=%s, cost_price=%s WHERE id=%s", 
                      (price, cost_price, exists[0]))
        else:
            c.execute("INSERT INTO kirana_products (name, variant, price, cost_price, stock) VALUES (%s,%s,%s,%s,%s)",
                      (name, variant, price, cost_price, stock))

    conn.commit()
    conn.close()
    print("Done!")

if __name__ == "__main__":
    seed()
