import requests
import time
import json
import os
from datetime import datetime, timezone

# ----- CONFIG -----
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.environ.get("DISCOGS_TOKEN")
if not TOKEN:
    raise SystemExit("DISCOGS_TOKEN not set — add it to your .env file.")

LABELS = {
    "felt": 2743373,
    "motion_ward": 938908,
    "year0001": 973197,
    "posh_isolation": 154437,
}

# Set to a small number (e.g. 5) for a quick TEST run.
# Set to None for the real, full pull (~20 min).
LIMIT_PER_LABEL = None

REQUEST_PAUSE = 1.2   # seconds between calls; keeps us under 60/min
# ------------------

HEADERS = {
    "Authorization": f"Discogs token={TOKEN}",
    "User-Agent": "HyperIslandDA27/1.0",
}


def get(url, params=None):
    """GET with a polite pause, plus auto-retry if we hit the rate limit."""
    while True:
        resp = requests.get(url, headers=HEADERS, params=params)
        if resp.status_code == 429:
            print("   rate limited — waiting 60s...")
            time.sleep(60)
            continue
        resp.raise_for_status()
        time.sleep(REQUEST_PAUSE)
        return resp.json()


def get_release_ids(label_id):
    """Page through a label and collect every release id."""
    ids = []
    page = 1
    while True:
        data = get(
            f"https://api.discogs.com/labels/{label_id}/releases",
            params={"per_page": 100, "page": page},
        )
        for rel in data["releases"]:
            ids.append(rel["id"])
        if page >= data["pagination"]["pages"]:
            break
        page += 1
    return ids


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = os.path.join("raw", "discogs", "releases", f"ingest_date={today}")
    os.makedirs(out_dir, exist_ok=True)
    print(f"Saving raw data to: {out_dir}\n")

    for name, label_id in LABELS.items():
        print(f"=== {name} (id {label_id}) ===")
        release_ids = get_release_ids(label_id)
        if LIMIT_PER_LABEL is not None:
            release_ids = release_ids[:LIMIT_PER_LABEL]
        print(f"  fetching {len(release_ids)} releases...")

        out_path = os.path.join(out_dir, f"{name}.jsonl")
        saved = 0
        with open(out_path, "w") as f:
            for i, rid in enumerate(release_ids, start=1):
                try:
                    detail = get(f"https://api.discogs.com/releases/{rid}")
                except Exception as e:
                    print(f"   skipped release {rid}: {e}")
                    continue
                f.write(json.dumps(detail) + "\n")
                saved += 1
                if i % 25 == 0:
                    print(f"   {i}/{len(release_ids)} done")
        print(f"  saved {saved} releases to {out_path}\n")

    print("Done.")


if __name__ == "__main__":
    main()