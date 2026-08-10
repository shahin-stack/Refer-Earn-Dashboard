import sqlite3
import pandas as pd
import json

def get_extensive_analytics():
    conn_det = sqlite3.connect('detailed_split.db')
    query = "SELECT Branch, Staff, [Customer Type], [Total Value], [POINT REDUMPTION (DEDUCTION)] FROM Detailed_split_1 UNION ALL SELECT Branch, Staff, [Customer Type], [Total Value], [POINT REDUMPTION (DEDUCTION)] FROM Detailed_split_2"
    df = pd.read_sql(query, conn_det)
    conn_det.close()

    # Clean data
    df['p'] = pd.to_numeric(df['POINT REDUMPTION (DEDUCTION)'], errors='coerce').fillna(0).abs()
    df['v'] = pd.to_numeric(df['Total Value'], errors='coerce').fillna(0)

    # 1. Branch Redemption Efficiency (Redemption Value / Total Sales Value)
    branch_stats = df.groupby('Branch').agg({'p': 'sum', 'v': 'sum', 'Customer Type': 'count'})
    branch_stats['efficiency'] = (branch_stats['p'] / branch_stats['v']) * 100
    top_efficient_branches = branch_stats.sort_values('efficiency', ascending=False).head(10)['efficiency'].to_dict()

    # 2. Staff Leaderboard (Top 10 by Points Redeemed)
    staff_leaderboard = df.groupby('Staff')['p'].sum().sort_values(ascending=False).head(10).to_dict()

    # 3. Customer Type Distribution
    cust_type_dist = df['Customer Type'].value_counts().head(5).to_dict()

    data = {
        "branch_redemption_efficiency": top_efficient_branches,
        "staff_leaderboard": staff_leaderboard,
        "customer_type_distribution": cust_type_dist
    }

    with open('dashboard_analytics_v2.json', 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == '__main__':
    get_extensive_analytics()
