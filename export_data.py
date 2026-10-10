import sqlite3
import pandas as pd

def export_data():
    print("Loading Monthly DB...")
    conn_monthly = sqlite3.connect('monthly.db')
    df_monthly = pd.read_sql("SELECT [Mobile] FROM r_f_monthly", conn_monthly)
    conn_monthly.close()

    df_monthly['Mobile'] = pd.to_numeric(df_monthly['Mobile'], errors='coerce').fillna(0).astype('int64').astype(str)
    valid_mobiles = set(df_monthly['Mobile'].unique())
    valid_mobiles.discard('0')


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
    df_detailed['Customer Mobile'] = pd.to_numeric(df_detailed['Customer Mobile'], errors='coerce').fillna(0).astype('int64').astype(str)
    df_detailed['Total Value'] = pd.to_numeric(df_detailed['Total Value'], errors='coerce').fillna(0)
    df_detailed['POINT REDUMPTION (DEDUCTION)'] = pd.to_numeric(df_detailed['POINT REDUMPTION (DEDUCTION)'], errors='coerce').fillna(0)
    
    if df_detailed['POINT REDUMPTION (DEDUCTION)'].max() <= 0 and df_detailed['POINT REDUMPTION (DEDUCTION)'].min() < 0:
        df_detailed['POINT REDUMPTION (DEDUCTION)'] = df_detailed['POINT REDUMPTION (DEDUCTION)'].abs()

    df_merged = df_detailed[df_detailed['Customer Mobile'].isin(valid_mobiles)]

    # Group by mobile number
    df_grouped = df_merged.groupby('Customer Mobile').agg({
        'Total Value': 'sum',
        'POINT REDUMPTION (DEDUCTION)': 'sum'
    }).reset_index()

    df_grouped.rename(columns={
        'Customer Mobile': 'Mobile Number',
        'Total Value': 'Purchase Value',
        'POINT REDUMPTION (DEDUCTION)': 'Redeemed Points'
    }, inplace=True)
    
    # Indicate whether the user has redeemed
    df_grouped['Has Redeemed'] = df_grouped['Redeemed Points'] > 0

    print("Saving to Excel...")
    df_grouped.to_excel('Purchase_and_Redeemed_Data.xlsx', index=False)
    print("Done! File saved as Purchase_and_Redeemed_Data.xlsx")

if __name__ == '__main__':
    export_data()
