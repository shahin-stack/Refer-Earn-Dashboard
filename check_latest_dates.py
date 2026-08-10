import sqlite3
import pandas as pd

print('='*50)
print('LATEST DATES IN DASHBOARD DATA')
print('='*50)

# monthly.db - latest START_DATE
conn = sqlite3.connect('monthly.db')
result = conn.execute("SELECT MIN(SUBSTR(START_DATE,1,10)), MAX(SUBSTR(START_DATE,1,10)), COUNT(DISTINCT MOBILE_NUMBER) FROM r_f_monthly_OG").fetchone()
print(f'\nmonthly.db -> r_f_monthly_OG')
print(f'  Earliest date : {result[0]}')
print(f'  Latest date   : {result[1]}')
print(f'  Unique members: {result[2]:,}')
conn.close()

# detailed_split.db - latest Date
conn2 = sqlite3.connect('detailed_split.db')
result2 = conn2.execute('SELECT MIN([Date]), MAX([Date]), COUNT(*) FROM "jan_16___march_31_Detailed"').fetchone()
print(f'\ndetailed_split.db -> jan_16___march_31_Detailed')
print(f'  Earliest date : {result2[0]}')
print(f'  Latest date   : {result2[1]}')
print(f'  Total rows    : {result2[2]:,}')
conn2.close()

# eaas.db - latest created_at
conn3 = sqlite3.connect('eaas.db')
result3 = conn3.execute("SELECT MIN(SUBSTR(created_at,1,10)), MAX(SUBSTR(created_at,1,10)), COUNT(*) FROM eaas_users").fetchone()
print(f'\neaas.db -> eaas_users')
print(f'  Earliest date : {result3[0]}')
print(f'  Latest date   : {result3[1]}')
print(f'  Total users   : {result3[2]:,}')
conn3.close()

print('\n' + '='*50)
print('SUMMARY: Overall latest date across all data')
print('='*50)

