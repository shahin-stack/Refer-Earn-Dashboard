import pandas as pd
import clickhouse_connect
import sys
from datetime import datetime

def get_client():
    return clickhouse_connect.get_client(
        host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
        port=8443,
        username='default',
        password='ZFlujj9SA_Iei',
        secure=True
    )

def normalize_date(val):
    """Normalize any date string to YYYY-MM-DD format."""
    val = str(val).strip()
    # Try DD-MM-YYYY
    for fmt in ('%d-%m-%Y', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(val[:len(fmt.replace('%d','00').replace('%m','00').replace('%Y','0000').replace('%H','00').replace('%M','00').replace('%S','00'))], fmt).strftime('%Y-%m-%d')
        except:
            pass
    # Fallback: let pandas parse it
    try:
        return pd.to_datetime(val, dayfirst=False).strftime('%Y-%m-%d')
    except:
        return val

def normalize_date_series(series):
    """Normalize a series with mixed date formats to YYYY-MM-DD."""
    def _norm(val):
        val = str(val).strip()
        # DD-MM-YYYY
        try:
            return datetime.strptime(val, '%d-%m-%Y').strftime('%Y-%m-%d')
        except: pass
        # YYYY-MM-DD HH:MM:SS
        try:
            return datetime.strptime(val[:19], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
        except: pass
        # YYYY-MM-DD
        try:
            return datetime.strptime(val[:10], '%Y-%m-%d').strftime('%Y-%m-%d')
        except: pass
        # pandas fallback
        try:
            return pd.to_datetime(val).strftime('%Y-%m-%d')
        except:
            return val
    return series.apply(_norm)

def ingest_refer_point_data(client):
    print("Reading Refer point data.xlsx...")
    df = pd.read_excel('Refer point data.xlsx')
    print(f"  Loaded {len(df)} rows, columns: {list(df.columns)}")

    # Normalize column names
    df.columns = [c.strip().replace(' ', '_').lower() for c in df.columns]
    # Expected: customer_name, customer_mobile_number, campaign_name, bonus_points, start_date

    df['customer_name']           = df['customer_name'].fillna('').astype(str)
    df['customer_mobile_number']  = df['customer_mobile_number'].astype(str).str.replace(r'\.0$', '', regex=True)
    df['campaign_name']           = df['campaign_name'].fillna('').astype(str)
    df['bonus_points']            = pd.to_numeric(df['bonus_points'], errors='coerce').fillna(0).astype(float)
    print("  Normalizing date formats to YYYY-MM-DD...")
    df['start_date']              = normalize_date_series(df['start_date'].astype(str))
    print(f"  Sample dates after normalization: {df['start_date'].head(5).tolist()}")

    print("Creating refer_point_data table...")
    client.command('''
        CREATE TABLE IF NOT EXISTS refer_point_data (
            customer_name           String,
            customer_mobile_number  String,
            campaign_name           String,
            bonus_points            Float64,
            start_date              String
        ) ENGINE = MergeTree()
        ORDER BY customer_mobile_number
    ''')

    client.command('TRUNCATE TABLE refer_point_data')

    print("Inserting data into refer_point_data...")
    client.insert_df('refer_point_data', df)
    print(f"  Successfully ingested {len(df)} rows into refer_point_data.")


def ingest_loyalty_user_data(client):
    print("Reading Complete user data for loyalty.csv...")
    df = pd.read_csv('Complete user data for loyalty.csv', dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]
    print(f"  Loaded {len(df)} rows, columns: {list(df.columns)}")

    # Fill NaN with empty string for all string columns
    for col in df.columns:
        df[col] = df[col].fillna('').astype(str)

    print("Creating loyalty_user_data table...")
    client.command('''
        CREATE TABLE IF NOT EXISTS loyalty_user_data (
            id                  String,
            created_at          String,
            user_phone          String,
            user_email          String,
            firstname           String,
            lastname            String,
            updated_at          String,
            user_id             String,
            address             String,
            pincode             String,
            state               String,
            date_of_birth       String,
            wedding_anniversary String,
            married             String,
            update_count        String,
            profile_status      String,
            gender              String
        ) ENGINE = MergeTree()
        ORDER BY id
    ''')

    client.command('TRUNCATE TABLE loyalty_user_data')

    print("Inserting data into loyalty_user_data...")
    client.insert_df('loyalty_user_data', df)
    print(f"  Successfully ingested {len(df)} rows into loyalty_user_data.")


if __name__ == '__main__':
    try:
        client = get_client()
        print("Connected to ClickHouse.")
        ingest_refer_point_data(client)
        ingest_loyalty_user_data(client)
        print("\nAll data ingested successfully!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
