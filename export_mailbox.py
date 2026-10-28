import csv
import time
from datetime import datetime
from email.utils import parseaddr

from gmail_client import get_service

OUT = "mailbox_export.csv"
QUERY = "newer_than:180d -in:sent -in:drafts"
BATCH = 25
FIELDS = ["id", "date", "name", "address", "domain", "subject",
          "labels", "has_unsubscribe", "snippet"]


def list_ids(service):
    ids, token = [], None
    while True:
        resp = service.users().messages().list(
            userId="me", q=QUERY, maxResults=500, pageToken=token
        ).execute()
        ids += [m["id"] for m in resp.get("messages", [])]
        token = resp.get("nextPageToken")
        print(f"Listed {len(ids)} emails...")
        if not token:
            return ids


def to_row(msg):
    h = {x["name"].lower(): x["value"] for x in msg["payload"]["headers"]}
    name, addr = parseaddr(h.get("from", ""))
    return {
        "id": msg["id"],
        "date": datetime.fromtimestamp(int(msg["internalDate"]) / 1000).strftime("%Y-%m-%d"),
        "name": name,
        "address": addr.lower(),
        "domain": addr.split("@")[-1].lower() if "@" in addr else "",
        "subject": h.get("subject", ""),
        "labels": "|".join(msg.get("labelIds", [])),
        "has_unsubscribe": "list-unsubscribe" in h,
        "snippet": msg.get("snippet", "")[:120],
    }


def fetch_batch(service, ids):
    rows, failed = [], []

    def cb(request_id, response, exception):
        if exception:
            failed.append(request_id)
        else:
            rows.append(to_row(response))

    batch = service.new_batch_http_request(callback=cb)
    for i in ids:
        batch.add(
            service.users().messages().get(
                userId="me", id=i, format="metadata",
                metadataHeaders=["From", "Subject", "List-Unsubscribe"],
            ),
            request_id=i,
        )
    batch.execute()
    return rows, failed


if __name__ == "__main__":
    service = get_service()
    ids = list_ids(service)
    all_rows, retry = [], []

    for start in range(0, len(ids), BATCH):
        rows, failed = fetch_batch(service, ids[start:start + BATCH])
        all_rows += rows
        retry += failed
        print(f"Fetched {len(all_rows)}/{len(ids)}")
        time.sleep(1)  # stay under Gmail's rate limit

    if retry:
        print(f"Retrying {len(retry)} failed emails...")
        time.sleep(10)
        for start in range(0, len(retry), BATCH):
            rows, _ = fetch_batch(service, retry[start:start + BATCH])
            all_rows += rows
            time.sleep(2)

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Saved {len(all_rows)} emails to {OUT}")