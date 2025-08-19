import psycopg2
import sys
from pprint import pprint

# Database connection configuration - Reused from data_ingestion.py
# ⚠️ Make sure this password is correct
DB_CONFIG = {
    'host': 'localhost',
    'database': 'trading_historical',
    'user': 'trading_bot',
    'password': 'your_secure_password'  
}

def get_db_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"❌ Database connection error: {e}")
        sys.exit(1)

def view_records(table_name, limit=20):
    """
    Connects to the database and prints the first N records from a table.
    """
    print(f"🔍 Viewing the first {limit} records from '{table_name}'...")
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # SQL query to select records
        query = f"SELECT * FROM {table_name} LIMIT {limit};"
        
        cur.execute(query)
        
        # Get column names
        column_names = [desc[0] for desc in cur.description]
        
        # Fetch the records
        records = cur.fetchall()
        
        if not records:
            print(f"⚠️ No records found in the table '{table_name}'.")
            return
        
        print("\n" + "=" * 50)
        print("📋 DATABASE RECORDS")
        print("=" * 50)
        print("Columns:", column_names)
        
        for i, record in enumerate(records):
            print("-" * 50)
            print(f"Record {i + 1}:")
            # Using a dictionary for better readability
            pprint(dict(zip(column_names, record)))
            
    except Exception as e:
        print(f"❌ An error occurred while fetching data: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Specify the table you want to view
    view_records(table_name='historical_prices')