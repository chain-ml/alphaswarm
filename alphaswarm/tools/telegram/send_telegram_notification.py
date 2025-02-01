import asyncio
import logging
from typing import Optional

from alphaswarm.agent.clients.telegram_bot import TelegramApp
from smolagents import Tool

logger = logging.getLogger(__name__)


class SendTelegramNotificationTool(Tool):
    name = "send_telegram_notification"
    description = """Send a Telegram notification to the registered Telegram channel with the given message and priority.
    Returns a string describing whether the notification was sent successfully or not."""

    inputs = {
        "message": {"type": "string", "description": "The message to send.", "required": True},
        "confidence": {"type": "number", "description": "The confidence score, between 0 and 1.", "required": True},
        "priority": {
            "type": "string",
            "description": "The priority of the alert, one of 'high', 'medium', 'low'.",
            "required": True,
        },
    }
    output_type = "string"

    def __init__(self, telegram_bot_token: str, chat_id: int) -> None:
        super().__init__()

        self.token = telegram_bot_token
        self.chat_id = chat_id

        self._telegram_app = TelegramApp(bot_token=self.token)

    def forward(self, message: str, confidence: float, priority: str) -> str:
        message_to_send = self.format_alert_message(message=message, confidence=confidence, priority=priority)
        asyncio.run(self._telegram_app.send_message(chat_id=self.chat_id, message=message_to_send))
        return "Message sent successfully"

    @classmethod
    def format_alert_message(cls, message: str, confidence: float, priority: Optional[str]) -> str:
        """Format the analysis result into a user-friendly message"""

        priority_str = f"*Priority:* {cls._get_priority_emoji(priority)} {priority.upper() if priority else ''}"

        return "\n\n".join(
            [
                "🔔 *AI Agent Alert*",
                priority_str,
                f"*Details:*\n{message}",
                f"*Confidence:* {confidence * 100:.1f}%",
            ]
        )

    @staticmethod
    def _get_priority_emoji(priority: Optional[str]) -> str:
        default = "⚪"
        if not priority:
            return default
        return {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, default)
