import sqlite3
import sys

out = open('inspect_out2.txt', 'w', encoding='utf-8')

def p(msg):
    out.write(str(msg) + '\n')

# Inspect 'total data.db'
p('=== total data.db ===')
conn = sqlite3.connect('total data.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
p('Tables: ' + str([t[0] for t in tables]))
for t in tables:
    tname = t[0]
    cols = conn.execute(f'PRAGMA table_info("{tname}")').fetchall()
    p(f'  [{tname}] columns: ' + str([c[1] for c in cols]))
    count = conn.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
    p(f'  [{tname}] row count: {count}')
    sample = conn.execute(f'SELECT * FROM "{tname}" LIMIT 2').fetchall()
    for row in sample:
        p('   sample: ' + str(row))
conn.close()

p('')
p('=== monthly.db ===')
conn2 = sqlite3.connect('monthly.db')
tables2 = conn2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
p('Tables: ' + str([t[0] for t in tables2]))
for t in tables2:
    tname = t[0]
    cols = conn2.execute(f'PRAGMA table_info("{tname}")').fetchall()
    p(f'  [{tname}] columns: ' + str([c[1] for c in cols]))
    count2 = conn2.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
    p(f'  [{tname}] row count: {count2}')
    sample2 = conn2.execute(f'SELECT * FROM "{tname}" LIMIT 2').fetchall()
    for row in sample2:
        p('   sample: ' + str(row))
conn2.close()

out.close()
print('Done. Check inspect_out2.txt')
