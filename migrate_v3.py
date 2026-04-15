from models import connect

def migrate():
    conn = connect()
    c = conn.cursor()
    try:
        # Check if column exists
        c.execute("DESCRIBE sales")
        columns = [col[0] for col in c.fetchall()]
        
        if 'payment_method' not in columns:
            print("Adding payment_method column...")
            c.execute("ALTER TABLE sales ADD COLUMN payment_method VARCHAR(50)")
            conn.commit()
            print("Migration completed successfully.")
        else:
            print("payment_method column already exists.")
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
