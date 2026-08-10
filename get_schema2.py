import sqlite3

out = open('schema_result2.txt', 'w', encoding='utf-8')

conn = sqlite3.connect('total data.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
out.write('TOTAL DATA DB - Full column info:\n')
for t in tables:
    tname = t[0]
    out.write(f'\nTable: {repr(tname)}\n')
    cols = conn.execute(f'PRAGMA table_info("{tname}")').fetchall()
    for c in cols:
        # c[0]=cid, c[1]=name, c[2]=type
        out.write(f'  cid={c[0]}, name={repr(c[1])}, type={repr(c[2])}\n')
    cnt = conn.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
    out.write(f'  total rows: {cnt}\n')
    # sample first row
    row = conn.execute(f'SELECT * FROM "{tname}" LIMIT 1').fetchone()
    out.write(f'  sample row: {row}\n')
conn.close()

out.close()
print('Done')
