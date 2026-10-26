import os

import requests
from dotenv import load_dotenv

load_dotenv()
token = os.environ["TELEGRAM_BOT_TOKEN"]

data = requests.get(
    f"https://api.telegram.org/bot{token}/getUpdates", timeout=30
).json()

if not data.get("ok"):
    print("Telegram rejected the request:", data)
elif not data["result"]:
    print("No messages found. Send your bot a message, then run this again.")
else:
    for update in data["result"]:
        message = update.get("message")
        if message:
            chat = message["chat"]
            print("Chat ID:", chat["id"], "| name:", chat.get("first_name"))