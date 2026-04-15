from models import connect

def migrate():
    conn = connect()
    c = conn.cursor()
    try:
        # Check if columns exist
        c.execute("DESCRIBE sales")
        columns = [col[0] for col in c.fetchall()]
        
        if 'customer_name' not in columns:
            print("Adding customer_name column...")
            c.execute("ALTER TABLE sales ADD COLUMN customer_name VARCHAR(255)")
        
        if 'customer_village' not in columns:
            print("Adding customer_village column...")
            c.execute("ALTER TABLE sales ADD COLUMN customer_village VARCHAR(255)")
            
        conn.commit()
        print("Migration completed successfully.")
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
