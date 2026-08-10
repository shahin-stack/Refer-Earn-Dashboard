import sqlite3
import pandas as pd

def check_dates():
    conn_det = sqlite3.connect('detailed_split.db')
    df_det = pd.read_sql("SELECT [Date], [Customer Mobile], [POINT REDUMPTION (DEDUCTION)], [Total Value] FROM Detailed_split_1 UNION ALL SELECT [Date], [Customer Mobile], [POINT REDUMPTION (DEDUCTION)], [Total Value] FROM Detailed_split_2", conn_det)
    conn_det.close()

    # Find unique dates and their counts
    print("Top 10 Dates by Count:")
    print(df_det['Date'].value_counts().head(10))
    
    # Min/Max dates
    print(f"Min Date: {df_det['Date'].min()}")
    print(f"Max Date: {df_det['Date'].max()}")

if __name__ == '__main__':
    check_dates()
