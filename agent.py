import json
import os
import sys
import time

from gmail_client import get_service, list_latest, get_body, apply_label
from rules import classify_by_rules
from triage import classify_message, decide_action, send_alert

PROCESSED_PATH = "processed.json"
FETCH_LATEST = 50      # how many recent inbox emails to look at
MAX_AI_PER_RUN = 10    # cap on Gemini calls per run
MAX_BODY_CHARS = 4000


def load_processed() -> dict:
    if not os.path.exists(PROCESSED_PATH):
        return {}
    with open(PROCESSED_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_processed(processed: dict) -> None:
    with open(PROCESSED_PATH, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=2)


def main(dry_run: bool) -> None:
    service = get_service()
    processed = load_processed()
    emails = list_latest(service, FETCH_LATEST)

    rule_count = ai_count = 0
    for e in emails:
        if e["id"] in processed:
            continue

        category = classify_by_rules(
            e["domain"], e["labels"], e["has_unsubscribe"], e["subject"]
        )
        labels, alert = [], None
        action_note = ""

        if category is not None:
            # Rules layer: no AI, no email body, instant.
            source = "rules"
            labels = [f"Triage/{category}"]
            if category == "security_account":
                alert = {
                    "urgency": "medium",
                    "category": category,
                    "summary": "Security or account alert",
                    "reason": "Matched a security sender rule",
                }
        else:
            # AI layer: only personal or unknown senders get here.
            if ai_count >= MAX_AI_PER_RUN:
                print("Reached the AI cap for this run; the rest wait for next run.")
                continue
            body = get_body(service, e["id"])[:MAX_BODY_CHARS] or "(no plain-text body)"
            text = f"From: {e['sender']}\nSubject: {e['subject']}\n\n{body}"
            try:
                result = classify_message(text)
            except RuntimeError as err:
                print(err)
                break
            source = "ai"
            category = result["category"]
            action = decide_action(result)
            labels = [f"Triage/{category}"]
            if action == "human_review":
                labels.append("Triage/human_review")
                alert = result
            action_note = f" -> {action}"
            ai_count += 1

        print(
            f"[{source.upper()}] {category}{action_note}  |  "
            f"{e['sender'][:45]}  |  {e['subject'][:50]}"
        )

        if not dry_run:
            for label in labels:
                apply_label(service, e["id"], label)
            if alert:
                send_alert({"sender": e["sender"], "subject": e["subject"]}, alert)
            processed[e["id"]] = {"category": category, "source": source}
            save_processed(processed)  # saved after every email

        if source == "ai":
            time.sleep(6)  # stay under Gemini's per-minute limit
        else:
            rule_count += 1

    mode = " (dry run: nothing changed)" if dry_run else ""
    print(f"Done. {rule_count} by rules, {ai_count} by AI{mode}.")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)