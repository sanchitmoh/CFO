"""
AI CFO — Slack Service
Send notifications to Slack via Webhooks or Bot API
"""
import logging
from typing import Dict, Any

from config import settings

logger = logging.getLogger(__name__)


def _app_url(path: str) -> str:
    base = settings.APP_BASE_URL.rstrip("/")
    suffix = path if path.startswith("/") else f"/{path}"
    return f"{base}{suffix}"


class SlackService:
    """Slack notification service."""
    
    async def send_message(
        self,
        text: str,
        channel: str | None = None,
        blocks: list[Dict[str, Any]] | None = None,
        webhook_url: str | None = None,
    ) -> bool:
        """
        Send a message to Slack.
        
        Args:
            text: Plain text message (fallback for notifications)
            channel: Channel to send to (only for bot token, ignored for webhooks)
            blocks: Rich formatting blocks (optional)
        
        Returns:
            True if message sent successfully
        """
        try:
            if webhook_url:
                return await self._send_via_webhook(webhook_url, text, blocks)

            has_bot_token = bool(
                settings.SLACK_BOT_TOKEN
                and not settings.SLACK_BOT_TOKEN.startswith("xoxb-your")
            )
            has_webhook = bool(
                settings.SLACK_WEBHOOK_URL
                and not settings.SLACK_WEBHOOK_URL.endswith("YOUR/WEBHOOK/URL")
            )

            if not has_bot_token and not has_webhook:
                logger.debug("Slack is not configured, skipping notification")
                return False

            if has_bot_token:
                return await self._send_via_bot(text, channel, blocks)
            if has_webhook:
                return await self._send_via_webhook(str(settings.SLACK_WEBHOOK_URL), text, blocks)
            else:
                logger.error("No Slack credentials configured (need SLACK_BOT_TOKEN or SLACK_WEBHOOK_URL)")
                return False
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}", exc_info=True)
            return False
    
    async def _send_via_webhook(self, webhook_url: str, text: str, blocks: list | None) -> bool:
        """Send message via Incoming Webhook (simple method)."""
        try:
            import httpx
        except ImportError:
            logger.error("httpx not installed. Run: pip install httpx")
            return False
        
        if not webhook_url:
            logger.error("Slack webhook URL not configured")
            return False
        
        payload = {"text": text}
        if blocks:
            payload["blocks"] = blocks
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()
        
        logger.info("Slack webhook message sent successfully")
        return True
    
    async def _send_via_bot(self, text: str, channel: str | None, blocks: list | None) -> bool:
        """Send message via Bot Token (advanced features)."""
        try:
            from slack_sdk.web.async_client import AsyncWebClient
        except ImportError:
            logger.error("slack-sdk not installed. Run: pip install slack-sdk")
            return False
        
        if not settings.SLACK_BOT_TOKEN:
            logger.error("SLACK_BOT_TOKEN not configured")
            return False
        
        client = AsyncWebClient(token=settings.SLACK_BOT_TOKEN)
        
        response = await client.chat_postMessage(
            channel=channel or settings.SLACK_DEFAULT_CHANNEL,
            text=text,
            blocks=blocks,
        )
        
        logger.info(f"Slack bot message sent: ts={response['ts']}, channel={channel}")
        return response["ok"]
    
    async def send_alert(
        self,
        title: str,
        message: str,
        severity: str = "info",
        channel: str | None = None,
        category: str | None = None,
        webhook_url: str | None = None,
    ) -> bool:
        """
        Send a formatted alert to Slack with rich formatting.
        
        Args:
            title: Alert title
            message: Alert message/description
            severity: Alert severity (critical, warning, info, success)
            channel: Channel to send to (optional, uses default if not specified)
            category: Alert category (optional)
        
        Returns:
            True if alert sent successfully
        """
        # Color coding for severity
        colors = {
            "critical": "#FF0000",
            "warning": "#FFA500",
            "info": "#00E5CC",
            "success": "#00FF00",
        }
        color = colors.get(severity, "#808080")
        
        # Emoji mapping
        emojis = {
            "critical": "🚨",
            "warning": "⚠️",
            "info": "ℹ️",
            "success": "✅",
        }
        emoji = emojis.get(severity, "📢")
        
        # Build context elements
        context_elements = [
            {
                "type": "mrkdwn",
                "text": f"*Severity:* {severity.upper()}",
            }
        ]
        
        if category:
            context_elements.append({
                "type": "mrkdwn",
                "text": f"*Category:* {category}",
            })
        
        # Rich formatting with blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {title}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message,
                },
            },
            {
                "type": "context",
                "elements": context_elements,
            },
            {
                "type": "divider",
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"AI CFO Platform | <{_app_url('/alerts')}|View All Alerts>",
                    }
                ],
            },
        ]
        
        # Fallback text for notifications
        fallback_text = f"{emoji} {title}: {message}"
        
        return await self.send_message(
            text=fallback_text,
            channel=channel,
            blocks=blocks,
            webhook_url=webhook_url,
        )
    
    async def send_report_notification(
        self,
        report_type: str,
        period: str,
        summary: str,
        channel: str | None = None,
    ) -> bool:
        """
        Send a report generation notification.
        
        Args:
            report_type: Type of report (e.g., "Monthly Financial Report")
            period: Report period (e.g., "January 2026")
            summary: Brief summary of key metrics
            channel: Channel to send to (optional)
        
        Returns:
            True if notification sent successfully
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 {report_type} Ready",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Period:* {period}\n\n{summary}",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Report",
                        },
                        "url": _app_url("/reports"),
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Download PDF",
                        },
                        "url": _app_url("/reports/export"),
                    },
                ],
            },
        ]
        
        return await self.send_message(
            text=f"📊 {report_type} for {period} is ready",
            channel=channel,
            blocks=blocks,
        )
    
    async def send_anomaly_detection(
        self,
        transaction_description: str,
        amount: float,
        expected_range: str,
        channel: str | None = None,
        currency_symbol: str = "$",
    ) -> bool:
        """
        Send an anomaly detection notification.
        
        Args:
            transaction_description: Description of the anomalous transaction
            amount: Transaction amount
            expected_range: Expected range for this type of transaction
            channel: Channel to send to (optional)
            currency_symbol: The currency symbol to use (default: $)
        
        Returns:
            True if notification sent successfully
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔍 Anomaly Detected",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Transaction:*\n{transaction_description}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Amount:*\n{currency_symbol}{amount:,.2f}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Expected Range:*\n{expected_range}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "This transaction is significantly different from your typical spending pattern.",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Review Transaction",
                        },
                        "url": _app_url("/transactions"),
                        "style": "primary",
                    },
                ],
            },
        ]
        
        return await self.send_message(
            text=f"🔍 Anomaly detected: {transaction_description} ({currency_symbol}{amount:,.2f})",
            channel=channel,
            blocks=blocks,
        )


# Singleton instance
slack_service = SlackService()
