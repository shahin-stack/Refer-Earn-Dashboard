import sqlite3

def explore_db():
    conn = sqlite3.connect('detailed_split.db')
    cursor = conn.cursor()
    
    # List tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"Tables: {tables}")
    
    for table_name in [t[0] for t in tables]:
        print(f"\nTable: {table_name}")
        cursor.execute(f"PRAGMA table_info([{table_name}])")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  Column: {col[1]} ({col[2]})")
            
        cursor.execute(f"SELECT count(*) FROM [{table_name}]")
        print(f"  Total rows: {cursor.fetchone()[0]}")
        
        cursor.execute(f"SELECT [Date], [Customer Mobile] FROM [{table_name}] LIMIT 5")
        print(f"  Samples: {cursor.fetchall()}")

    conn.close()

if __name__ == "__main__":
    explore_db()
