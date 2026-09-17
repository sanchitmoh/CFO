"""
Test script for Resend email service
Run with: python test_resend_email.py
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from services.email_service import email_service
from config import settings


async def test_resend_email():
    """Test Resend email configuration and send a test email."""
    
    print("=" * 60)
    print("RESEND EMAIL SERVICE TEST")
    print("=" * 60)
    print()
    
    # Check configuration
    print("📋 Configuration Check:")
    print(f"   EMAIL_PROVIDER: {settings.EMAIL_PROVIDER}")
    print(f"   RESEND_API_KEY: {'✅ Set' if settings.RESEND_API_KEY else '❌ Not set'}")
    print(f"   EMAIL_FROM_ADDRESS: {settings.EMAIL_FROM_ADDRESS}")
    print(f"   EMAIL_FROM_NAME: {settings.EMAIL_FROM_NAME}")
    print()
    
    if not settings.RESEND_API_KEY:
        print("❌ ERROR: RESEND_API_KEY is not set in .env file")
        print()
        print("To fix:")
        print("1. Go to https://resend.com/api-keys")
        print("2. Create an API key")
        print("3. Add to backend/.env:")
        print("   RESEND_API_KEY=re_YourActualKeyHere")
        print()
        return False
    
    if settings.EMAIL_PROVIDER.lower() != "resend":
        print(f"⚠️  WARNING: EMAIL_PROVIDER is '{settings.EMAIL_PROVIDER}', not 'resend'")
        print("   The test will still run but emails won't use Resend")
        print()
    
    # Prompt for recipient email
    print("📧 Test Email:")
    recipient = input("   Enter recipient email (or press Enter to use default): ").strip()
    if not recipient:
        recipient = settings.EMAIL_FROM_ADDRESS
    
    print(f"   Sending to: {recipient}")
    print()
    print("🚀 Sending test email...")
    print()
    
    try:
        # Test 1: Simple email
        success = await email_service.send_email(
            to_addresses=[recipient],
            subject="✅ Resend Test Email - AI CFO Platform",
            html_content="""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #0A0F1E 0%, #1E2A42 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                    <h1 style="margin: 0;">✅ Success!</h1>
                </div>
                <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px;">
                    <h2 style="color: #0A0F1E;">Resend is working!</h2>
                    <p>Your AI CFO Platform can now send emails via Resend API.</p>
                    <ul style="list-style: none; padding: 0;">
                        <li>✅ API key configured correctly</li>
                        <li>✅ Email service operational</li>
                        <li>✅ Ready for production use</li>
                    </ul>
                    <p style="color: #666; font-size: 14px; margin-top: 30px;">
                        This is a test email from your AI CFO Platform.
                    </p>
                </div>
            </body>
            </html>
            """,
            text_content="""
            ✅ Success! Resend is working!
            
            Your AI CFO Platform can now send emails via Resend API.
            
            ✅ API key configured correctly
            ✅ Email service operational
            ✅ Ready for production use
            
            This is a test email from your AI CFO Platform.
            """
        )
        
        if success:
            print("✅ SUCCESS! Test email sent successfully!")
            print()
            print("📬 Check your inbox:")
            print(f"   Recipient: {recipient}")
            print(f"   Subject: ✅ Resend Test Email - AI CFO Platform")
            print()
            print("Note: Check spam folder if you don't see it in inbox")
            print()
            
            # Test 2: Alert email
            print("🚨 Sending test alert email...")
            alert_success = await email_service.send_alert_email(
                to_addresses=[recipient],
                alert_title="Low Cash Balance Test Alert",
                alert_message="This is a test alert from your AI CFO Platform. Your actual alerts will look like this!",
                alert_severity="warning",
                alert_category="test",
            )
            
            if alert_success:
                print("✅ Alert email sent successfully!")
                print()
            else:
                print("❌ Alert email failed")
                print()
            
            print("=" * 60)
            print("NEXT STEPS:")
            print("=" * 60)
            print()
            print("1. Check your email inbox for 2 test emails")
            print("2. If using production, verify your domain at:")
            print("   https://resend.com/domains")
            print("3. Update EMAIL_FROM_ADDRESS to use your domain")
            print("4. Remove the 'temporarily unavailable' banner from:")
            print("   frontend/app/(app)/settings/page.tsx")
            print("5. Deploy to Render with RESEND_API_KEY env var")
            print()
            return True
            
        else:
            print("❌ FAILED: Email was not sent")
            print()
            print("Common issues:")
            print("1. Invalid API key")
            print("2. Domain not verified (use onboarding@resend.dev for testing)")
            print("3. Rate limit exceeded")
            print("4. Network issues")
            print()
            print("Check backend logs for detailed error messages")
            print()
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_resend_email())
    sys.exit(0 if result else 1)
