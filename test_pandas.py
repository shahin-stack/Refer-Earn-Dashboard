import pandas as pd
import sqlite3
import json

def test():
    conn = sqlite3.connect('eaas.db')
    df = pd.read_sql_query("SELECT District FROM eaas_users WHERE District IS NOT NULL AND TRIM(District) != ''", conn)
    counts = df['District'].value_counts().head(20)
    districts = [{'rank': i + 1, 'district': str(dist), 'count': int(count)} for i, (dist, count) in enumerate(counts.items())]
    print(json.dumps({'districts': districts, 'total': int(counts.sum())}))
    conn.close()

test()
