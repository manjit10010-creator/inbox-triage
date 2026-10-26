import os

import requests
from dotenv import load_dotenv

load_dotenv()
url = os.environ["DISCORD_WEBHOOK_URL"]

response = requests.post(
    url,
    json={"content": "Test alert from inbox-triage"},
    timeout=30,
)
print(response.status_code, response.text)