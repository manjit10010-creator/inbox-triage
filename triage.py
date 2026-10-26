import csv
import json
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()
client = genai.Client()

MODEL = "gemini-3.5-flash-lite"  # one place to change it later
CSV_PATH = "results.csv"

FIELDS = [
    "message",
    "category",
    "sender_name",
    "summary",
    "urgency",
    "needs_human_review",
    "reason",
    "action",
    "draft_reply",
]


def classify_message(message: str) -> dict:
    prompt = f"""
    You are an assistant that triages incoming business messages.
    Read the message and return JSON with these fields:
    - category: one of "sales_inquiry", "support_request", "spam", "other"
    - sender_name: the sender's name, or null if not given
    - summary: one sentence describing what they want
    - urgency: one of "low", "medium", "high"
    - needs_human_review: true or false
    - reason: one short sentence explaining why you chose this category
    - draft_reply: a short, polite reply (2 to 5 sentences) to the sender,
      or null if the category is "spam" or the message contains a legal threat

    Rules:
    - If a message is both a support problem and a sales question, choose
      "support_request", because an unresolved problem comes first.
    - If the message is too vague to tell what the sender wants, use
      category "other" and do not guess.
    - urgency is "high" only for legal threats, repeated unanswered contact,
      refund demands, or system outages. A broken checkout, login, or payment
      counts as a system outage. A request to reply quickly alone is "medium".
      A sales inquiry that mentions a deadline, budget, or quantity is at
      least "medium". Everything else is "low".
    - needs_human_review is true ONLY for: legal threats, angry or threatening
      tone, messages that mix several unrelated requests, or messages too vague
      to categorize. A clear, polite request is false.

    Rules for draft_reply:
    - Reply in the same language as the message. If the message is Hinglish
      (Hindi written in English letters), reply in simple Hinglish.
    - Never promise refunds, prices, discounts, deadlines, or legal positions,
      and never admit fault. Do not invent any facts.
    - If the message mentions a lawyer, lawsuit, or legal action, draft_reply
      must be null. A human will write that reply.
    - For sales inquiries, thank them and ask one or two questions needed to
      prepare a quote.
    - For support requests, say the issue is being looked into and ask for
      any detail needed. Apologize only for the inconvenience, never for a
      specific failure.
    - For vague messages, politely ask what they would like to discuss.
    - End with the sign-off "[Your Name]".

    Message:
    {message}
    """

    response = None
    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0,
                ),
            )
            break
        except errors.ServerError:
            wait = 5 * (attempt + 1)  # 5s, 10s, 15s, 20s, 25s
            print(f"Server busy, retrying in {wait}s...")
            time.sleep(wait)
        except errors.ClientError as e:
            if e.code == 429:
                raise RuntimeError(
                    "Quota exceeded (429). Wait for the reset or switch MODEL."
                ) from e
            raise

    if response is None:
        raise RuntimeError("Gemini is still unavailable, try again later")

    return json.loads(response.text)


def decide_action(result: dict) -> str:
    """Routing rules live in code, not in the model."""
    if result["category"] == "spam":
        return "ignore"
    # Safety net: the model's flag is a suggestion, these rules are enforced.
    if result["needs_human_review"] or result["urgency"] == "high":
        return "human_review"
    if not result.get("draft_reply"):
        return "human_review"
    return "ready_for_approval"


def load_done() -> dict:
    """Read results.csv (if it exists) so finished messages are not re-sent."""
    if not os.path.exists(CSV_PATH):
        return {}
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return {row["message"]: row for row in csv.DictReader(f)}


def save_all(rows: list) -> None:
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    test_messages = [
        "Hi, I'm Priya from Bright Cafe. We need a website with online ordering, ideally launched next month. What would it cost?",
        "My order #4821 never arrived and nobody is replying to my emails. This is the third time I'm writing. I want a refund TODAY.",
        "CONGRATULATIONS! You've won a free prize. Click here to claim now!!!",
        "hey, are you free to talk sometime?",
        # harder cases
        "Love your product, but the checkout keeps crashing. Also, do you offer bulk discounts for 50+ licenses?",
        "Bhai, website banwani hai apne shop ke liye, kitna lagega? Jaldi batao.",
        "I'm sure this is just a misunderstanding, but this is my fifth email and I'm now contacting my lawyer.",
        "hi",
    ]

    done = load_done()
    rows = list(done.values())

    for message in test_messages:
        if message in done:
            print(f"Skipping (already saved): {message[:40]}...")
            continue

        try:
            result = classify_message(message)
        except RuntimeError as e:
            print(e)
            break

        result["message"] = message
        result["action"] = decide_action(result)
        rows.append(result)
        save_all(rows)  # saved after every message, so a crash loses nothing

        print(f"[{result['action'].upper()}] {result['category']} / {result['urgency']}")
        print(f"Message: {message}")
        print(f"Draft:   {result['draft_reply']}")
        print("---")
        time.sleep(6)  # stay under the per-minute limit

    print(f"Done. {len(rows)} results in {CSV_PATH}")