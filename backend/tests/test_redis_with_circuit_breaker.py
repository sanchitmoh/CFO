"""Test Redis connection with circuit breaker behavior"""
import asyncio
import time
from cache import get_redis, _redis_down_until, REDIS_CIRCUIT_BREAKER_SECONDS

async def test_circuit_breaker():
    """Test that Redis works after circuit breaker timeout"""
    print("=" * 60)
    print("Redis Circuit Breaker Test")
    print("=" * 60)
    
    # Check circuit breaker status
    import time as _time
    if _redis_down_until > 0:
        remaining = _redis_down_until - _time.monotonic()
        if remaining > 0:
            print(f"\n⚠️  Circuit breaker is OPEN")
            print(f"   Remaining time: {remaining:.1f}s")
            print(f"   Waiting for circuit breaker to close...")
            await asyncio.sleep(remaining + 1)
            print(f"✓  Circuit breaker should now be CLOSED")
    
    print("\n[1/3] Testing Redis connection...")
    try:
        r = await get_redis()
        print("✓ Redis client obtained")
        
        print("\n[2/3] Testing PING...")
        result = await r.ping()
        print(f"✓ PING successful: {result}")
        
        print("\n[3/3] Testing SET/GET operations...")
        test_key = "test:circuit_breaker:check"
        test_value = f"test_{int(time.time())}"
        
        await r.setex(test_key, 10, test_value)
        retrieved = await r.get(test_key)
        await r.delete(test_key)
        
        print(f"✓ SET/GET/DELETE successful")
        print(f"   Stored: {test_value}")
        print(f"   Retrieved: {retrieved}")
        
        print("\n" + "=" * 60)
        print("✅ Redis is working correctly!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ Redis test failed!")
        print("=" * 60)
        print(f"Error: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_circuit_breaker())
    exit(0 if success else 1)
