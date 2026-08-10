import sqlite3
import os

print('\n=== Database Row Counts ===')

for db in ['detailed_split.db', 'monthly.db']:
    if not os.path.exists(db):
        print(f'{db} not found.')
        continue
        
    print(f'\nDatabase: {db}')
    print('-' * 40)
    
    conn = sqlite3.connect(db)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    
    total_db_rows = 0
    for table in tables:
        tname = table[0]
        cnt = conn.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
        print(f'Table: {tname:<20} | Rows: {cnt:,}')
        total_db_rows += cnt
        
    print('-' * 40)
    print(f'Total Rows in {db}: {total_db_rows:,}')
    conn.close()
