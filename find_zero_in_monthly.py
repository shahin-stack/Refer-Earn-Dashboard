import sqlite3
import pandas as pd

def check_monthly_mobs():
    conn_mon = sqlite3.connect('monthly.db')
    df_mon = pd.read_sql("SELECT [Mobile Number] FROM r_f_monthly", conn_mon)
    conn_mon.close()

    def clean(m):
        m = str(m).strip()
        if m.endswith('.0'): m = m[:-2]
        return m

    df_mon['m'] = df_mon['Mobile Number'].apply(clean)
    
    # Check for '0'
    print(f"Total Rows in Monthly DB: {len(df_mon)}")
    print(f"Unique Mobile Numbers in Monthly DB: {df_mon['m'].nunique()}")
    
    zeros = df_mon[df_mon['m'] == '0']
    print(f"Rows where mobile is exactly '0': {len(zeros)}")
    
    none_vals = df_mon[df_mon['m'] == 'None']
    print(f"Rows where mobile is 'None': {len(none_vals)}")

if __name__ == '__main__':
    check_monthly_mobs()
