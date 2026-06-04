import requests
import time
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

labels = {
    "FELT": 2743373,
    "Motion Ward": 938908,
    "Year0001": 973197,
    "Posh Isolation": 154437,
}

for name, label_id in labels.items():
    r = requests.get(
        f"https://api.discogs.com/labels/{label_id}/releases",
        headers=headers,
        params={"per_page": 5, "page": 1},
    )
    data = r.json()
    total = data["pagination"]["items"]
    print(f"\n=== {name} (id {label_id}) ===")
    print(f"Total releases: {total}")

    for rel in data["releases"][:5]:
        print(f"  - {rel.get('year','?')}  {rel.get('title','?')}  [{rel.get('format','?')}]")

    if data["releases"]:
        first_id = data["releases"][0]["id"]
        time.sleep(1)
        detail = requests.get(
            f"https://api.discogs.com/releases/{first_id}",
            headers=headers,
        ).json()
        community = detail.get("community", {})
        print("  sample release community data:")
        print(f"     have={community.get('have')}, want={community.get('want')}, "
              f"num_for_sale={detail.get('num_for_sale')}, "
              f"rating={community.get('rating', {}).get('average')}")

    time.sleep(1)