import urllib.request, json

def verify():
    url = 'http://localhost:7090/api/dashboard?start=2026-03-01&end=2026-03-01'
    try:
        res = urllib.request.urlopen(url).read()
        data = json.loads(res.decode('utf-8'))
        print("API Response for 2026-03-01:")
        print(json.dumps(data, indent=2))
    except Exception as e:
        print("Error verifying:", e)

if __name__ == '__main__':
    verify()
