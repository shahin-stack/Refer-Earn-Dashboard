import sqlite3

conn = sqlite3.connect('database.db')
cur = conn.cursor()

# List all tables with 'refer' in the name
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cur.fetchall()]
print("All tables:", tables)

refer_tables = [t for t in tables if 'refer' in t.lower()]
print("Refer tables:", refer_tables)

for tbl in refer_tables:
    try:
        # Get columns
        cur.execute(f"PRAGMA table_info(\"{tbl}\")")
        cols = [c[1] for c in cur.fetchall()]
        print(f"\nTable: {tbl}")
        print(f"Columns: {cols}")
        
        # Try to find date column
        date_cols = [c for c in cols if 'date' in c.lower() or 'Date' in c or 'DATE' in c]
        print(f"Date columns: {date_cols}")
        
        for dc in date_cols:
            cur.execute(f'SELECT MIN("{dc}"), MAX("{dc}"), COUNT(*) FROM "{tbl}"')
            res = cur.fetchone()
            print(f"  [{dc}] Min: {res[0]}, Max: {res[1]}, Rows: {res[2]:,}")
        
        if not date_cols:
            cur.execute(f'SELECT COUNT(*) FROM "{tbl}"')
            cnt = cur.fetchone()[0]
            print(f"  Rows: {cnt:,}")
    except Exception as e:
        print(f"  Error: {e}")

conn.close()
