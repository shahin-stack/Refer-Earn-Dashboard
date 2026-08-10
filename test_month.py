import pandas as pd
import sqlite3

def test():
    conn = sqlite3.connect('eaas.db')
    df = pd.read_sql_query("SELECT date_of_birth FROM eaas_users LIMIT 50", conn)
    print(df.head())
    
    # drop empty/nulls
    df = df.dropna(subset=['date_of_birth'])
    df = df[df['date_of_birth'].str.strip() != '']
    
    # check extract month
    def get_month(d):
        try:
            return int(d.split('-')[1])
        except:
            return None
    
    df['m'] = df['date_of_birth'].apply(get_month)
    print(df['m'].value_counts(dropna=False))
    
    conn.close()

test()
