import sqlite3
import pandas as pd
import json

def get_dashboard_data():
    conn_det = sqlite3.connect('detailed_split.db')
    query = "SELECT Branch, [Date], [Total Value], [POINT REDUMPTION (DEDUCTION)] FROM Detailed_split_1 UNION ALL SELECT Branch, [Date], [Total Value], [POINT REDUMPTION (DEDUCTION)] FROM Detailed_split_2"
    df = pd.read_sql(query, conn_det)
    conn_det.close()

    # Branch counts
    branch_counts = df.groupby('Branch')['Total Value'].count().sort_values(ascending=False).head(10).to_dict()
    
    # Branch values
    branch_values = df.groupby('Branch')['Total Value'].sum().sort_values(ascending=False).head(10).to_dict()

    # Time series (Grouped by Date)
    # Date is likely string DD-MM-YYYY
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y', errors='coerce')
    df_time = df.groupby(df['Date'].dt.date)['Total Value'].sum().tail(15).to_dict()

    data = {
        "top_branches_count": branch_counts,
        "top_branches_value": branch_values,
        "recent_time_series": {str(k): v for k, v in df_time.items()}
    }

    with open('dashboard_data.json', 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == '__main__':
    get_dashboard_data()
