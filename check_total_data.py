import sqlite3
import os

db = 'total data.db'
if not os.path.exists(db):
    print(f"File {db} not found.")
    exit(1)

size = os.path.getsize(db)

with open('db_output.txt', 'w', encoding='utf-8') as f:
    f.write(f"Database size: {size / (1024*1024):.2f} MB\n")

    try:
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cur.fetchall()]
        f.write(f"Tables found: {', '.join(tables)}\n")

        for t in tables:
            cur.execute(f'SELECT COUNT(*) FROM "{t}"')
            count = cur.fetchone()[0]
            f.write(f"Row count in '{t}': {count}\n")
    except sqlite3.Error as e:
        f.write(f"SQLite error: {e}\n")
    finally:
        if 'conn' in locals():
            conn.close()
