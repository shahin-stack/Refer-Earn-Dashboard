import urllib.request, json

print("Testing Age Report with date filter...")
d = json.loads(urllib.request.urlopen('http://127.0.0.1:7050/api/age-report?start=2026-01-16&end=2026-02-10').read())
print(f"  Age total (Jan16-Feb10): {d['total']:,}")

print("\nTesting District Report with date filter...")
d2 = json.loads(urllib.request.urlopen('http://127.0.0.1:7050/api/district-report?start=2026-01-16&end=2026-02-10').read())
print(f"  District total (Jan16-Feb10): {d2['total']:,}")
if d2['districts']:
    print(f"  Top district: {d2['districts'][0]['district']} -> {d2['districts'][0]['count']:,}")

print("\nTesting without filter (should show all data)...")
d3 = json.loads(urllib.request.urlopen('http://127.0.0.1:7050/api/age-report').read())
print(f"  Age total (no filter): {d3['total']:,}")
d4 = json.loads(urllib.request.urlopen('http://127.0.0.1:7050/api/district-report').read())
print(f"  District total (no filter): {d4['total']:,}")
print("\nAll checks done!")
