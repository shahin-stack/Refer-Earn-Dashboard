import sqlite3

# Check database.db for sale_data table
conn = sqlite3.connect('database.db')
all_tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('All tables in database.db:', [t[0] for t in all_tables])

sale_tables = [t[0] for t in all_tables if 'sale' in t[0].lower()]
print('Sale-related tables:', sale_tables)

if sale_tables:
    for tbl in sale_tables:
        try:
            cols = conn.execute(f'PRAGMA table_info("{tbl}")').fetchall()
            col_names = [c[1] for c in cols]
            print(f'\nTable: {tbl}')
            print(f'Columns: {col_names}')
            # Try common date column names
            date_cols = [c for c in col_names if any(x in c.lower() for x in ['date', 'time', 'created', 'updated'])]
            print(f'Date columns: {date_cols}')
            for dc in date_cols:
                result = conn.execute(f'SELECT MIN("{dc}"), MAX("{dc}"), COUNT(*) FROM "{tbl}"').fetchone()
                print(f'  {dc}: min={result[0]}, max={result[1]}, rows={result[2]:,}')
        except Exception as e:
            print(f'Error querying {tbl}: {e}')
else:
    print('No sale_data table found in database.db')
    # Show sample of all tables
    print('Looking in detailed_split.db...')

conn.close()

# Also check detailed_split.db
conn2 = sqlite3.connect('detailed_split.db')
all_tables2 = conn2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('\nAll tables in detailed_split.db:', [t[0] for t in all_tables2])
sale_tables2 = [t[0] for t in all_tables2 if 'sale' in t[0].lower()]
print('Sale-related tables:', sale_tables2)

for tbl in all_tables2[:5]:
    try:
        cols = conn2.execute(f'PRAGMA table_info("{tbl[0]}")').fetchall()
        col_names = [c[1] for c in cols]
        date_cols = [c for c in col_names if any(x in c.lower() for x in ['date', 'time', 'created', 'updated'])]
        if date_cols:
            print(f'\nTable: {tbl[0]}, Date cols: {date_cols}')
            for dc in date_cols:
                result = conn2.execute(f'SELECT MIN("{dc}"), MAX("{dc}"), COUNT(*) FROM "{tbl[0]}"').fetchone()
                print(f'  {dc}: min={result[0]}, max={result[1]}, rows={result[2]:,}')
    except Exception as e:
        print(f'Error: {e}')

conn2.close()
