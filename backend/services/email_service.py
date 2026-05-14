"""
AI CFO — Email Service
Supports multiple email providers: SendGrid, AWS SES, SMTP
"""
import logging
from datetime import datetime, timezone
from html import escape
from typing import Any, List

from config import settings

logger = logging.getLogger(__name__)


def _app_url(path: str) -> str:
    base = settings.APP_BASE_URL.rstrip("/")
    suffix = path if path.startswith("/") else f"/{path}"
    return f"{base}{suffix}"


def _format_date(value: datetime | None) -> str:
    if value is None:
        return "TBD"
    current = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return current.strftime("%d %b %Y")


def _format_currency(value: float, currency_code: str) -> str:
    return f"{currency_code} {value:,.2f}"


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

    async def send_invoice_email(
        self,
        invoice: Any,
        to_address: str | None = None,
    ) -> bool:
        """Send a formatted invoice email to the invoice recipient."""
        recipient = to_address or getattr(invoice, "client_email", None)
        if not recipient:
            logger.warning("Invoice email skipped because no recipient email is set")
            return False

        invoice_number = str(getattr(invoice, "invoice_number", "Invoice"))
        client_name = escape(str(getattr(invoice, "client_name", "Client")))
        currency_code = str(getattr(invoice, "currency_code", "INR"))
        subtotal = float(getattr(invoice, "subtotal", 0) or 0)
        tax_amount = float(getattr(invoice, "tax_amount", 0) or 0)
        total = float(getattr(invoice, "total", 0) or 0)
        amount_due = float(getattr(invoice, "amount_due", total) or 0)
        tax_rate = float(getattr(invoice, "tax_rate", 0) or 0) * 100
        issue_date = _format_date(getattr(invoice, "issue_date", None))
        due_date = _format_date(getattr(invoice, "due_date", None))
        notes_raw = str(getattr(invoice, "notes", "") or "").strip()
        notes_html = escape(notes_raw).replace("\n", "<br/>") if notes_raw else ""
        notes_text = notes_raw if notes_raw else "No additional notes."

        line_items = list(getattr(invoice, "line_items", None) or getattr(invoice, "items_json", None) or [])
        rows = []
        text_lines = []
        for item in line_items:
            description = escape(str(item.get("description", "Line item")))
            quantity = float(item.get("quantity", 0) or 0)
            unit_price = float(item.get("unit_price", 0) or 0)
            amount = float(item.get("amount", quantity * unit_price) or 0)
            rows.append(
                f"""
                <tr>
                    <td style="padding: 12px 0; color: #E8E4DE; border-bottom: 1px solid #232323;">{description}</td>
                    <td style="padding: 12px 0; color: #9A948A; text-align: center; border-bottom: 1px solid #232323;">{quantity:g}</td>
                    <td style="padding: 12px 0; color: #9A948A; text-align: right; border-bottom: 1px solid #232323;">{_format_currency(unit_price, currency_code)}</td>
                    <td style="padding: 12px 0; color: #E8E4DE; text-align: right; border-bottom: 1px solid #232323;">{_format_currency(amount, currency_code)}</td>
                </tr>
                """
            )
            text_lines.append(f"- {description}: {quantity:g} × {_format_currency(unit_price, currency_code)} = {_format_currency(amount, currency_code)}")

        line_items_html = "".join(rows) or """
            <tr>
                <td colspan="4" style="padding: 12px 0; color: #9A948A; border-bottom: 1px solid #232323;">No line items were attached.</td>
            </tr>
        """
        line_items_text = "\n".join(text_lines) if text_lines else "- No line items were attached."

        subject = f"Invoice {invoice_number} from {settings.EMAIL_FROM_NAME}"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="margin:0; background:#080808; color:#E8E4DE; font-family:Arial, sans-serif;">
            <div style="max-width:680px; margin:0 auto; padding:32px 20px;">
                <div style="border:1px solid #232323; border-radius:20px; overflow:hidden; background:#111111;">
                    <div style="padding:28px 32px; background:linear-gradient(135deg, #000000 0%, #17120A 100%); border-bottom:1px solid #232323;">
                        <div style="font-size:12px; letter-spacing:0.18em; text-transform:uppercase; color:#C9A962;">AI CFO Platform</div>
                        <h1 style="margin:12px 0 6px; font-size:30px; line-height:1.1;">Invoice {escape(invoice_number)}</h1>
                        <p style="margin:0; color:#9A948A; font-size:15px;">Issued for {client_name}. Payment due by {due_date}.</p>
                    </div>

                    <div style="padding:28px 32px;">
                        <div style="display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:12px; margin-bottom:24px;">
                            <div style="padding:14px 16px; border:1px solid #232323; border-radius:14px; background:#0D0D0D;">
                                <div style="font-size:11px; letter-spacing:0.12em; text-transform:uppercase; color:#9A948A;">Issue Date</div>
                                <div style="margin-top:6px; font-size:18px; color:#E8E4DE;">{issue_date}</div>
                            </div>
                            <div style="padding:14px 16px; border:1px solid #232323; border-radius:14px; background:#0D0D0D;">
                                <div style="font-size:11px; letter-spacing:0.12em; text-transform:uppercase; color:#9A948A;">Total</div>
                                <div style="margin-top:6px; font-size:18px; color:#E8E4DE;">{_format_currency(total, currency_code)}</div>
                            </div>
                            <div style="padding:14px 16px; border:1px solid #232323; border-radius:14px; background:#0D0D0D;">
                                <div style="font-size:11px; letter-spacing:0.12em; text-transform:uppercase; color:#9A948A;">Amount Due</div>
                                <div style="margin-top:6px; font-size:18px; color:#C9A962;">{_format_currency(amount_due, currency_code)}</div>
                            </div>
                        </div>

                        <table style="width:100%; border-collapse:collapse; margin-bottom:24px;">
                            <thead>
                                <tr>
                                    <th style="padding:0 0 10px; text-align:left; font-size:11px; letter-spacing:0.12em; text-transform:uppercase; color:#9A948A;">Description</th>
                                    <th style="padding:0 0 10px; text-align:center; font-size:11px; letter-spacing:0.12em; text-transform:uppercase; color:#9A948A;">Qty</th>
                                    <th style="padding:0 0 10px; text-align:right; font-size:11px; letter-spacing:0.12em; text-transform:uppercase; color:#9A948A;">Unit</th>
                                    <th style="padding:0 0 10px; text-align:right; font-size:11px; letter-spacing:0.12em; text-transform:uppercase; color:#9A948A;">Amount</th>
                                </tr>
                            </thead>
                            <tbody>{line_items_html}</tbody>
                        </table>

                        <div style="border:1px solid #232323; border-radius:16px; background:#0D0D0D; padding:18px 20px; margin-bottom:24px;">
                            <div style="display:flex; justify-content:space-between; margin-bottom:10px; color:#9A948A;">
                                <span>Subtotal</span>
                                <span>{_format_currency(subtotal, currency_code)}</span>
                            </div>
                            <div style="display:flex; justify-content:space-between; margin-bottom:10px; color:#9A948A;">
                                <span>Tax ({tax_rate:.2f}%)</span>
                                <span>{_format_currency(tax_amount, currency_code)}</span>
                            </div>
                            <div style="display:flex; justify-content:space-between; padding-top:12px; border-top:1px solid #232323; font-size:18px; color:#E8E4DE;">
                                <strong>Total due</strong>
                                <strong>{_format_currency(amount_due, currency_code)}</strong>
                            </div>
                        </div>

                        <div style="padding:18px 20px; border-radius:16px; background:#0A0A0A; border:1px solid #232323;">
                            <div style="font-size:11px; letter-spacing:0.12em; text-transform:uppercase; color:#C9A962; margin-bottom:10px;">Notes & Terms</div>
                            <div style="color:#CFC8BF; line-height:1.7;">{notes_html or "No additional notes."}</div>
                        </div>

                        <div style="margin-top:24px;">
                            <a href="{_app_url('/invoices')}" style="display:inline-block; padding:12px 18px; border-radius:999px; background:#C9A962; color:#0B0907; text-decoration:none; font-weight:bold;">Open invoices workspace</a>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
Invoice {invoice_number}

Client: {getattr(invoice, "client_name", "Client")}
Issue date: {issue_date}
Due date: {due_date}
Subtotal: {_format_currency(subtotal, currency_code)}
Tax ({tax_rate:.2f}%): {_format_currency(tax_amount, currency_code)}
Total due: {_format_currency(amount_due, currency_code)}

Line items:
{line_items_text}

Notes:
{notes_text}

Open invoices workspace: {_app_url('/invoices')}
        """.strip()

        return await self.send_email(
            to_addresses=[recipient],
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

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
