import urllib.request as req
import json

token = input("token: ").strip()
uid = input("user_id: ").strip()

headers = {"Authorization": token, "New-Api-User": uid, "Content-Type": "application/json"}

# Step 1: list tokens
r1 = req.Request("http://localhost:3001/api/token/?p=0&size=100", headers=headers)
resp = req.urlopen(r1, timeout=10)
data = json.loads(resp.read())
print("Tokens:", json.dumps(data, indent=2)[:2000])

tokens = data.get("data") or []
if tokens:
    ids = [t["id"] for t in tokens if t.get("id")]
    # Step 2: reveal full keys
    r2 = req.Request("http://localhost:3001/api/token/batch/keys", headers=headers,
                     data=json.dumps({"ids": ids}).encode(), method="POST")
    resp2 = req.urlopen(r2, timeout=10)
    data2 = json.loads(resp2.read())
    print("\nFull keys:", json.dumps(data2, indent=2)[:2000])
