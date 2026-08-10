import sqlite3

def check_mobs():
    conn = sqlite3.connect('detailed_split.db')
    cursor = conn.cursor()
    
    for table in ['Detailed_split_1', 'Detailed_split_2']:
        print(f"\nTop 10 mobiles in {table}:")
        cursor.execute(f"SELECT [Customer Mobile], count(*) FROM {table} GROUP BY [Customer Mobile] ORDER BY count(*) DESC LIMIT 10")
        print(cursor.fetchall())
        
        print(f"Count of distinct mobiles in {table}:")
        cursor.execute(f"SELECT count(distinct [Customer Mobile]) FROM {table}")
        print(cursor.fetchone()[0])

    conn.close()

if __name__ == "__main__":
    check_mobs()
