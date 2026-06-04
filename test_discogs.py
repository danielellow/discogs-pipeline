import requests
import os

from dotenv import load_dotenv
load_dotenv()
TOKEN = os.environ.get("DISCOGS_TOKEN")
if not TOKEN:
    raise SystemExit("DISCOGS_TOKEN not set — add it to your .env file.")

headers = {
    # this line proves it's you (the higher rate limit)
    "Authorization": f"Discogs token={TOKEN}",
    # Discogs REQUIRES you to name your app, or it rejects the request
    "User-Agent": "HyperIslandDA27/1.0",
}

# 249504 is the example release id from Discogs' own API docs — a real record
response = requests.get("https://api.discogs.com/releases/249504", headers=headers)

print("Status code:", response.status_code)   # 200 means success
print(response.json())                          # the actual data