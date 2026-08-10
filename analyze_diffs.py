import sqlite3
import pandas as pd

def find_common_points():
    conn_det = sqlite3.connect('detailed_split.db')
    df_det = pd.read_sql("SELECT [POINT REDUMPTION (DEDUCTION)] FROM Detailed_split_1 UNION ALL SELECT [POINT REDUMPTION (DEDUCTION)] FROM Detailed_split_2", conn_det)
    conn_det.close()

    df_det['p'] = pd.to_numeric(df_det['POINT REDUMPTION (DEDUCTION)'], errors='coerce').fillna(0).abs()
    
    # Check for value 1830 or values that sum to 29280 across 16 customers
    red_vals = df_det[df_det['p'] > 0]['p']
    print("Most common redemption values:")
    print(red_vals.value_counts().head(20))
    
    # Check if 1830 exists
    if 1830 in red_vals.values:
        print("\nValue 1,830 exists in the data!")
        print(f"Frequency of 1,830: {len(red_vals[red_vals == 1830])}")
    else:
        print("\nValue 1,830 not found.")

if __name__ == '__main__':
    find_common_points()
