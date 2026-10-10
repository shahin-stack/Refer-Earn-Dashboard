import pandas as pd
import clickhouse_connect
import sys

def main():
    print("Reading User details - eaas.csv...")
    try:
        df = pd.read_csv('User details - eaas.csv', dtype=str)
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        return

    # Normalize columns
    df.columns = [c.strip().lower() for c in df.columns]
    print(f"Loaded {len(df)} rows. Columns: {list(df.columns)}")

    # Fill NaN with empty string
    for col in df.columns:
        df[col] = df[col].fillna('').astype(str)

    print("Connecting to ClickHouse...")
    client = clickhouse_connect.get_client(
        host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
        port=8443,
        username='default',
        password='ZFlujj9SA_Iei',
        secure=True
    )

    print("Inserting data into loyalty_user_data...")
    try:
        client.insert_df('loyalty_user_data', df)
        print(f"Successfully appended {len(df)} rows to loyalty_user_data.")
    except Exception as e:
        print(f"Error during insertion: {e}")

if __name__ == '__main__':
    main()
