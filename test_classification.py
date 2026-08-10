import urllib.request
import json

url = 'http://127.0.0.1:8020/api/customer-classification'
print(f'Calling: {url}')

try:
    with urllib.request.urlopen(url, timeout=120) as r:
        body = r.read().decode('utf-8')
        data = json.loads(body)
        print('\n=== Customer Classification API Result ===')
        print(f"Total R&E Participants : {data.get('total_participants', 'N/A'):,}")
        print(f"Pre-programme Base Size: {data.get('base_size', 'N/A'):,}")
        print(f"Repeat Customers       : {data.get('repeat_count', 'N/A'):,}  ({data.get('repeat_pct', 'N/A')}%)")
        print(f"New Customers          : {data.get('new_count', 'N/A'):,}  ({data.get('new_pct', 'N/A')}%)")
        print('\nRaw JSON:')
        print(json.dumps(data, indent=2))
except Exception as e:
    print(f'ERROR: {e}')
