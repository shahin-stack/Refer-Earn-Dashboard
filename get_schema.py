import sqlite3

out = open('schema_result.txt', 'w', encoding='utf-8')

# total data.db
conn = sqlite3.connect('total data.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
out.write('TOTAL DATA DB TABLES:\n')
for t in tables:
    out.write('  ' + t[0] + '\n')
    cols = conn.execute(f'PRAGMA table_info("{t[0]}")').fetchall()
    for c in cols:
        out.write(f'    col[{c[0]}]: {c[1]}\n')
    cnt = conn.execute(f'SELECT COUNT(*) FROM "{t[0]}"').fetchone()[0]
    out.write(f'    row count: {cnt}\n')
conn.close()

out.write('\n')

# monthly.db
conn2 = sqlite3.connect('monthly.db')
tables2 = conn2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
out.write('MONTHLY DB TABLES:\n')
for t in tables2:
    out.write('  ' + t[0] + '\n')
    cols2 = conn2.execute(f'PRAGMA table_info("{t[0]}")').fetchall()
    for c in cols2:
        out.write(f'    col[{c[0]}]: {c[1]}\n')
    cnt2 = conn2.execute(f'SELECT COUNT(*) FROM "{t[0]}"').fetchone()[0]
    out.write(f'    row count: {cnt2}\n')
conn2.close()

out.close()
print('Done')
