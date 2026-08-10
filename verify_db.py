import sqlite3
import os
import json

result = {}
for db in ['detailed_split.db', 'monthly.db']:
    if not os.path.exists(db):
        result[db] = 'NOT FOUND'
        continue
    size_kb = round(os.path.getsize(db) / 1024, 1)
    conn = sqlite3.connect(db)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    db_info = {'size_kb': size_kb, 'tables': []}
    for t in tables:
        tname = t[0]
        cnt = conn.execute('SELECT COUNT(*) FROM "' + tname + '"').fetchone()[0]
        cols = [d[1] for d in conn.execute('PRAGMA table_info("' + tname + '")').fetchall()]
        db_info['tables'].append({'name': tname, 'rows': cnt, 'columns': cols})
    conn.close()
    result[db] = db_info

with open('verify_result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
print('Done')
