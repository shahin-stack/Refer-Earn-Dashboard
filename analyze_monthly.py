import sqlite3
import pandas as pd

def analyze_monthly():
    conn = sqlite3.connect('monthly.db')
    # Get column names
    cursor = conn.execute("SELECT * FROM r_f_monthly LIMIT 1")
    cols = [description[0] for description in cursor.description]
    print(f"Monthly DB Columns: {cols}")
    
    df = pd.read_sql("SELECT * FROM r_f_monthly LIMIT 10", conn)
    conn.close()
    # Print sample data
    print(df.head())

if __name__ == '__main__':
    analyze_monthly()
