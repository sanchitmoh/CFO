"""Quick Redis connection test"""
import asyncio
from cache import get_redis
from config import settings

async def test():
    print(f"Testing Redis: {settings.REDIS_URL[:30]}...{settings.REDIS_URL[-20:]}")
    try:
        r = await get_redis()
        result = await r.ping()
        print(f"✅ PING successful: {result}")
        
        # Test set/get
        await r.setex("test:key", 10, "test_value")
        val = await r.get("test:key")
        print(f"✅ SET/GET successful: {val}")
        await r.delete("test:key")
        
        print("✅ Redis is working!")
        return True
    except Exception as e:
        print(f"❌ Redis failed: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test())
