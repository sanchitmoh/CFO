"""
Test calculator service with extreme values
"""
import asyncio
from decimal import Decimal

from sqlalchemy import select
from database import get_db
from models import Workspace
from schemas import AffordabilityRequest
from services.calculator_service import check_affordability


async def test_extreme_amount():
    """Test calculator with unrealistic 900 million amount"""
    async for db in get_db():
        # Get first workspace
        result = await db.execute(select(Workspace).limit(1))
        workspace = result.scalar_one_or_none()
        
        if not workspace:
            print("❌ No workspace found. Please create a workspace first.")
            return
        
        print(f"✅ Testing with workspace: {workspace.name}")
        print(f"   Currency: {workspace.currency}")
        print()
        
        # Test with extreme amount
        request = AffordabilityRequest(
            expense_name="sasa problm",
            amount=Decimal("900000000"),  # 900 million
            frequency="one_time",
            is_hire=False
        )
        
        print(f"📊 Testing affordability for:")
        print(f"   Expense: {request.expense_name}")
        print(f"   Amount: {request.amount:,.2f} {workspace.currency}")
        print(f"   Frequency: {request.frequency}")
        print()
        
        response = await check_affordability(db, workspace.id, request)
        
        print("📈 Results:")
        print(f"   Can Afford: {response.can_afford}")
        print(f"   Current Runway: {response.current_runway_months} months")
        print(f"   Projected Runway: {response.projected_runway_months} months")
        print(f"   Current Balance (3m): {response.current_balance_3m:,.2f}")
        print(f"   Projected Balance (3m): {response.projected_balance_3m:,.2f}")
        if response.break_even_revenue:
            print(f"   Break-even Revenue: {response.break_even_revenue:,.2f}")
        print()
        print(f"💡 AI Suggestion:")
        print(f"   {response.ai_suggestion}")
        print()
        
        # Check if warning is present
        if "⚠️ Unrealistic amount" in response.ai_suggestion:
            print("✅ Sanity check PASSED: Unrealistic amount detected!")
        else:
            print("⚠️  Sanity check not triggered (amount may be within normal range)")


async def test_normal_amount():
    """Test calculator with normal amount"""
    async for db in get_db():
        result = await db.execute(select(Workspace).limit(1))
        workspace = result.scalar_one_or_none()
        
        if not workspace:
            return
        
        print("\n" + "="*60)
        print("Testing with NORMAL amount (50,000)")
        print("="*60 + "\n")
        
        request = AffordabilityRequest(
            expense_name="New Marketing Campaign",
            amount=Decimal("50000"),
            frequency="one_time",
            is_hire=False
        )
        
        print(f"📊 Testing affordability for:")
        print(f"   Expense: {request.expense_name}")
        print(f"   Amount: {request.amount:,.2f} {workspace.currency}")
        print(f"   Frequency: {request.frequency}")
        print()
        
        response = await check_affordability(db, workspace.id, request)
        
        print("📈 Results:")
        print(f"   Can Afford: {response.can_afford}")
        print(f"   Current Runway: {response.current_runway_months} months")
        print(f"   Projected Runway: {response.projected_runway_months} months")
        print(f"   Current Balance (3m): {response.current_balance_3m:,.2f}")
        print(f"   Projected Balance (3m): {response.projected_balance_3m:,.2f}")
        if response.break_even_revenue:
            print(f"   Break-even Revenue: {response.break_even_revenue:,.2f}")
        print()
        print(f"💡 AI Suggestion:")
        print(f"   {response.ai_suggestion}")
        print()


if __name__ == "__main__":
    print("="*60)
    print("CALCULATOR SERVICE - EXTREME VALUE TEST")
    print("="*60 + "\n")
    
    asyncio.run(test_extreme_amount())
    asyncio.run(test_normal_amount())
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
