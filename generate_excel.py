import clickhouse_connect
import pandas as pd

def generate():
    client = clickhouse_connect.get_client(
        host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
        port=8443,
        username='default',
        password='ZFlujj9SA_Iei',
        secure=True
    )

    query = """
    WITH valid_sales AS (
        SELECT 
            if(endsWith(customer_mobile, '.0'), substr(customer_mobile, 1, length(customer_mobile) - 2), customer_mobile) as mob,
            total_value,
            abs(toFloat64OrZero(point_redemption)) as redemption
        FROM sales_data
        WHERE parsed_date >= '2026-01-16'
        AND if(endsWith(customer_mobile, '.0'), substr(customer_mobile, 1, length(customer_mobile) - 2), customer_mobile) IN (
            SELECT if(endsWith(customer_mobile_number, '.0'), substr(customer_mobile_number, 1, length(customer_mobile_number) - 2), customer_mobile_number) FROM refer_point_data
        )
    )
    SELECT 
        mob as `Mobile Number`,
        sum(total_value) as `Purchase Value`,
        sum(redemption) as `Point Redeemed Value`,
        if(sum(redemption) > 0, 1, 0) as `Has Redeemed`
    FROM valid_sales
    GROUP BY mob
    """
    
    print("Executing query on ClickHouse...")
    res = client.query(query)
    
    print("Converting to DataFrame...")
    df = pd.DataFrame(res.result_rows, columns=res.column_names)
    
    # Create separate dataframes
    df_purchase = df[['Mobile Number', 'Purchase Value']].copy()
    df_redeemed = df[df['Has Redeemed'] == 1][['Mobile Number', 'Purchase Value', 'Point Redeemed Value']].copy()
    
    print("Saving to Excel with separate sheets...")
    with pd.ExcelWriter("Purchase_and_Redeemed_Separate.xlsx") as writer:
        df_purchase.to_excel(writer, sheet_name='Total_Purchase_Count', index=False)
        df_redeemed.to_excel(writer, sheet_name='Total_Redeemed_Count', index=False)
    
    # Quick sanity check
    print(f"Total Rows (Purchase Count): {len(df_purchase)}")
    print(f"Total Redeemed Count: {len(df_redeemed)}")
    print(f"Total Point Redeemed Value: {df_redeemed['Point Redeemed Value'].sum()}")
    print("Done! File saved as Purchase_and_Redeemed_Separate.xlsx")
    
if __name__ == '__main__':
    generate()
