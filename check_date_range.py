import sqlite3
import pandas as pd

def check_dates():
    conn = sqlite3.connect('detailed_split.db')
    df1 = pd.read_sql("SELECT [Date] FROM Detailed_split_1", conn)
    df2 = pd.read_sql("SELECT [Date] FROM Detailed_split_2", conn)
    conn.close()
    
    df = pd.concat([df1, df2])
    # The format is DD-MM-YYYY based on earlier investigation
    df['dt'] = pd.to_datetime(df['Date'], format='%d-%m-%Y', errors='coerce')
    
    print(f"Min Date: {df['dt'].min()}")
    print(f"Max Date: {df['dt'].max()}")
    print(f"Unique Dates: {df['dt'].nunique()}")

if __name__ == '__main__':
    check_dates()
