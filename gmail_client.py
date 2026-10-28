import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Read-only for now. We'll widen this in a later stage.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_service():
    """Log in (first run opens a browser) and return a Gmail API client."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def list_latest(service, n=5):
    """Return the n newest inbox emails as dicts: id, sender, subject."""
    result = service.users().messages().list(
        userId="me", labelIds=["INBOX"], maxResults=n
    ).execute()

    emails = []
    for m in result.get("messages", []):
        msg = service.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["From", "Subject"],
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        emails.append({
            "id": m["id"],
            "sender": headers.get("From", "(unknown)"),
            "subject": headers.get("Subject", "(no subject)"),
        })
    return emails


if __name__ == "__main__":
    service = get_service()
    for e in list_latest(service):
        print(f"{e['sender']}  |  {e['subject']}")