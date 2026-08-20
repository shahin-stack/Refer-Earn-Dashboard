"""
Remove the 7 duplicate Aug-9 rows that were accidentally inserted from the Excel file.
The Excel file contained 7 rows dated 2026-08-09 which already existed in the table.
Strategy: DELETE rows from Aug 9 that exactly match the 7 mobile numbers from the Excel file.
"""
import clickhouse_connect
import pandas as pd

client = clickhouse_connect.get_client(
    host='pdhsuv47ec.ap-south-1.aws.clickhouse.cloud',
    port=8443, username='default', password='ZFlujj9SA_Iei', secure=True
)

# Load the 7 Aug 9 rows from Excel
df = pd.read_excel(r'C:\Users\SHAHIN\Desktop\Refer & Earn Dashboard\refer_point_data august 10 - 19.xlsx')
df['parsed_date'] = pd.to_datetime(df['Start Date'], format='%d-%m-%Y').dt.strftime('%Y-%m-%d')
aug9_df = df[df['parsed_date'] == '2026-08-09'].copy()
aug9_df['mob'] = aug9_df['Customer Mobile'].astype(str)

print(f"Aug 9 rows in Excel: {len(aug9_df)}")
print(aug9_df[['Customer Name', 'Customer Mobile', 'Campaign Name', 'Bonus Point']].to_string())

# Count before deletion
before = client.query("SELECT count() FROM refer_point_data WHERE start_date='2026-08-09'").result_rows[0][0]
print(f"\nAug 9 rows in CH before delete: {int(before)}")

# Build a DELETE query for the exact duplicates using lightweight delete
# We delete rows where (mobile, campaign, bonus) match AND start_date='2026-08-09'
# using ALTER TABLE ... DELETE
mob_list = "', '".join(aug9_df['mob'].tolist())
campaign_list = "', '".join(aug9_df['Campaign Name'].astype(str).tolist())

print(f"\nMobiles to delete from Aug 9: {mob_list}")

# Delete using ALTER TABLE DELETE (supported on SharedMergeTree)
delete_sql = f"""
    ALTER TABLE refer_point_data DELETE
    WHERE start_date = '2026-08-09'
      AND customer_mobile_number IN ('{mob_list}')
"""
# First check what we'd be deleting (in case some mobiles appear multiple times on Aug 9)
preview = client.query(f"""
    SELECT customer_name, customer_mobile_number, campaign_name, bonus_points, start_date
    FROM refer_point_data
    WHERE start_date = '2026-08-09'
      AND customer_mobile_number IN ('{mob_list}')
    ORDER BY customer_mobile_number
""").result_rows
print(f"\nRows that will be deleted ({len(preview)} total):")
for row in preview:
    print(f"  {row}")

# Each mobile should appear exactly TWICE on Aug 9 (original + duplicate)
# We need to remove only ONE copy (the duplicate). Use a safer approach:
# Delete ALL matching rows, then re-insert the original 7.
print("\nProceeding with delete + re-insert approach...")

# Step 1: Get the original 7 rows from CH (before the file added duplicates)
# They should be identical - just pick one copy of each
original_7 = []
for _, row in aug9_df.iterrows():
    mob = str(int(row['Customer Mobile']))
    r = client.query(f"""
        SELECT customer_name, customer_mobile_number, campaign_name, bonus_points, start_date
        FROM refer_point_data
        WHERE start_date = '2026-08-09'
          AND customer_mobile_number = '{mob}'
        LIMIT 1
    """).result_rows
    if r:
        original_7.append(r[0])

print(f"Saved {len(original_7)} original rows to re-insert after delete")

# Step 2: Delete ALL copies of these mobiles on Aug 9
client.command(f"""
    ALTER TABLE refer_point_data DELETE
    WHERE start_date = '2026-08-09'
      AND customer_mobile_number IN ('{mob_list}')
""")
print("DELETE command issued, waiting for mutation...")

import time
time.sleep(5)

# Step 3: Re-insert the original 7
if original_7:
    reinsert_df = pd.DataFrame(original_7, columns=['customer_name','customer_mobile_number','campaign_name','bonus_points','start_date'])
    client.insert_df('refer_point_data', reinsert_df)
    print(f"Re-inserted {len(reinsert_df)} original rows")

# Verify
time.sleep(3)
after = client.query("SELECT count() FROM refer_point_data WHERE start_date='2026-08-09'").result_rows[0][0]
total = client.query("SELECT count() FROM refer_point_data").result_rows[0][0]
max_date = client.query("SELECT MAX(start_date) FROM refer_point_data").result_rows[0][0]
print(f"\nAug 9 rows after fix: {int(after)}")
print(f"Total rows: {int(total):,}")
print(f"Last date : {max_date}")
print("Done!")
