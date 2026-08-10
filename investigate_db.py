import sqlite3
import pandas as pd

def check_db():
    conn = sqlite3.connect('detailed_split.db')
    
    print("Checking Detailed_split_1...")
    df1 = pd.read_sql("SELECT [Customer Mobile] FROM Detailed_split_1", conn)
    print(f"Total rows in Split 1: {len(df1)}")
    print(f"Unique mobiles in Split 1: {df1['Customer Mobile'].nunique()}")
    
    print("\nChecking Detailed_split_2...")
    df2 = pd.read_sql("SELECT [Customer Mobile] FROM Detailed_split_2", conn)
    print(f"Total rows in Split 2: {len(df2)}")
    print(f"Unique mobiles in Split 2: {df2['Customer Mobile'].nunique()}")
    
    conn.close()

if __name__ == "__main__":
    check_db()
