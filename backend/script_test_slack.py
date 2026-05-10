"""
Test Slack Integration
Run this script to verify your Slack configuration is working.

Usage:
    python test_slack.py
"""
import asyncio
from services.slack_service import slack_service


async def test_basic_message():
    """Test basic Slack message."""
    print("💬 Testing basic Slack message...")
    print("=" * 60)
    
    success = await slack_service.send_message(
        text="Hello from AI CFO! 🚀 This is a test message.",
    )
    
    if success:
        print("✅ Basic message sent successfully!")
        print("   Check your Slack channel")
    else:
        print("❌ Failed to send message")
        print("   Check your configuration in backend/.env")
    
    return success


async def test_alert_notification():
    """Test alert notification with rich formatting."""
    print("\n🚨 Testing alert notification...")
    print("=" * 60)
    
    success = await slack_service.send_alert(
        title="Low Cash Balance Warning",
        message="Your cash balance has dropped below $5,000. Consider reviewing your expenses to maintain healthy cash flow.",
        severity="warning",
        category="Cash Flow",
    )
    
    if success:
        print("✅ Alert notification sent successfully!")
    else:
        print("❌ Failed to send alert")
    
    return success


async def test_critical_alert():
    """Test critical alert."""
    print("\n🚨 Testing critical alert...")
    print("=" * 60)
    
    success = await slack_service.send_alert(
        title="Critical: Unusual Transaction Detected",
        message="A transaction of $25,000 was detected, which is 5x higher than your average. Please review immediately.",
        severity="critical",
        category="Anomaly Detection",
    )
    
    if success:
        print("✅ Critical alert sent successfully!")
    else:
        print("❌ Failed to send critical alert")
    
    return success


async def test_info_notification():
    """Test info notification."""
    print("\n ℹ️ Testing info notification...")
    print("=" * 60)
    
    success = await slack_service.send_alert(
        title="Monthly Report Generated",
        message="Your monthly financial report for January 2026 is ready for review.",
        severity="info",
        category="Reports",
    )
    
    if success:
        print("✅ Info notification sent successfully!")
    else:
        print("❌ Failed to send info notification")
    
    return success


async def test_report_notification():
    """Test report notification."""
    print("\n📊 Testing report notification...")
    print("=" * 60)
    
    success = await slack_service.send_report_notification(
        report_type="Monthly Financial Report",
        period="January 2026",
        summary="• Revenue: $125,000 (+12%)\n• Expenses: $85,000 (-5%)\n• Net Profit: $40,000\n• Cash Runway: 8.5 months",
    )
    
    if success:
        print("✅ Report notification sent successfully!")
    else:
        print("❌ Failed to send report notification")
    
    return success


async def test_anomaly_notification():
    """Test anomaly detection notification."""
    print("\n🔍 Testing anomaly detection notification...")
    print("=" * 60)
    
    success = await slack_service.send_anomaly_detection(
        transaction_description="Office Supplies - Staples",
        amount=2500.00,
        expected_range="$100 - $500",
    )
    
    if success:
        print("✅ Anomaly notification sent successfully!")
    else:
        print("❌ Failed to send anomaly notification")
    
    return success


async def main():
    """Run all Slack tests."""
    print("\n" + "=" * 60)
    print("AI CFO Slack Integration Test")
    print("=" * 60)
    
    # Run all tests
    results = {
        "Basic Message": await test_basic_message(),
        "Alert Notification": await test_alert_notification(),
        "Critical Alert": await test_critical_alert(),
        "Info Notification": await test_info_notification(),
        "Report Notification": await test_report_notification(),
        "Anomaly Notification": await test_anomaly_notification(),
    }
    
    # Wait a bit between messages to avoid rate limiting
    await asyncio.sleep(1)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print("=" * 60)
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All tests passed! Your Slack integration is working.")
        print("   Check your Slack channel to see all the test messages.")
    else:
        print("\n⚠️  Some tests failed. Check your configuration:")
        print("   1. Verify SLACK_ENABLED=true in backend/.env")
        print("   2. Check SLACK_WEBHOOK_URL or SLACK_BOT_TOKEN is set")
        print("   3. Ensure the webhook/bot has access to the channel")
        print("   4. Review backend logs for error details")


if __name__ == "__main__":
    asyncio.run(main())
