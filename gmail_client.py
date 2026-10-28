import base64
import os
from email.message import EmailMessage
from email.utils import parseaddr

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Can read, label and create drafts. Our code never calls a send function.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def get_service():
    """Log in (first run opens a browser) and return a Gmail API client."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if os.environ.get("AGENT_AUTO"):
                raise RuntimeError(
                    "Gmail login expired. Run agent.py manually once to log in again."
                )
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def list_latest(service, n=5):
    """Return the n newest inbox emails with the fields the rules and drafts need."""
    result = service.users().messages().list(
        userId="me", labelIds=["INBOX"], maxResults=n
    ).execute()

    emails = []
    for m in result.get("messages", []):
        msg = service.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["From", "Subject", "List-Unsubscribe", "Message-ID", "Reply-To"],
        ).execute()
        headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
        _, addr = parseaddr(headers.get("from", ""))
        emails.append({
            "id": m["id"],
            "thread_id": msg["threadId"],
            "message_id": headers.get("message-id", ""),
            "sender": headers.get("from", "(unknown)"),
            "reply_to": headers.get("reply-to") or headers.get("from", ""),
            "subject": headers.get("subject", "(no subject)"),
            "domain": addr.split("@")[-1].lower() if "@" in addr else "",
            "labels": msg.get("labelIds", []),
            "has_unsubscribe": "list-unsubscribe" in headers,
        })
    return emails


def get_body(service, msg_id):
    """Return the plain-text body of an email (empty string if none)."""
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()

    def find_text(part):
        if part.get("mimeType") == "text/plain" and part["body"].get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
        for sub in part.get("parts", []):
            text = find_text(sub)
            if text:
                return text
        return ""

    return find_text(msg["payload"])


def get_or_create_label(service, name):
    """Return the label id for `name`, creating the label if needed."""
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"] == name:
            return label["id"]
    created = service.users().labels().create(userId="me", body={"name": name}).execute()
    return created["id"]


def apply_label(service, msg_id, label_name):
    label_id = get_or_create_label(service, label_name)
    service.users().messages().modify(
        userId="me", id=msg_id, body={"addLabelIds": [label_id]}
    ).execute()


def create_draft(service, email, body_text):
    """Save a reply as a Gmail draft in the same thread. Never sends anything."""
    subject = email["subject"]
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    msg = EmailMessage()
    msg["To"] = email["reply_to"]
    msg["Subject"] = subject
    if email["message_id"]:
        msg["In-Reply-To"] = email["message_id"]
        msg["References"] = email["message_id"]
    msg.set_content(body_text)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().drafts().create(
        userId="me",
        body={"message": {"raw": raw, "threadId": email["thread_id"]}},
    ).execute()


if __name__ == "__main__":
    service = get_service()
    for e in list_latest(service):
        print(f"{e['sender']}  |  {e['subject']}")