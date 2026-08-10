import sqlite3

with open('tables_output.txt', 'w') as f:
    conn = sqlite3.connect('detailed_split.db')
    tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    f.write(f"detailed_split.db tables: {tables}\n")
    for t in tables:
        count = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        f.write(f"  {t}: {count} rows\n")
    conn.close()

    conn = sqlite3.connect('monthly.db')
    tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    f.write(f"monthly.db tables: {tables}\n")
    for t in tables:
        count = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        f.write(f"  {t}: {count} rows\n")
    conn.close()
