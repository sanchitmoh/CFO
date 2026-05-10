"""
Test Email Integration
Run this script to verify your email configuration is working.

Usage:
    python test_email.py your-email@example.com
"""
import asyncio
import sys
from services.email_service import email_service


async def test_basic_email(recipient: str):
    """Test basic email sending."""
    print(f"📧 Testing email to: {recipient}")
    print("=" * 60)
    
    success = await email_service.send_email(
        to_addresses=[recipient],
        subject="AI CFO Test Email",
        html_content="""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h1 style="color: #00E5CC;">Hello from AI CFO! 🚀</h1>
            <p>This is a test email to verify your email integration is working correctly.</p>
            <p>If you're seeing this, your email configuration is set up properly!</p>
            <hr>
            <p style="color: #666; font-size: 12px;">
                AI CFO Platform - Intelligent Financial Management
            </p>
        </body>
        </html>
        """,
        text_content="Hello from AI CFO! This is a test email.",
    )
    
    if success:
        print("✅ Email sent successfully!")
        print(f"   Check your inbox at: {recipient}")
    else:
        print("❌ Failed to send email")
        print("   Check your configuration in backend/.env")
        print("   Review backend logs for details")
    
    return success


async def test_alert_email(recipient: str):
    """Test alert email formatting."""
    print(f"\n📧 Testing alert email to: {recipient}")
    print("=" * 60)
    
    success = await email_service.send_alert_email(
        to_addresses=[recipient],
        alert_title="Low Cash Balance Warning",
        alert_message="Your cash balance has dropped below $5,000. Consider reviewing your expenses.",
        alert_severity="warning",
        alert_category="Cash Flow",
    )
    
    if success:
        print("✅ Alert email sent successfully!")
    else:
        print("❌ Failed to send alert email")
    
    return success


async def main():
    """Run email tests."""
    if len(sys.argv) < 2:
        print("Usage: python test_email.py your-email@example.com")
        sys.exit(1)
    
    recipient = sys.argv[1]
    
    print("\n" + "=" * 60)
    print("AI CFO Email Integration Test")
    print("=" * 60)
    
    # Test basic email
    basic_success = await test_basic_email(recipient)
    
    # Test alert email
    alert_success = await test_alert_email(recipient)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Basic Email: {'✅ PASS' if basic_success else '❌ FAIL'}")
    print(f"Alert Email: {'✅ PASS' if alert_success else '❌ FAIL'}")
    print("=" * 60)
    
    if basic_success and alert_success:
        print("\n🎉 All tests passed! Your email integration is working.")
    else:
        print("\n⚠️  Some tests failed. Check your configuration:")
        print("   1. Verify EMAIL_PROVIDER in backend/.env")
        print("   2. Check provider-specific credentials")
        print("   3. Review backend logs for error details")


if __name__ == "__main__":
    asyncio.run(main())
