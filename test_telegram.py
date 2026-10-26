import os

import requests
from dotenv import load_dotenv

load_dotenv()
token = os.environ["TELEGRAM_BOT_TOKEN"]
chat_id = os.environ["TELEGRAM_CHAT_ID"]

response = requests.post(
    f"https://api.telegram.org/bot{token}/sendMessage",
    json={"chat_id": chat_id, "text": "Test alert from inbox-triage"},
    timeout=30,
)
print(response.status_code, response.text)