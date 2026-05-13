"""Debug: check workspace_id alignment."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

async def main():
    from database import AsyncSessionLocal
    from sqlalchemy import text

    async with AsyncSessionLocal() as session:
        # 1. What workspace_ids exist in transactions?
        r = await session.execute(text("""
            SELECT workspace_id, count(*), min(date), max(date)
            FROM transactions
            GROUP BY workspace_id
        """))
        print("Transaction workspace_ids:")
        for row in r:
            print(f"  workspace_id={row[0]}  count={row[1]}  dates={row[2]} to {row[3]}")

        # 2. What workspace_ids exist in the users table?
        r = await session.execute(text("SELECT id, workspace_id, email FROM users"))
        print("\nUsers:")
        for row in r:
            print(f"  user_id={row[0]}  workspace_id={row[1]}  email={row[2]}")

        # 3. What workspaces exist?
        r = await session.execute(text("SELECT id, name FROM workspaces"))
        print("\nWorkspaces:")
        for row in r:
            print(f"  id={row[0]}  name={row[1]}")

        # 4. Test the exact aggregation query the dashboard runs
        print("\n--- Simulating dashboard q_totals ---")
        r = await session.execute(text("""
            SELECT type, sum(amount), count(id)
            FROM transactions
            WHERE workspace_id = (SELECT workspace_id FROM users LIMIT 1)
              AND date >= (SELECT max(date) - INTERVAL '180 days' FROM transactions)
            GROUP BY type
        """))
        for row in r:
            print(f"  type={row[0]}  sum={row[1]}  count={row[2]}")

if __name__ == "__main__":
    asyncio.run(main())
