import json
import requests
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self, slack_webhook: Optional[str], discord_webhook: Optional[str]):
        self.slack_webhook = slack_webhook
        self.discord_webhook = discord_webhook

    def notify(self, title: str, body: str, extra: dict=None):
        payload = {"text": f"*{title}*\n{body}"}
        if self.slack_webhook:
            try:
                r = requests.post(self.slack_webhook, json={"text": f"{title}\n{body}"}, timeout=10)
                r.raise_for_status()
            except Exception as e:
                logger.exception("Failed to send Slack notification: %s", e)

        if self.discord_webhook:
            try:
                r = requests.post(self.discord_webhook, json={"content": f"**{title}**\n{body}"}, timeout=10)
                r.raise_for_status()
            except Exception as e:
                logger.exception("Failed to send Discord notification: %s", e)

        if not self.slack_webhook and not self.discord_webhook:
            print(f"[NOTIFY] {title}\n{body}\n")
