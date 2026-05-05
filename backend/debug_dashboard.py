"""Debug: check what's actually in the DB and clear stale cache."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

async def main():
    from database import AsyncSessionLocal
    from sqlalchemy import text

    async with AsyncSessionLocal() as session:
        # 1. Count transactions
        r = await session.execute(text("SELECT count(*), min(date), max(date) FROM transactions"))
        row = r.one()
        print(f"Total transactions: {row[0]}")
        print(f"Date range: {row[1]} to {row[2]}")

        # 2. Check types and amounts
        r = await session.execute(text("""
            SELECT type, count(*), sum(amount), min(amount), max(amount)
            FROM transactions
            GROUP BY type
        """))
        for row in r:
            print(f"  type={row[0]}  count={row[1]}  sum={row[2]}  min={row[3]}  max={row[4]}")

        # 3. Sample a few rows
        r = await session.execute(text("SELECT id, date, amount, type, description FROM transactions LIMIT 5"))
        print("\nSample rows:")
        for row in r:
            print(f"  {row[0]}  date={row[1]}  amount={row[2]}  type={row[3]}  desc={row[4]}")

    # 4. Clear dashboard cache
    try:
        from cache import get_redis
        redis = await get_redis()
        keys = []
        async for key in redis.scan_iter("dashboard:*"):
            keys.append(key)
        async for key in redis.scan_iter("v:*"):
            keys.append(key)
        if keys:
            await redis.delete(*keys)
            print(f"\nCleared {len(keys)} cached dashboard keys")
        else:
            print("\nNo cached dashboard keys found")
    except Exception as e:
        print(f"\nCache clear failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
