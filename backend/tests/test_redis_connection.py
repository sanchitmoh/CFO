"""
Quick Redis connection test script
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def test_redis():
    """Test Redis connection with detailed diagnostics"""
    from backend.cache import get_redis
    from backend.config import settings
    
    print("=" * 60)
    print("Redis Connection Test")
    print("=" * 60)
    print(f"\nRedis URL: {settings.REDIS_URL[:30]}...{settings.REDIS_URL[-20:]}")
    print(f"Cache TTL: {settings.CACHE_TTL_SECONDS}s")
    
    try:
        print("\n[1/3] Attempting to get Redis client...")
        r = await get_redis()
        print("✓ Redis client created")
        
        print("\n[2/3] Testing PING command...")
        response = await r.ping()
        print(f"✓ PING successful: {response}")
        
        print("\n[3/3] Testing SET/GET operations...")
        test_key = "test:connection:check"
        test_value = "Hello from AI CFO!"
        
        await r.setex(test_key, 10, test_value)
        print(f"✓ SET successful: {test_key}")
        
        retrieved = await r.get(test_key)
        print(f"✓ GET successful: {retrieved}")
        
        await r.delete(test_key)
        print(f"✓ DELETE successful")
        
        print("\n" + "=" * 60)
        print("✅ Redis is working correctly!")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ Redis connection FAILED!")
        print("=" * 60)
        print(f"\nError type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        
        # Additional diagnostics
        print("\n--- Diagnostics ---")
        
        if "Connection refused" in str(e):
            print("• Redis server is not running or not accessible")
            print("• Check if Redis is installed and running")
            
        elif "timeout" in str(e).lower():
            print("• Connection timeout - Redis server may be slow or unreachable")
            print("• Check network connectivity and firewall rules")
            
        elif "authentication" in str(e).lower() or "NOAUTH" in str(e):
            print("• Authentication failed")
            print("• Check REDIS_URL credentials in backend/.env")
            
        elif "SSL" in str(e) or "TLS" in str(e):
            print("• SSL/TLS connection issue")
            print("• Verify rediss:// URL format and certificate settings")
            
        else:
            print("• Unknown error - check Redis server logs")
        
        print("\n--- Troubleshooting Steps ---")
        print("1. Verify REDIS_URL in backend/.env is correct")
        print("2. Check if Redis server is running (local or Upstash)")
        print("3. Test connection with redis-cli or Upstash console")
        print("4. Check firewall/network settings")
        print("5. Verify credentials and permissions")
        
        return False
    
    return True

if __name__ == "__main__":
    result = asyncio.run(test_redis())
    sys.exit(0 if result else 1)
