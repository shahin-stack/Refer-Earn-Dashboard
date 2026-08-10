import sqlite3
import pandas as pd
import numpy as np

def generate_report():
    print("Loading Monthly DB...")
    conn_monthly = sqlite3.connect('monthly.db')
    df_monthly = pd.read_sql("SELECT [Mobile Number], [Point Given] FROM r_f_monthly", conn_monthly)
    conn_monthly.close()

    # Clean Mobile Number string
    df_monthly['Mobile Number'] = pd.to_numeric(df_monthly['Mobile Number'], errors='coerce').fillna(0).astype('int64').astype(str)

    # 1. Total Customer Count
    total_customer_count = df_monthly[df_monthly['Mobile Number'] != '0']['Mobile Number'].nunique()

    # 2. Total Bonus Point Given
    total_bonus_point_given = pd.to_numeric(df_monthly['Point Given'], errors='coerce').fillna(0).sum()

    print("Loading Detailed DB...")
    conn_detailed = sqlite3.connect('detailed_split.db')
    query = """
    SELECT [Customer Mobile], [Total Value], [POINT REDUMPTION (DEDUCTION)]
    FROM Detailed_split_1
    UNION ALL
    SELECT [Customer Mobile], [Total Value], [POINT REDUMPTION (DEDUCTION)]
    FROM Detailed_split_2
    """
    df_detailed = pd.read_sql(query, conn_detailed)
    conn_detailed.close()

    print("Processing Data...")
    # Clean Customer Mobile
    df_detailed['Customer Mobile'] = pd.to_numeric(df_detailed['Customer Mobile'], errors='coerce').fillna(0).astype('int64').astype(str)

    # Ensure numeric types
    df_detailed['Total Value'] = pd.to_numeric(df_detailed['Total Value'], errors='coerce').fillna(0)
    
    # Check if POINT REDUMPTION is negative or positive
    df_detailed['POINT REDUMPTION (DEDUCTION)'] = pd.to_numeric(df_detailed['POINT REDUMPTION (DEDUCTION)'], errors='coerce').fillna(0)
    
    # Sometimes deductions are represented as negative. Let's ensure we use their absolute magnitude if they are negative.
    # The requirement is POINT REDUMPTION (DEDUCTION) > 0. Let's check max vs min.
    if df_detailed['POINT REDUMPTION (DEDUCTION)'].max() <= 0 and df_detailed['POINT REDUMPTION (DEDUCTION)'].min() < 0:
        # It's coded as negative
        df_detailed['POINT REDUMPTION (DEDUCTION)'] = df_detailed['POINT REDUMPTION (DEDUCTION)'].abs()

    # valid_mobiles set
    valid_mobiles = set(df_monthly['Mobile Number'].unique())
    valid_mobiles.discard('0')

    # numbers which is in both files
    df_merged = df_detailed[df_detailed['Customer Mobile'].isin(valid_mobiles)]

    # 3. Total Purchase Count
    total_purchase_count = df_merged['Customer Mobile'].nunique()

    # Filter for redeemed > 0
    df_redeemed = df_merged[df_merged['POINT REDUMPTION (DEDUCTION)'] > 0]

    # 4. Total Redeemed Count
    total_redeemed_count = df_redeemed['Customer Mobile'].nunique()

    # 5. Total Point Redeemed Value
    total_point_redeemed_value = df_redeemed['POINT REDUMPTION (DEDUCTION)'].sum()

    # 6. Total Redeemed Purchase Value
    total_redeemed_purchase_value = df_redeemed['Total Value'].sum()

    # 7. Loyalty Point Discount % 
    loyalty_point_discount_pct = (total_point_redeemed_value / total_redeemed_purchase_value) * 100 if total_redeemed_purchase_value else 0

    # 8. Average Purchase Value
    average_purchase_value = total_redeemed_purchase_value / total_redeemed_count if total_redeemed_count else 0

    # 9. Average Loyalty Point Redemption
    average_loyalty_point_redemption = total_point_redeemed_value / total_redeemed_count if total_redeemed_count else 0

    print("\n--- REPORT OUTPUT ---\n")
    print("| Metric | Value |")
    print("|---|---|")
    print(f"| Total Customer Count | {total_customer_count:,.0f} |")
    print(f"| Total Bonus Point Given | {total_bonus_point_given:,.2f} |")
    print(f"| Total Purchase Count | {total_purchase_count:,.0f} |")
    print(f"| Total Redeemed Count | {total_redeemed_count:,.0f} |")
    print(f"| Total Point Redeemed Value | {total_point_redeemed_value:,.2f} |")
    print(f"| Total Redeemed Purchase Value | {total_redeemed_purchase_value:,.2f} |")
    print(f"| Loyalty Point Discount % | {loyalty_point_discount_pct:,.2f}% |")
    print(f"| Average Purchase Value | {average_purchase_value:,.2f} |")
    print(f"| Average Loyalty Point Redemption | {average_loyalty_point_redemption:,.2f} |")

    with open('report_output.txt', 'w') as f:
        f.write(f"Total Customer Count|{total_customer_count:,.0f}\n")
        f.write(f"Total Bonus Point Given|{total_bonus_point_given:,.2f}\n")
        f.write(f"Total Purchase Count|{total_purchase_count:,.0f}\n")
        f.write(f"Total Redeemed Count|{total_redeemed_count:,.0f}\n")
        f.write(f"Total Point Redeemed Value|{total_point_redeemed_value:,.2f}\n")
        f.write(f"Total Redeemed Purchase Value|{total_redeemed_purchase_value:,.2f}\n")
        f.write(f"Loyalty Point Discount %|{loyalty_point_discount_pct:,.2f}%\n")
        f.write(f"Average Purchase Value|{average_purchase_value:,.2f}\n")
        f.write(f"Average Loyalty Point Redemption|{average_loyalty_point_redemption:,.2f}\n")


if __name__ == '__main__':
    generate_report()
