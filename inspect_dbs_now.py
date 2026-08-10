import sqlite3
import pandas as pd

# ── monthly.db ──────────────────────────────────────────────
print('='*60)
print('DATABASE: monthly.db')
print('='*60)
conn = sqlite3.connect('monthly.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print(f'Tables: {[t[0] for t in tables]}')
for t in tables:
    tname = t[0]
    count = conn.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
    cols  = [c[1] for c in conn.execute(f'PRAGMA table_info("{tname}")').fetchall()]
    print(f'\nTable: {tname}  |  Rows: {count:,}')
    print(f'Columns: {cols}')
    df = pd.read_sql(f'SELECT * FROM "{tname}" LIMIT 5', conn)
    print(df.to_string(index=False))
conn.close()

print()
print('='*60)
print('DATABASE: detailed_split.db')
print('='*60)
conn2 = sqlite3.connect('detailed_split.db')
tables2 = conn2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
table_names = [t[0] for t in tables2 if t[0] != 'sqlite_sequence']
print(f'Tables ({len(table_names)} total): {table_names}')
for t in table_names:
    count = conn2.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    cols  = [c[1] for c in conn2.execute(f'PRAGMA table_info("{t}")').fetchall()]
    print(f'\nTable: {t}  |  Rows: {count:,}')
    print(f'Columns: {cols}')
    df = pd.read_sql(f'SELECT * FROM "{t}" LIMIT 5', conn2)
    print(df.to_string(index=False))
conn2.close()
