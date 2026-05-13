"""
AI CFO — Email Service
Supports multiple email providers: SendGrid, AWS SES, SMTP
"""
import logging
from typing import List

from config import settings

logger = logging.getLogger(__name__)


def _app_url(path: str) -> str:
    base = settings.APP_BASE_URL.rstrip("/")
    suffix = path if path.startswith("/") else f"/{path}"
    return f"{base}{suffix}"


class EmailService:
    """Unified email service supporting multiple providers."""
    
    async def send_email(
        self,
        to_addresses: List[str],
        subject: str,
        html_content: str,
        text_content: str | None = None,
    ) -> bool:
        """
        Send email using configured provider.
        
        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject line
            html_content: HTML version of email body
            text_content: Plain text version (optional, for fallback)
        
        Returns:
            True if email sent successfully, False otherwise
        """
        if not to_addresses:
            logger.warning("No recipient addresses provided")
            return False
        
        try:
            if settings.EMAIL_PROVIDER == "sendgrid":
                return await self._send_sendgrid(to_addresses, subject, html_content, text_content)
            elif settings.EMAIL_PROVIDER == "aws_ses":
                return await self._send_aws_ses(to_addresses, subject, html_content, text_content)
            elif settings.EMAIL_PROVIDER == "smtp":
                return await self._send_smtp(to_addresses, subject, html_content, text_content)
            else:
                logger.error(f"Unknown email provider: {settings.EMAIL_PROVIDER}")
                return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            return False
    
    async def _send_sendgrid(
        self,
        to_addresses: List[str],
        subject: str,
        html_content: str,
        text_content: str | None,
    ) -> bool:
        """Send email via SendGrid."""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content
        except ImportError:
            logger.error("SendGrid not installed. Run: pip install sendgrid")
            return False
        
        if not settings.SENDGRID_API_KEY:
            logger.error("SENDGRID_API_KEY not configured")
            return False
        
        message = Mail(
            from_email=Email(settings.EMAIL_FROM_ADDRESS, settings.EMAIL_FROM_NAME),
            to_emails=[To(addr) for addr in to_addresses],
            subject=subject,
            html_content=Content("text/html", html_content),
        )
        
        if text_content:
            message.add_content(Content("text/plain", text_content))
        
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        
        logger.info(f"SendGrid email sent: status={response.status_code}, to={to_addresses}")
        return response.status_code in [200, 201, 202]
    
    async def _send_aws_ses(
        self,
        to_addresses: List[str],
        subject: str,
        html_content: str,
        text_content: str | None,
    ) -> bool:
        """Send email via AWS SES."""
        try:
            import boto3
        except ImportError:
            logger.error("boto3 not installed. Run: pip install boto3")
            return False
        
        if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
            logger.error("AWS credentials not configured")
            return False
        
        client = boto3.client(
            'ses',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        
        body = {"Html": {"Data": html_content, "Charset": "UTF-8"}}
        if text_content:
            body["Text"] = {"Data": text_content, "Charset": "UTF-8"}
        
        response = client.send_email(
            Source=f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>",
            Destination={"ToAddresses": to_addresses},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": body,
            },
        )
        
        logger.info(f"AWS SES email sent: message_id={response['MessageId']}, to={to_addresses}")
        return True
    
    async def _send_smtp(
        self,
        to_addresses: List[str],
        subject: str,
        html_content: str,
        text_content: str | None,
    ) -> bool:
        """Send email via SMTP."""
        try:
            import aiosmtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
        except ImportError:
            logger.error("aiosmtplib not installed. Run: pip install aiosmtplib")
            return False
        
        if not settings.SMTP_HOST or not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            logger.error("SMTP credentials not configured")
            return False
        
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>"
        message["To"] = ", ".join(to_addresses)
        
        if text_content:
            message.attach(MIMEText(text_content, "plain"))
        message.attach(MIMEText(html_content, "html"))
        
        # Use start_tls=True for STARTTLS (port 587)
        # Use tls=True for direct TLS (port 465)
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            start_tls=settings.SMTP_USE_TLS,  # Changed from use_tls to start_tls
        )
        
        logger.info(f"SMTP email sent: to={to_addresses}")
        return True
    
    async def send_alert_email(
        self,
        to_addresses: List[str],
        alert_title: str,
        alert_message: str,
        alert_severity: str,
        alert_category: str,
    ) -> bool:
        """
        Send a formatted alert email.
        
        Args:
            to_addresses: List of recipient email addresses
            alert_title: Alert title
            alert_message: Alert message/description
            alert_severity: Alert severity (critical, warning, info)
            alert_category: Alert category
        
        Returns:
            True if email sent successfully
        """
        # Color coding for severity
        severity_colors = {
            "critical": "#FF0000",
            "warning": "#FFA500",
            "info": "#00E5CC",
        }
        color = severity_colors.get(alert_severity, "#808080")
        
        subject = f"AI CFO Alert: {alert_title}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #0A0F1E 0%, #1E2A42 100%); 
                           color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
                .alert-box {{ background: white; border-left: 4px solid {color}; 
                              padding: 20px; margin: 20px 0; border-radius: 4px; }}
                .severity {{ display: inline-block; padding: 4px 12px; border-radius: 12px; 
                            background: {color}; color: white; font-size: 12px; 
                            font-weight: bold; text-transform: uppercase; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #00E5CC; 
                          color: white; text-decoration: none; border-radius: 6px; 
                          font-weight: bold; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">🚨 AI CFO Alert</h1>
                </div>
                <div class="content">
                    <div class="alert-box">
                        <h2 style="margin-top: 0; color: {color};">{alert_title}</h2>
                        <p style="font-size: 16px; margin: 15px 0;">{alert_message}</p>
                        <p style="margin: 10px 0;">
                            <span class="severity">{alert_severity}</span>
                            <span style="margin-left: 10px; color: #666;">Category: {alert_category}</span>
                        </p>
                    </div>
                    <p style="color: #666;">
                        This alert was generated by your AI CFO platform based on your configured thresholds 
                        and financial activity.
                    </p>
                    <a href="{_app_url('/alerts')}" class="button">View All Alerts</a>
                </div>
                <div class="footer">
                    <p>AI CFO Platform - Intelligent Financial Management</p>
                    <p>To manage your notification preferences, visit Settings and open Alerts</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        AI CFO ALERT
        
        {alert_title}
        
        {alert_message}
        
        Severity: {alert_severity.upper()}
        Category: {alert_category}
        
        ---
        AI CFO Platform - Intelligent Financial Management
        View alerts: {_app_url('/alerts')}
        """
        
        return await self.send_email(
            to_addresses=to_addresses,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )


# Singleton instance
email_service = EmailService()
