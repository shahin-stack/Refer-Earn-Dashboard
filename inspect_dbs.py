import sqlite3

# Inspect 'total data.db'
print('=== total data.db ===')
conn = sqlite3.connect('total data.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Tables:', [t[0] for t in tables])
for t in tables:
    tname = t[0]
    cols = conn.execute(f'PRAGMA table_info("{tname}")').fetchall()
    print(f'  [{tname}] columns:', [c[1] for c in cols])
    count = conn.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
    print(f'  [{tname}] row count:', count)
    # Sample 2 rows
    sample = conn.execute(f'SELECT * FROM "{tname}" LIMIT 2').fetchall()
    for row in sample:
        print('   sample row:', row)
conn.close()

print()
print('=== monthly.db ===')
conn2 = sqlite3.connect('monthly.db')
tables2 = conn2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Tables:', [t[0] for t in tables2])
for t in tables2:
    tname = t[0]
    cols = conn2.execute(f'PRAGMA table_info("{tname}")').fetchall()
    print(f'  [{tname}] columns:', [c[1] for c in cols])
    count2 = conn2.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
    print(f'  [{tname}] row count:', count2)
    sample2 = conn2.execute(f'SELECT * FROM "{tname}" LIMIT 2').fetchall()
    for row in sample2:
        print('   sample row:', row)
conn2.close()
