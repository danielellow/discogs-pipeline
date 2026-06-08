import requests
import os

from dotenv import load_dotenv
load_dotenv()
TOKEN = os.environ.get("DISCOGS_TOKEN")
if not TOKEN:
    raise SystemExit("DISCOGS_TOKEN not set — add it to your .env file.")

headers = {
    "Authorization": f"Discogs token={TOKEN}",
    "User-Agent": "HyperIslandDA27/1.0",
}

# 249504 is the example release id from Discogs' own API docs; if this works, we know our token and headers are correct.
response = requests.get("https://api.discogs.com/releases/249504", headers=headers)

print("Status code:", response.status_code)   # 200 means success
print(response.json())                          # the actual data