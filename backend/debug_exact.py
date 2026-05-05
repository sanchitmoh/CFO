"""Debug: exact dashboard simulation with correct workspace."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

async def main():
    from database import AsyncSessionLocal
    from sqlalchemy import text

    ws_id = "b61bbd4d-37ed-4e73-a059-085e3e478827"

    async with AsyncSessionLocal() as session:
        # Test 1: Simple count with workspace filter
        r = await session.execute(text(f"""
            SELECT count(*) FROM transactions WHERE workspace_id = '{ws_id}'
        """))
        print(f"Count with workspace filter (no RLS): {r.scalar()}")

        # Test 2: With date range
        r = await session.execute(text(f"""
            SELECT type, sum(amount), count(id)
            FROM transactions
            WHERE workspace_id = '{ws_id}'
              AND date >= '2024-05-01'
            GROUP BY type
        """))
        print("With date filter (2024-05-01+):")
        rows = r.fetchall()
        if not rows:
            print("  (empty!)")
        for row in rows:
            print(f"  type={row[0]}  sum={row[1]}  count={row[2]}")

        # Test 3: Now with SET LOCAL RLS
        await session.execute(text("BEGIN"))
        await session.execute(text(f"SET LOCAL app.workspace_id = '{ws_id}'"))
        r = await session.execute(text(f"""
            SELECT type, sum(amount), count(id)
            FROM transactions
            WHERE workspace_id = '{ws_id}'
              AND date >= '2024-05-01'
            GROUP BY type
        """))
        print("\nWith RLS SET LOCAL + date filter:")
        rows = r.fetchall()
        if not rows:
            print("  (empty!)")
        for row in rows:
            print(f"  type={row[0]}  sum={row[1]}  count={row[2]}")

        # Test 4: Check if RLS policies are active
        r = await session.execute(text("""
            SELECT tablename, policyname, cmd, qual
            FROM pg_policies
            WHERE tablename = 'transactions'
        """))
        print("\nRLS policies on transactions:")
        rows = r.fetchall()
        if not rows:
            print("  (none)")
        for row in rows:
            print(f"  table={row[0]}  policy={row[1]}  cmd={row[2]}  qual={row[3]}")

        # Test 5: Is RLS enabled on the table?
        r = await session.execute(text("""
            SELECT relname, relrowsecurity, relforcerowsecurity
            FROM pg_class
            WHERE relname = 'transactions'
        """))
        print("\nRLS status on transactions table:")
        for row in r:
            print(f"  table={row[0]}  rls_enabled={row[1]}  force_rls={row[2]}")

if __name__ == "__main__":
    asyncio.run(main())
