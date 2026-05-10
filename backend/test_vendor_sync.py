"""Quick test script for vendor sync + spend map."""
import asyncio
from database import get_db_session
from models import Vendor, Transaction
from sqlalchemy import select, func
from services.vendor_service import sync_vendors_from_transactions, get_vendor_spend_map


async def test():
    async for db in get_db_session():
        # Find a workspace with transactions
        result = await db.execute(
            select(Transaction.workspace_id, func.count(Transaction.id))
            .group_by(Transaction.workspace_id)
            .limit(1)
        )
        row = result.first()
        if not row:
            print("No transactions found")
            return
        ws_id = row[0]
        print(f"Workspace: {ws_id}, Transactions: {row[1]}")

        # Run sync
        created = await sync_vendors_from_transactions(db, ws_id)
        await db.commit()
        print(f"Synced: {created} new vendors")

        # Check vendors
        vendors = await db.execute(
            select(Vendor.name, Vendor.category).where(
                Vendor.workspace_id == ws_id
            ).limit(10)
        )
        print("--- Vendors (name | category) ---")
        for v in vendors.all():
            name = v[0] or "?"
            cat = v[1] or "None"
            print(f"  {name:30s} | {cat}")

        # Check spend map
        spend = await get_vendor_spend_map(db, ws_id)
        print(f"\n--- Spend Map ({len(spend)} vendors, showing first 5) ---")
        for name, stats in list(spend.items())[:5]:
            ts = stats["total_spent"]
            tc = stats["transaction_count"]
            print(f"  {name:30s} | spent={ts:.2f} | txns={tc}")


asyncio.run(test())
