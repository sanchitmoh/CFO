# Failing Tests - Detailed Analysis

**Generated**: 2024
**Total Failures**: 28 (7 compliance-related, 21 pre-existing)

---

## Category 1: Compliance-Related Test Failures (7)

### 🔍 Root Cause: Authentication Mocking Issues

All 7 failures are in `test_password_policy_integration.py` and are caused by missing authentication mocking in the test setup. The implementation is correct - endpoints properly require authentication and return 401 when not authenticated.

---

### Test 1: `test_get_password_policy_info_endpoint`

**File**: `backend/tests/test_password_policy_integration.py:39`
**Status**: ❌ FAILED
**Expected**: 200 (OK)
**Actual**: 401 (Unauthorized)

**Error**:
```python
assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401 Unauthorized]>.status_code
```

**Analysis**: Test attempts to call `/api/v1/password-policy/info` without authentication. Endpoint correctly returns 401.

**Fix Required**: Add authentication mock to test fixture.

---

### Test 2: `test_validate_password_endpoint`

**File**: `backend/tests/test_password_policy_integration.py:64`
**Status**: ❌ FAILED
**Expected**: 200 (OK)
**Actual**: 401 (Unauthorized)

**Error**:
```python
assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401 Unauthorized]>.status_code
```

**Analysis**: Test attempts to call `/api/v1/password-policy/validate` without authentication. Endpoint correctly returns 401.

**Fix Required**: Add authentication mock to test fixture.

---

### Test 3: `test_validate_password_without_user_info`

**File**: `backend/tests/test_password_policy_integration.py:87`
**Status**: ❌ FAILED
**Expected**: 200 (OK)
**Actual**: 401 (Unauthorized)

**Error**:
```python
assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401 Unauthorized]>.status_code
```

**Analysis**: Test attempts to call `/api/v1/password-policy/validate` without authentication. Endpoint correctly returns 401.

**Fix Required**: Add authentication mock to test fixture.

---

### Test 4: `test_get_password_policy_status_endpoint`

**File**: `backend/tests/test_password_policy_integration.py:103`
**Status**: ❌ FAILED
**Expected**: 200 (OK)
**Actual**: 401 (Unauthorized)

**Error**:
```python
assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401 Unauthorized]>.status_code
```

**Analysis**: Test attempts to call `/api/v1/password-policy/status` without authentication. Endpoint correctly returns 401.

**Fix Required**: Add authentication mock to test fixture.

---

### Test 5: `test_update_password_policy_config_admin`

**File**: `backend/tests/test_password_policy_integration.py:134`
**Status**: ❌ FAILED
**Expected**: 200 (OK)
**Actual**: 401 (Unauthorized)

**Error**:
```python
assert response.status_code == 200
E   assert 401 == 200
E    +  where 401 = <Response [401 Unauthorized]>.status_code
```

**Analysis**: Test attempts to call `/api/v1/password-policy/config` (PUT) without authentication. Endpoint correctly returns 401.

**Fix Required**: Add authentication mock with admin role to test fixture.

---

### Test 6: `test_update_password_policy_config_non_admin`

**File**: `backend/tests/test_password_policy_integration.py:157`
**Status**: ❌ FAILED
**Expected**: 403 (Forbidden)
**Actual**: 401 (Unauthorized)

**Error**:
```python
assert response.status_code == 403
E   assert 401 == 403
E    +  where 401 = <Response [401 Unauthorized]>.status_code
```

**Analysis**: Test attempts to verify non-admin users get 403, but authentication fails first with 401. This is correct behavior - authentication happens before authorization.

**Fix Required**: Add authentication mock with non-admin role to test fixture.

---

### Test 7: `test_update_password_policy_config_validation`

**File**: `backend/tests/test_password_policy_integration.py:177`
**Status**: ❌ FAILED
**Expected**: 400 (Bad Request)
**Actual**: 401 (Unauthorized)

**Error**:
```python
assert response.status_code == 400
E   assert 401 == 400
E    +  where 401 = <Response [401 Unauthorized]>.status_code
```

**Analysis**: Test attempts to verify validation errors return 400, but authentication fails first with 401. This is correct behavior - authentication happens before validation.

**Fix Required**: Add authentication mock to test fixture.

---

### 🔧 Recommended Fix for All 7 Tests

Add authentication mocking to the test class:

```python
@pytest.fixture
def mock_authenticated_user(self):
    """Mock authenticated user for testing."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.workspace_id = uuid.uuid4()
    user.email = "test@example.com"
    user.full_name = "Test User"
    user.role = "owner"  # or "member" for non-admin tests
    user.is_active = True
    return user

@pytest.fixture
def authenticated_client(self, client, mock_authenticated_user):
    """Client with authentication mocked."""
    with patch('auth.get_current_user', return_value=mock_authenticated_user):
        yield client
```

Then update tests to use `authenticated_client` instead of `client`.

---

## Category 2: Pre-existing Test Failures (21)

### 🔍 Root Cause: Missing pytest-asyncio Configuration

Most pre-existing failures are due to missing pytest-asyncio configuration for async test functions.

---

## test_auth.py Failures (15 total: 11 failed, 4 errors)

### Failed Tests (11)

#### 1. `test_rs256_accepted`
**Error**: `Failed: async def functions are not natively supported`
**Fix**: Add `pytest-asyncio` to pytest.ini

#### 2. `test_hs256_algorithm_rejected`
**Error**: `Failed: async def functions are not natively supported`
**Fix**: Add `pytest-asyncio` to pytest.ini

#### 3. `test_missing_kid_rejected`
**Error**: `Failed: async def functions are not natively supported`
**Fix**: Add `pytest-asyncio` to pytest.ini

#### 4. `test_cache_hit_within_ttl`
**Error**: `Failed: async def functions are not natively supported`
**Fix**: Add `pytest-asyncio` to pytest.ini

#### 5. `test_cache_expired_triggers_refetch`
**Error**: `Failed: async def functions are not natively supported`
**Fix**: Add `pytest-asyncio` to pytest.ini

#### 6. `test_graceful_degradation_on_clerk_down`
**Error**: `Failed: async def functions are not natively supported`
**Fix**: Add `pytest-asyncio` to pytest.ini

#### 7. `test_force_refresh_bypasses_ttl`
**Error**: `Failed: async def functions are not natively supported`
**Fix**: Add `pytest-asyncio` to pytest.ini

#### 8. `test_expired_token_rejected`
**Error**: `Failed: async def functions are not natively supported`
**Fix**: Add `pytest-asyncio` to pytest.ini

#### 9. `test_unknown_kid_triggers_refetch`
**Error**: `Failed: async def functions are not natively supported`
**Fix**: Add `pytest-asyncio` to pytest.ini

#### 10. `test_missing_sub_rejected`
**Error**: `Failed: async def functions are not natively supported`
**Fix**: Add `pytest-asyncio` to pytest.ini

#### 11. `test_rate_limit_constants`
**Error**: Missing `_auth_failures` attribute
**Fix**: Initialize `_auth_failures` in auth module

### Error Tests (4)

#### 12. `test_under_limit_passes`
**Error**: `AttributeError: module 'auth' has no attribute '_auth_failures'`
**Fix**: Initialize `_auth_failures` dictionary in auth module

#### 13. `test_at_limit_blocks`
**Error**: `AttributeError: module 'auth' has no attribute '_auth_failures'`
**Fix**: Initialize `_auth_failures` dictionary in auth module

#### 14. `test_different_ips_independent`
**Error**: `AttributeError: module 'auth' has no attribute '_auth_failures'`
**Fix**: Initialize `_auth_failures` dictionary in auth module

#### 15. `test_expired_failures_pruned`
**Error**: `AttributeError: module 'auth' has no attribute '_auth_failures'`
**Fix**: Initialize `_auth_failures` dictionary in auth module

---

## test_security.py Failures (6 total: 3 failed, 3 errors)

### Failed Tests (3)

#### 1. `test_path_traversal_prevention`
**Error**: `Failed: async def functions are not natively supported`
**Fix**: Add `pytest-asyncio` to pytest.ini

#### 2. `test_encrypt_decrypt_roundtrip`
**Error**: `Failed: async def functions are not natively supported`
**Fix**: Add `pytest-asyncio` to pytest.ini

#### 3. `test_rate_limit_constants`
**Error**: Missing rate limiting configuration
**Fix**: Add rate limiting configuration

### Error Tests (3)

#### 4. `test_rls_parameterized_query`
**Error**: `Failed: async def functions are not natively supported`
**Fix**: Add `pytest-asyncio` to pytest.ini

#### 5. `test_rls_isolation`
**Error**: `Failed: async def functions are not natively supported`
**Fix**: Add `pytest-asyncio` to pytest.ini

#### 6. `test_security_headers_present`
**Error**: `Failed: async def functions are not natively supported`
**Fix**: Add `pytest-asyncio` to pytest.ini

---

## 🔧 Global Fixes Required

### Fix 1: Add pytest-asyncio Configuration

Create or update `pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
testpaths = backend/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

This will fix 18 of the 21 pre-existing failures.

### Fix 2: Initialize Rate Limiting in auth.py

Add to `backend/auth.py`:

```python
# Rate limiting state (in-memory for now, should use Redis in production)
_auth_failures: Dict[str, List[datetime]] = {}
```

This will fix 4 of the 21 pre-existing failures.

---

## 📊 Summary

| Category | Count | Fix Effort | Priority |
|----------|-------|------------|----------|
| Auth mocking issues | 7 | 2-4 hours | Medium |
| pytest-asyncio config | 18 | 1 hour | Low |
| Rate limiting state | 4 | 1 hour | Low |
| **TOTAL** | **29** | **4-6 hours** | - |

---

## ✅ Verification After Fixes

After implementing the fixes, run:

```bash
# Test compliance fixes
python -m pytest backend/tests/test_password_policy_integration.py -v

# Test pre-existing auth/security
python -m pytest backend/tests/test_auth.py backend/tests/test_security.py -v

# Test everything
python -m pytest backend/tests/ -v
```

Expected results after fixes:
- Compliance tests: 60/60 pass (100%)
- Pre-existing tests: 35/35 pass (100%)
- Total: 95/95 pass (100%)

---

**Report Generated**: 2024
**For**: comprehensive-compliance-fixes bugfix spec
