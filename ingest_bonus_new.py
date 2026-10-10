import pandas as pd
import clickhouse_connect
from datetime import datetime

def normalize_date(val):
    val = str(val).strip()
    # Try DD-MM-YYYY
    try:
        return datetime.strptime(val, '%d-%m-%Y').strftime('%Y-%m-%d')
    except:
        pass
    # Try YYYY-MM-DD HH:MM:SS
    try:
        return datetime.strptime(val[:19], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
    except:
        pass
    # Try YYYY-MM-DD
    try:
        return datetime.strptime(val[:10], '%Y-%m-%d').strftime('%Y-%m-%d')
    except:
        pass
    # pandas fallback
    try:
        return pd.to_datetime(val).strftime('%Y-%m-%d')
    except:
        return val

def main():
    print("Reading bonus.xlsx...")
    df = pd.read_excel('bonus.xlsx')
    
    print(f"Loaded {len(df)} rows.")
    
    # Rename columns to match ClickHouse table
    df = df.rename(columns={
        'Customer Name': 'customer_name',
        'Customer Mobile': 'customer_mobile_number',
        'Campaign Name': 'campaign_name',
        'Bonus Point': 'bonus_points',
        'Start Date': 'start_date'
    })
    
    # Process columns
    df['customer_name'] = df['customer_name'].fillna('').astype(str)
    df['customer_mobile_number'] = df['customer_mobile_number'].astype(str).str.replace(r'\.0$', '', regex=True)
    df['campaign_name'] = df['campaign_name'].fillna('').astype(str)
    df['bonus_points'] = pd.to_numeric(df['bonus_points'], errors='coerce').fillna(0).astype(float)
    
    print("Normalizing date format to YYYY-MM-DD...")
    df['start_date'] = df['start_date'].apply(normalize_date)
    
    print(f"Sample formatted dates: {df['start_date'].head().tolist()}")
    
    print("Connecting to ClickHouse...")
    client = clickhouse_connect.get_client(
        host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
        port=8443,
        username='default',
        password='ZFlujj9SA_Iei',
        secure=True
    )
    
    print("Inserting data into refer_point_data...")
    client.insert_df('refer_point_data', df)
    print(f"Successfully appended {len(df)} rows to refer_point_data.")

if __name__ == '__main__':
    main()
